"""
Used Phones API Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Q, F
from django_filters.rest_framework import DjangoFilterBackend
import logging
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer

logger = logging.getLogger(__name__)
from .serializers import (
    UsedPhoneListSerializer, UsedPhoneDetailSerializer, 
    UsedPhoneCreateSerializer, UsedPhoneOfferSerializer,
    UsedPhoneFavoriteSerializer
)


class UsedPhoneViewSet(viewsets.ModelViewSet):
    """Used Phone ViewSet"""
    queryset = UsedPhone.objects.filter(status='active')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'description']
    ordering_fields = ['price', 'created_at', 'view_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """지역 필터링 추가"""
        queryset = super().get_queryset()
        
        # 지역 필터링
        region = self.request.query_params.get('region')
        if region:
            # 상위 지역(시/도)인 경우 하위 지역도 포함
            from api.models import Region
            
            # 입력된 지역이 상위 지역인지 확인
            parent_region = Region.objects.filter(
                name=region,
                parent_id__isnull=True  # parent_id가 null이면 상위 지역
            ).first()
            
            if parent_region:
                # 상위 지역인 경우: 해당 지역과 모든 하위 지역 포함
                sub_regions = Region.objects.filter(parent_id=parent_region.pk)
                region_ids = [parent_region.pk] + list(sub_regions.values_list('pk', flat=True))
                
                queryset = queryset.filter(
                    Q(regions__region_id__in=region_ids) |  # UsedPhoneRegion을 통한 다중 지역
                    Q(region_id__in=region_ids)  # 메인 region 필드
                ).distinct()
            else:
                # 하위 지역이거나 정확한 매칭
                queryset = queryset.filter(
                    Q(regions__region__name__icontains=region) |  # UsedPhoneRegion을 통한 다중 지역
                    Q(region__name__icontains=region)  # 메인 region 필드
                ).distinct()
        
        # 가격 범위 필터링
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            try:
                queryset = queryset.filter(price__gte=int(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                queryset = queryset.filter(price__lte=int(max_price))
            except ValueError:
                pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update':
            return UsedPhoneCreateSerializer
        elif self.action == 'list':
            return UsedPhoneListSerializer
        return UsedPhoneDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create to handle regions properly"""
        logger.info(f"=== UsedPhone Create Request ===")
        logger.info(f"User: {request.user}")
        logger.info(f"Request data keys: {request.data.keys()}")
        
        # regions 데이터 확인
        regions = request.data.getlist('regions') if hasattr(request.data, 'getlist') else request.data.get('regions', [])
        logger.info(f"Regions data: {regions}")
        
        # 시리얼라이저에 regions 데이터 전달
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        """Set seller automatically when creating - 공구와 동일한 지역 처리 로직"""
        logger.info(f"perform_create called by user: {self.request.user}")
        
        # 중고폰 생성
        instance = serializer.save(seller=self.request.user)
        
        # 다중 지역 처리 (공구와 동일한 로직)
        regions_data = self.request.data.getlist('regions') if hasattr(self.request.data, 'getlist') else self.request.data.get('regions', [])
        
        if regions_data:
            from api.models import Region
            from used_phones.models import UsedPhoneRegion
            
            logger.info(f"[다중 지역 처리 시작] {len(regions_data)}개 지역 데이터 처리")
            
            for idx, region_data in enumerate(regions_data[:3]):  # 최대 3개
                try:
                    # 프론트엔드에서 전달된 데이터 파싱
                    if isinstance(region_data, str):
                        # "서울특별시 강남구" 형식
                        parts = region_data.split()
                        province = parts[0] if len(parts) > 0 else None
                        city = parts[1] if len(parts) > 1 else None
                        region_code = None
                        region_name = None
                    else:
                        # 딕셔너리 형식
                        region_code = region_data.get('code')
                        region_name = region_data.get('name')
                        province = region_data.get('province')
                        city = region_data.get('city')
                    
                    logger.info(f"[지역 {idx+1}] 처리 시작 - code: {region_code}, name: {region_name}, province: {province}, city: {city}")
                    
                    region = None
                    
                    if region_code:
                        # 1. 코드로 검색
                        region = Region.objects.filter(code=region_code).first()
                        if region:
                            logger.info(f"[지역 검색 성공 - 코드 매칭] {region.name} (코드: {region.code})")
                    
                    # 2. province/city로 검색
                    if not region and province and city:
                        # 지역명 매핑 (프론트엔드와 백엔드 데이터 불일치 해결)
                        province_mapping = {
                            '전북특별자치도': '전라북도',
                            '제주특별자치도': '제주도',
                            '강원특별자치도': '강원도'
                        }
                        city_mapping = {
                            '서귀포': '서귀포시',
                            '제주': '제주시'
                        }
                        
                        mapped_province = province_mapping.get(province, province)
                        mapped_city = city_mapping.get(city, city)
                        
                        logger.info(f"[province/city 검색 시도] {province} {city} -> {mapped_province} {mapped_city}")
                        
                        # 세종특별자치시 처리
                        if mapped_province == '세종특별자치시' and mapped_city == '세종시':
                            region = Region.objects.filter(
                                name='세종특별자치시',
                                level=1
                            ).first()
                            if region:
                                logger.info(f"[지역 검색 성공 - 특별자치시] {region.name} (코드: {region.code})")
                        
                        # 일반 지역 검색
                        if not region:
                            region = Region.objects.filter(
                                name=mapped_city,
                                parent__name=mapped_province,
                                level__in=[1, 2]
                            ).first()
                            
                            if region:
                                logger.info(f"[지역 검색 성공 - province/city] {region.name} (코드: {region.code})")
                            else:
                                # full_name으로 검색
                                full_name_search = f"{mapped_province} {mapped_city}"
                                region = Region.objects.filter(full_name=full_name_search).first()
                                if region:
                                    logger.info(f"[지역 검색 성공 - full_name] {region.name} (코드: {region.code})")
                                else:
                                    logger.warning(f"[지역 검색 실패] {mapped_province} {mapped_city}에 해당하는 지역을 찾을 수 없습니다.")
                    
                    if region:
                        # UsedPhoneRegion 생성
                        UsedPhoneRegion.objects.create(
                            used_phone=instance,
                            region=region
                        )
                        logger.info(f"[지역 추가 완료] {region.name} (코드: {region.code})")
                        
                        # 첫 번째 지역을 메인 지역으로 설정
                        if idx == 0:
                            instance.region = region
                            instance.region_name = region.name
                            instance.save(update_fields=['region', 'region_name'])
                            logger.info(f"[기본 지역 설정] {region.name}")
                    else:
                        logger.warning(f"[지역 추가 실패] 지역을 찾을 수 없습니다: {region_data}")
                        
                except Exception as e:
                    logger.error(f"[지역 처리 오류] {e}")
            
            logger.info(f"[다중 지역 처리 완료] 총 {UsedPhoneRegion.objects.filter(used_phone=instance).count()}개 지역 저장됨")
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count on detail view"""
        instance = self.get_object()
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        
        # F() expression 사용 후 객체 다시 로드
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Toggle favorite"""
        phone = self.get_object()
        favorite, created = UsedPhoneFavorite.objects.get_or_create(
            user=request.user,
            phone=phone
        )
        
        if not created:
            favorite.delete()
            phone.favorite_count = F('favorite_count') - 1
            phone.save(update_fields=['favorite_count'])
            phone.refresh_from_db()  # F() expression 사용 후 객체 다시 로드
            return Response({'status': 'unfavorited', 'favorite_count': phone.favorite_count})
        
        phone.favorite_count = F('favorite_count') + 1
        phone.save(update_fields=['favorite_count'])
        phone.refresh_from_db()  # F() expression 사용 후 객체 다시 로드
        return Response({'status': 'favorited', 'favorite_count': phone.favorite_count})
