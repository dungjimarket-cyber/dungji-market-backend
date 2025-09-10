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
        """Set seller automatically when creating"""
        logger.info(f"perform_create called by user: {self.request.user}")
        
        # 중고폰 생성
        instance = serializer.save(seller=self.request.user)
        
        # regions 데이터 처리
        regions = self.request.data.getlist('regions') if hasattr(self.request.data, 'getlist') else self.request.data.get('regions', [])
        
        if regions:
            from api.models import Region
            from used_phones.models import UsedPhoneRegion
            from django.db.models import Q
            
            logger.info(f"Processing {len(regions)} regions")
            
            for region_str in regions[:3]:  # 최대 3개까지
                try:
                    # "서울특별시 강남구" 형태의 문자열 파싱
                    parts = region_str.split()
                    if len(parts) >= 2:
                        province = parts[0]
                        city = parts[1] if len(parts) > 1 else ""
                        
                        # 정확한 full_name 매칭 시도
                        region = Region.objects.filter(full_name=region_str).first()
                        
                        # 없으면 시도와 시군구 모두 포함하는 것 검색
                        if not region:
                            region = Region.objects.filter(
                                Q(full_name__contains=province) & Q(full_name__contains=city)
                            ).first()
                        
                        # 그래도 없으면 시군구만으로 검색
                        if not region and city:
                            region = Region.objects.filter(name=city).first()
                        
                        if region:
                            UsedPhoneRegion.objects.create(
                                used_phone=instance,
                                region=region
                            )
                            logger.info(f"지역 추가 성공: {region.full_name}")
                        else:
                            logger.warning(f"지역을 찾을 수 없음: {region_str}")
                except Exception as e:
                    logger.error(f"지역 처리 실패 ({region_str}): {e}")
    
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
