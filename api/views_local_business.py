"""
지역 업체 정보 ViewSet
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes as perm_decorator
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
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

    def list(self, request, *args, **kwargs):
        """카테고리 목록 조회 - 세무사+회계사, 법무사+변호사 통합

        쿼리 파라미터:
        - raw=true: 통합 없이 원본 카테고리 10개 반환 (전문가 회원가입용)
        """
        from django.db.models import Q

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # raw=true인 경우 원본 카테고리 그대로 반환 (전문가 회원가입용)
        raw_mode = request.query_params.get('raw', '').lower() == 'true'
        if raw_mode:
            return Response(serializer.data)

        # 통합할 카테고리 처리
        # 세무사+회계사 → 세무·회계, 법무사+변호사 → 법률 서비스, 청소+이사 → 청소·이사
        categories = []
        tax_accounting_added = False
        legal_service_added = False
        cleaning_moving_added = False
        skip_categories = []

        for cat_data in serializer.data:
            category_name = cat_data['name']

            # 세무사+회계사 통합
            if category_name in ['세무사', '회계사']:
                skip_categories.append(category_name)
                if not tax_accounting_added:
                    tax_accounting_count = LocalBusiness.objects.filter(
                        Q(category__name='세무사') | Q(category__name='회계사')
                    ).count()
                    categories.append({
                        'id': 'tax_accounting',
                        'name': '세무·회계',
                        'name_en': 'tax & accounting',
                        'icon': '💼',
                        'google_place_type': 'accounting',
                        'description': '세무사, 회계사 등 세무·회계 전문 서비스',
                        'order_index': 1,
                        'is_active': True,
                        'business_count': tax_accounting_count,
                        'merged_categories': ['세무사', '회계사']
                    })
                    tax_accounting_added = True

            # 법무사+변호사 통합
            elif category_name in ['법무사', '변호사']:
                skip_categories.append(category_name)
                if not legal_service_added:
                    legal_service_count = LocalBusiness.objects.filter(
                        Q(category__name='법무사') | Q(category__name='변호사')
                    ).count()
                    categories.append({
                        'id': 'legal_service',
                        'name': '법률 서비스',
                        'name_en': 'legal service',
                        'icon': '⚖️',
                        'google_place_type': 'legal',
                        'description': '변호사, 법무사 등 법률 전문 서비스',
                        'order_index': 2,
                        'is_active': True,
                        'business_count': legal_service_count,
                        'merged_categories': ['변호사', '법무사']
                    })
                    legal_service_added = True

            # 청소+이사 통합
            elif category_name in ['청소 전문', '이사 전문']:
                skip_categories.append(category_name)
                if not cleaning_moving_added:
                    cleaning_moving_count = LocalBusiness.objects.filter(
                        Q(category__name='청소 전문') | Q(category__name='이사 전문')
                    ).count()
                    categories.append({
                        'id': 'cleaning_moving',
                        'name': '청소·이사',
                        'name_en': 'cleaning & moving',
                        'icon': '🧹',
                        'google_place_type': 'service',
                        'description': '청소, 이사 전문 서비스',
                        'order_index': 9,
                        'is_active': True,
                        'business_count': cleaning_moving_count,
                        'merged_categories': ['청소 전문', '이사 전문']
                    })
                    cleaning_moving_added = True

            # 나머지 카테고리는 그대로 추가
            else:
                business_count = LocalBusiness.objects.filter(category_id=cat_data['id']).count()
                cat_data['business_count'] = business_count
                categories.append(cat_data)

        return Response(categories)


class LocalBusinessViewSet(viewsets.ModelViewSet):
    """지역 업체 ViewSet"""

    queryset = LocalBusiness.objects.select_related(
        'category'
    ).prefetch_related('links')
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']  # 명시적으로 POST 허용
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_verified']  # category는 get_queryset에서 커스텀 처리
    search_fields = ['name', 'address']
    ordering_fields = ['popularity_score', 'rating', 'review_count', 'rank_in_region', 'created_at']
    ordering = ['-popularity_score']  # 기본 정렬: 인기도순 (높은순)

    # Version marker for deployment verification
    _deployment_version = "2025-01-23-v2"

    def get_queryset(self):
        """커스텀 필터링"""
        from django.db.models import Q

        queryset = super().get_queryset()

        # region_name__icontains 파라미터 처리
        region_filter = self.request.query_params.get('region_name__icontains')
        if region_filter:
            queryset = queryset.filter(region_name__icontains=region_filter)

        # 통합 카테고리 필터링 처리
        category_filter = self.request.query_params.get('category')
        if category_filter:
            if category_filter == 'tax_accounting':
                # 세무·회계: 세무사 + 회계사
                queryset = queryset.filter(
                    Q(category__name='세무사') | Q(category__name='회계사')
                )
            elif category_filter == 'legal_service':
                # 법률 서비스: 변호사 + 법무사
                queryset = queryset.filter(
                    Q(category__name='변호사') | Q(category__name='법무사')
                )
            elif category_filter == 'cleaning_moving':
                # 청소·이사: 청소 전문 + 이사 전문
                queryset = queryset.filter(
                    Q(category__name='청소 전문') | Q(category__name='이사 전문')
                )
            else:
                # 일반 카테고리 ID 필터링
                queryset = queryset.filter(category_id=category_filter)

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
            summary, error_msg = generate_business_summary(reviews, business_name)

            if summary:
                return Response({
                    'success': True,
                    'summary': summary
                })
            else:
                # 리뷰 없음/텍스트 없음은 정상 응답 (200 OK)
                if error_msg in ["리뷰 데이터 없음", "텍스트 리뷰 없음 (평점만 존재)"]:
                    return Response({
                        'success': False,
                        'summary': None,
                        'reason': error_msg  # 500 아닌 200으로 반환
                    })
                # OpenAI API 오류만 500
                else:
                    return Response(
                        {'success': False, 'error': error_msg or 'AI 요약 생성 실패', 'summary': None},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        except Exception as e:
            logger.error(f'AI 요약 생성 중 오류: {str(e)}')
            return Response(
                {'success': False, 'error': f'AI 요약 생성 오류: {str(e)}', 'summary': None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def download_and_save_photo(self, photo_url, business_name, google_place_id):
        """Google 이미지를 다운로드해서 custom_photo 필드에 저장 (ImageField 사용)"""
        from django.core.files.base import ContentFile
        import uuid

        if not photo_url:
            return None

        try:
            # Google 이미지 다운로드
            response = requests.get(photo_url, timeout=10)
            if response.status_code != 200:
                logger.error(f'Failed to download photo: {response.status_code}')
                return None

            # 파일명 생성
            file_extension = 'jpg'
            filename = f"{google_place_id}_{uuid.uuid4().hex[:8]}.{file_extension}"

            # ContentFile 객체 생성 (ImageField.save()에 사용)
            return ContentFile(response.content), filename

        except Exception as e:
            logger.error(f'Error downloading photo for {business_name}: {str(e)}')
            return None

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """프론트에서 수집한 업체 데이터 일괄 저장 (30일 캐싱 정책 + S3 이미지 저장)"""
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
                            new_summary = business_data.get('editorial_summary')

                            # 기존 요약이 없고 새 요약이 있으면 저장
                            if not existing.editorial_summary and new_summary:
                                logger.info(f"[UPDATE] {business_data.get('name')}: 새 AI 요약 추가 - {new_summary}")
                                existing.editorial_summary = new_summary
                                existing.save(update_fields=['editorial_summary'])
                                updated_count += 1
                            # 기존 요약이 있고 새 요약이 있으면 업데이트
                            elif existing.editorial_summary and new_summary:
                                logger.info(f"[UPDATE] {business_data.get('name')}: AI 요약 갱신 - {new_summary}")
                                existing.editorial_summary = new_summary
                                existing.save(update_fields=['editorial_summary'])
                                updated_count += 1
                            # 둘 다 없으면 skip
                            else:
                                skipped_count += 1
                            continue

                        # 30일 지났으면 전체 업데이트 (이미지 포함)
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
                        existing.photo_url = business_data.get('photo_url')  # 백업용
                        existing.website_url = business_data.get('website_url')
                        existing.opening_hours = business_data.get('opening_hours')
                        existing.editorial_summary = business_data.get('editorial_summary')
                        existing.business_status = business_data.get('business_status', 'OPERATIONAL')
                        existing.last_review_time = business_data.get('last_review_time')
                        existing.popularity_score = business_data.get('popularity_score', 0)
                        existing.rank_in_region = business_data.get('rank_in_region', 999)
                        existing.last_synced_at = timezone.now()

                        # Google 이미지 다운로드 및 custom_photo 저장 (파일 없으면 무조건 저장)
                        photo_url = business_data.get('photo_url')
                        has_actual_file = existing.custom_photo and existing.custom_photo.name

                        if photo_url and not has_actual_file:
                            # 파일이 없으면 무조건 다운로드해서 저장
                            photo_result = self.download_and_save_photo(
                                photo_url,
                                business_data.get('name', ''),
                                google_place_id
                            )
                            if photo_result:
                                content_file, filename = photo_result
                                existing.custom_photo.save(filename, content_file, save=False)
                                logger.info(f"[S3 SAVE] {business_data.get('name')}: 이미지 저장 완료")
                            else:
                                logger.warning(f"[S3 FAIL] {business_data.get('name')}: 이미지 다운로드 실패")
                        elif has_actual_file:
                            logger.info(f"[SKIP] {business_data.get('name')}: 이미 이미지 파일 존재")

                        existing.save()
                        updated_count += 1

                    except LocalBusiness.DoesNotExist:
                        # 신규 업체 생성
                        editorial_summary = business_data.get('editorial_summary')
                        logger.info(f"[SAVE] {business_data.get('name')}: editorial_summary={editorial_summary}")

                        # 업체 생성
                        business = LocalBusiness.objects.create(
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
                            photo_url=business_data.get('photo_url'),  # 원본 URL은 백업용
                            website_url=business_data.get('website_url'),
                            opening_hours=business_data.get('opening_hours'),
                            editorial_summary=editorial_summary,
                            business_status=business_data.get('business_status', 'OPERATIONAL'),
                            last_review_time=business_data.get('last_review_time'),
                            popularity_score=business_data.get('popularity_score', 0),
                            rank_in_region=business_data.get('rank_in_region', 999),
                            last_synced_at=timezone.now(),
                        )

                        # Google 이미지 다운로드 및 custom_photo에 저장 (신규 업체는 무조건 저장)
                        photo_url = business_data.get('photo_url')
                        if photo_url:
                            photo_result = self.download_and_save_photo(
                                photo_url,
                                business_data.get('name', ''),
                                google_place_id
                            )
                            if photo_result:
                                content_file, filename = photo_result
                                business.custom_photo.save(filename, content_file, save=True)
                                logger.info(f"[S3 SAVE] {business_data.get('name')}: 이미지 저장 완료 (신규)")
                            else:
                                logger.warning(f"[S3 FAIL] {business_data.get('name')}: 이미지 다운로드 실패 (신규)")

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

        logger.info('=' * 80)
        logger.info(f'[google_search_proxy] CALLED - Version: {self._deployment_version}')
        logger.info(f'[google_search_proxy] Request method: {request.method}')
        logger.info(f'[google_search_proxy] Request data: {request.data}')
        logger.info(f'[google_search_proxy] User: {request.user}')
        logger.info('=' * 80)

        api_key = settings.GOOGLE_PLACES_API_KEY
        if not api_key:
            logger.error('[google_search_proxy] API key not configured!')
            return Response(
                {'error': 'Google Places API key not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # textQuery 또는 includedTypes로 API 선택
            has_text_query = 'textQuery' in request.data
            has_included_types = 'includedTypes' in request.data and request.data['includedTypes']

            if has_text_query:
                # Text Search API
                url = 'https://places.googleapis.com/v1/places:searchText'
                logger.info('[google_search_proxy] Using Text Search API')
            elif has_included_types:
                # Nearby Search API
                url = 'https://places.googleapis.com/v1/places:searchNearby'
                logger.info('[google_search_proxy] Using Nearby Search API')
            else:
                # 기본값: Nearby Search
                url = 'https://places.googleapis.com/v1/places:searchNearby'
                logger.info('[google_search_proxy] Using Nearby Search API (default)')

            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.businessStatus,places.internationalPhoneNumber,places.websiteUri,places.editorialSummary,places.reviews,places.photos,places.regularOpeningHours',
                'X-Goog-LanguageCode': 'ko'
            }

            logger.info(f'[google_search_proxy] Calling Google API: {url}')
            logger.info(f'[google_search_proxy] Request payload size: {len(str(request.data))} bytes')

            response = requests.post(url, json=request.data, headers=headers, timeout=10)

            logger.info(f'[google_search_proxy] Google API response status: {response.status_code}')
            logger.info(f'[google_search_proxy] Returning response to client')

            # 응답 그대로 반환
            return Response(response.json(), status=response.status_code)

        except requests.RequestException as e:
            logger.error('=' * 80)
            logger.error(f'[google_search_proxy] REQUEST EXCEPTION!')
            logger.error(f'[google_search_proxy] Error type: {type(e).__name__}')
            logger.error(f'[google_search_proxy] Error message: {str(e)}')
            logger.error('=' * 80)
            return Response(
                {'error': f'API request failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def photo(self, request, pk=None):
        """업체 사진 프록시 (photo_url 백업용)

        참고: custom_photo가 우선순위이므로 이 엔드포인트는 거의 사용 안 됨
        사용법: /api/local-businesses/{id}/photo/
        """
        from django.conf import settings

        business = self.get_object()

        if not business.photo_url:
            return HttpResponse(status=404)

        try:
            # photo_url에 API 키 추가 (백엔드에서만 처리)
            photo_url_with_key = f"{business.photo_url}&key={settings.GOOGLE_PLACES_API_KEY}"

            # Google에서 이미지 다운로드 (타임아웃 5초)
            response = requests.get(photo_url_with_key, timeout=5)

            if response.status_code == 200:
                # Content-Type 확인 (기본값: image/jpeg)
                content_type = response.headers.get('Content-Type', 'image/jpeg')

                # 이미지를 클라이언트에게 전달
                return HttpResponse(
                    response.content,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # 1일 브라우저 캐싱
                    }
                )
            else:
                logger.error(f'Failed to fetch photo for business {pk}: {response.status_code}')
                return HttpResponse(status=404)

        except requests.RequestException as e:
            logger.error(f'Error fetching photo for business {pk}: {str(e)}')
            return HttpResponse(status=500)


# 독립적인 view 함수로 google_search_proxy 구현
@csrf_exempt
@api_view(['POST'])
@perm_decorator([AllowAny])
def google_search_proxy_standalone(request):
    """Google Places API 프록시 (CORS 우회) - 독립 함수 버전

    ViewSet의 @action이 작동하지 않아 독립 함수로 구현

    사용법: POST /api/local-businesses/google-search-proxy/
    Body: { "textQuery": "...", "locationBias": {...}, "maxResultCount": 20 }
    """
    from django.conf import settings

    logger.info('=' * 80)
    logger.info('[google_search_proxy_standalone] CALLED - Standalone version')
    logger.info(f'[google_search_proxy_standalone] Request method: {request.method}')
    logger.info(f'[google_search_proxy_standalone] Request data: {request.data}')
    logger.info('=' * 80)

    api_key = settings.GOOGLE_PLACES_API_KEY
    if not api_key:
        logger.error('[google_search_proxy_standalone] API key not configured!')
        return Response(
            {'error': 'Google Places API key not configured'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    try:
        # textQuery 또는 includedTypes로 API 선택
        has_text_query = 'textQuery' in request.data
        has_included_types = 'includedTypes' in request.data and request.data['includedTypes']

        if has_text_query:
            url = 'https://places.googleapis.com/v1/places:searchText'
            logger.info('[google_search_proxy_standalone] Using Text Search API')
        elif has_included_types:
            url = 'https://places.googleapis.com/v1/places:searchNearby'
            logger.info('[google_search_proxy_standalone] Using Nearby Search API')
        else:
            url = 'https://places.googleapis.com/v1/places:searchNearby'
            logger.info('[google_search_proxy_standalone] Using Nearby Search API (default)')

        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.businessStatus,places.internationalPhoneNumber,places.websiteUri,places.editorialSummary,places.reviews,places.photos,places.regularOpeningHours',
            'X-Goog-LanguageCode': 'ko'
        }

        logger.info(f'[google_search_proxy_standalone] Calling Google API: {url}')
        response = requests.post(url, json=request.data, headers=headers, timeout=10)
        logger.info(f'[google_search_proxy_standalone] Google API response: {response.status_code}')

        return Response(response.json(), status=response.status_code)

    except requests.RequestException as e:
        logger.error('=' * 80)
        logger.error(f'[google_search_proxy_standalone] ERROR: {type(e).__name__}')
        logger.error(f'[google_search_proxy_standalone] Message: {str(e)}')
        logger.error('=' * 80)
        return Response(
            {'error': f'API request failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



