"""
지역 업체 정보 ViewSet
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.utils import timezone
from django.http import HttpResponse
import requests
import logging

logger = logging.getLogger(__name__)

from api.models_local_business import (
    LocalBusinessCategory,
    LocalBusiness,
    LocalBusinessView
)
from api.serializers_local_business import (
    LocalBusinessCategorySerializer,
    LocalBusinessListSerializer,
    LocalBusinessDetailSerializer
)


class LocalBusinessCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """업종 카테고리 ViewSet (읽기 전용)"""

    queryset = LocalBusinessCategory.objects.filter(is_active=True)
    serializer_class = LocalBusinessCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """활성화된 카테고리만 정렬순으로"""
        return self.queryset.order_by('order_index', 'name')


class LocalBusinessViewSet(viewsets.ModelViewSet):
    """지역 업체 ViewSet"""

    queryset = LocalBusiness.objects.select_related(
        'category'
    ).prefetch_related('links')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_verified']
    search_fields = ['name', 'address']
    ordering_fields = ['popularity_score', 'rating', 'review_count', 'rank_in_region', 'created_at']
    ordering = ['rank_in_region']  # 기본 정렬: 순위순

    # Version marker for deployment verification
    _deployment_version = "2025-01-23-rebuild"

    def get_queryset(self):
        """커스텀 필터링"""
        queryset = super().get_queryset()

        # region_name__icontains 파라미터 처리
        region_filter = self.request.query_params.get('region_name__icontains')
        if region_filter:
            queryset = queryset.filter(region_name__icontains=region_filter)

        return queryset

    def get_serializer_class(self):
        """액션별 Serializer 선택"""
        if self.action == 'retrieve':
            return LocalBusinessDetailSerializer
        return LocalBusinessListSerializer

    def retrieve(self, request, *args, **kwargs):
        """상세 조회 시 조회수 증가"""
        instance = self.get_object()

        # 조회수 증가
        LocalBusiness.objects.filter(pk=instance.pk).update(
            view_count=F('view_count') + 1
        )

        # 조회 로그 기록
        ip_address = self.get_client_ip(request)
        LocalBusinessView.objects.create(
            business=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address
        )

        # 인스턴스 새로고침 (view_count 업데이트 반영)
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @action(detail=False, methods=['get'])
    def by_region_category(self, request):
        """지역+업종별 상위 업체 조회

        Query Params:
            - region: 지역명 (예: 강남구, 수원시)
            - category: 카테고리 ID
            - limit: 조회 개수 (기본: 5)
        """
        region_name = request.query_params.get('region')
        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 5))

        if not region_name or not category_id:
            return Response(
                {'error': 'region과 category 파라미터가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        businesses = self.queryset.filter(
            region_name=region_name,
            category_id=category_id
        ).order_by('rank_in_region')[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """인기 업체 조회 (전체)

        Query Params:
            - category: 카테고리 ID (선택)
            - limit: 조회 개수 (기본: 10)
        """
        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))

        businesses = self.queryset.order_by('-popularity_score')

        if category_id:
            businesses = businesses.filter(category_id=category_id)

        businesses = businesses[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new(self, request):
        """최근 등록 업체 조회 (30일 이내)

        Query Params:
            - category: 카테고리 ID (선택)
            - limit: 조회 개수 (기본: 10)
        """
        from datetime import timedelta

        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))

        # 30일 이내 등록된 업체
        thirty_days_ago = timezone.now() - timedelta(days=30)
        businesses = self.queryset.filter(
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')

        if category_id:
            businesses = businesses.filter(category_id=category_id)

        businesses = businesses[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_summary(self, request):
        """리뷰를 받아서 AI 요약 생성"""
        from api.utils_ai_summary import generate_business_summary

        business_name = request.data.get('business_name')
        reviews = request.data.get('reviews', [])

        if not business_name:
            return Response(
                {'error': 'business_name이 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reviews or len(reviews) == 0:
            return Response(
                {'summary': None, 'message': '리뷰가 없어 요약을 생성할 수 없습니다'}
            )

        # AI 요약 생성
        try:
            summary = generate_business_summary(reviews, business_name)

            if summary:
                return Response({
                    'success': True,
                    'summary': summary
                })
            else:
                return Response(
                    {'success': False, 'error': 'AI 요약 생성 실패 (summary is None)', 'summary': None},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f'AI 요약 생성 중 오류: {str(e)}')
            return Response(
                {'success': False, 'error': f'AI 요약 생성 오류: {str(e)}', 'summary': None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """프론트에서 수집한 업체 데이터 일괄 저장 (30일 캐싱 정책)"""
        from django.db import transaction
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta

        businesses_data = request.data.get('businesses', [])

        if not businesses_data:
            return Response(
                {'error': 'businesses 배열이 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # 30일 기준
        thirty_days_ago = timezone.now() - timedelta(days=30)

        for business_data in businesses_data:
            try:
                with transaction.atomic():
                    category_id = business_data.get('category_id')
                    if not category_id:
                        errors.append(f"{business_data.get('name')}: category_id 필수")
                        continue

                    category = LocalBusinessCategory.objects.get(id=category_id)
                    google_place_id = business_data['google_place_id']

                    # 기존 업체 확인
                    try:
                        existing = LocalBusiness.objects.get(google_place_id=google_place_id)

                        # 30일 이내 업데이트된 업체는 AI 요약만 업데이트
                        if existing.last_synced_at and existing.last_synced_at > thirty_days_ago:
                            # AI 요약이 있으면 업데이트
                            if business_data.get('editorial_summary'):
                                existing.editorial_summary = business_data.get('editorial_summary')
                                existing.save(update_fields=['editorial_summary'])
                                updated_count += 1
                            else:
                                skipped_count += 1
                            continue

                        # 30일 지났으면 전체 업데이트 (photo_url 포함)
                        existing.category = category
                        existing.region_name = business_data.get('region_name', '')
                        existing.name = business_data.get('name', '')
                        existing.address = business_data.get('address', '')
                        existing.phone_number = business_data.get('phone_number')
                        existing.latitude = Decimal(str(business_data['latitude'])) if business_data.get('latitude') else None
                        existing.longitude = Decimal(str(business_data['longitude'])) if business_data.get('longitude') else None
                        existing.rating = Decimal(str(business_data['rating'])) if business_data.get('rating') else None
                        existing.review_count = business_data.get('review_count', 0)
                        existing.google_maps_url = business_data.get('google_maps_url', '')
                        existing.photo_url = business_data.get('photo_url')  # 30일 지났으니 갱신
                        existing.website_url = business_data.get('website_url')
                        existing.opening_hours = business_data.get('opening_hours')
                        existing.editorial_summary = business_data.get('editorial_summary')
                        existing.business_status = business_data.get('business_status', 'OPERATIONAL')
                        existing.last_review_time = business_data.get('last_review_time')
                        existing.popularity_score = business_data.get('popularity_score', 0)
                        existing.rank_in_region = business_data.get('rank_in_region', 999)
                        existing.last_synced_at = timezone.now()
                        existing.save()

                        updated_count += 1

                    except LocalBusiness.DoesNotExist:
                        # 신규 업체 생성
                        LocalBusiness.objects.create(
                            google_place_id=google_place_id,
                            category=category,
                            region_name=business_data.get('region_name', ''),
                            name=business_data.get('name', ''),
                            address=business_data.get('address', ''),
                            phone_number=business_data.get('phone_number'),
                            latitude=Decimal(str(business_data['latitude'])) if business_data.get('latitude') else None,
                            longitude=Decimal(str(business_data['longitude'])) if business_data.get('longitude') else None,
                            rating=Decimal(str(business_data['rating'])) if business_data.get('rating') else None,
                            review_count=business_data.get('review_count', 0),
                            google_maps_url=business_data.get('google_maps_url', ''),
                            photo_url=business_data.get('photo_url'),
                            website_url=business_data.get('website_url'),
                            opening_hours=business_data.get('opening_hours'),
                            editorial_summary=business_data.get('editorial_summary'),
                            business_status=business_data.get('business_status', 'OPERATIONAL'),
                            last_review_time=business_data.get('last_review_time'),
                            popularity_score=business_data.get('popularity_score', 0),
                            rank_in_region=business_data.get('rank_in_region', 999),
                            last_synced_at=timezone.now(),
                        )
                        created_count += 1

            except LocalBusinessCategory.DoesNotExist:
                errors.append(f"{business_data.get('name')}: 카테고리 {category_id} 없음")
            except Exception as e:
                errors.append(f"{business_data.get('name')}: {str(e)}")

        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors,
            'total': len(businesses_data),
            'message': f'30일 이내 업데이트된 {skipped_count}개 업체는 스킵했습니다 (photo_url 유지)'
        })

    @action(detail=False, methods=['post'])
    def google_search_proxy(self, request):
        """Google Places API 프록시 (CORS 우회)

        사용법: POST /api/local-businesses/google-search-proxy/
        Body: { "textQuery": "...", "locationBias": {...}, "maxResultCount": 20 }
        """
        from django.conf import settings

        logger.info(f'[google_search_proxy] Called with version: {self._deployment_version}')

        api_key = settings.GOOGLE_PLACES_API_KEY
        if not api_key:
            return Response(
                {'error': 'Google Places API key not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Google Places API 호출
            url = 'https://places.googleapis.com/v1/places:searchText'
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.businessStatus,places.internationalPhoneNumber,places.websiteUri,places.editorialSummary,places.reviews,places.photos,places.regularOpeningHours',
                'X-Goog-LanguageCode': 'ko'
            }

            response = requests.post(url, json=request.data, headers=headers, timeout=10)

            # 응답 그대로 반환
            return Response(response.json(), status=response.status_code)

        except requests.RequestException as e:
            logger.error(f'Google Places API proxy error: {str(e)}')
            return Response(
                {'error': f'API request failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def photo(self, request, pk=None):
        """업체 사진 프록시 (API 키 숨김)

        사용법: /api/local-businesses/{id}/photo/
        """
        business = self.get_object()

        if not business.photo_url:
            return HttpResponse(status=404)

        try:
            # Google에서 이미지 다운로드 (타임아웃 5초)
            response = requests.get(business.photo_url, timeout=5)

            if response.status_code == 200:
                # Content-Type 확인 (기본값: image/jpeg)
                content_type = response.headers.get('Content-Type', 'image/jpeg')

                # 이미지를 클라이언트에게 전달
                return HttpResponse(
                    response.content,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # 1일 캐싱
                    }
                )
            else:
                logger.error(f'Failed to fetch photo for business {pk}: {response.status_code}')
                return HttpResponse(status=404)

        except requests.RequestException as e:
            logger.error(f'Error fetching photo for business {pk}: {str(e)}')
            return HttpResponse(status=500)

