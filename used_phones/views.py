"""
Used Phones API Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import logging
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer, UsedPhoneDeletePenalty

logger = logging.getLogger(__name__)
from .serializers import (
    UsedPhoneListSerializer, UsedPhoneDetailSerializer, 
    UsedPhoneCreateSerializer, UsedPhoneOfferSerializer,
    UsedPhoneFavoriteSerializer
)


class UsedPhoneViewSet(viewsets.ModelViewSet):
    """Used Phone ViewSet"""
    queryset = UsedPhone.objects.filter(status__in=['active', 'trading']).prefetch_related(
        'regions__region',  # prefetch regions to avoid N+1 queries
        'images',
        'favorites'
    ).select_related('seller', 'region')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'description']
    ordering_fields = ['price', 'created_at', 'view_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """지역 필터링 추가"""
        queryset = super().get_queryset()
        
        # list 액션일 때는 active 상태만 보여주기
        # detail 액션이나 다른 action들은 trading 상태도 포함
        if self.action == 'list':
            queryset = queryset.filter(status='active')
        
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def offer(self, request, pk=None):
        """가격 제안하기"""
        phone = self.get_object()
        
        # 거래중인 상품에는 제안 불가
        if phone.status == 'trading':
            return Response(
                {'error': '거래중인 상품에는 제안할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 본인 상품에는 제안 불가
        if phone.seller == request.user:
            return Response(
                {'error': '본인 상품에는 제안할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 제안 횟수 체크 (상품당 5회)
        offer_count = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user
        ).count()
        
        if offer_count >= 5:
            return Response(
                {'error': '해당 상품에 최대 5회까지만 제안 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 제안 금액 검증
        amount = request.data.get('amount')
        if not amount:
            return Response(
                {'error': '제안 금액을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = int(amount)
        except ValueError:
            return Response(
                {'error': '올바른 금액을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최소 제안가 체크
        if phone.min_offer_price and amount < phone.min_offer_price:
            return Response(
                {'error': f'최소 제안 금액은 {phone.min_offer_price}원입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최대 990만원 제한
        if amount > 9900000:
            return Response(
                {'error': '최대 제안 가능 금액은 990만원입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이전 제안이 있는지 확인
        existing_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user,
            status='pending'
        ).first()
        
        # 즉시구매 여부 확인 (즉시판매가와 동일한 금액 제안)
        is_instant_purchase = (amount == phone.price)
        
        if existing_offer:
            # 기존 제안 업데이트
            existing_offer.amount = amount
            existing_offer.message = request.data.get('message', '')
            existing_offer.save()
            offer = existing_offer
        else:
            # 새 제안 생성
            offer = UsedPhoneOffer.objects.create(
                phone=phone,
                buyer=request.user,
                amount=amount,
                message=request.data.get('message', '')
            )
            
            # 유니크한 구매자 수로 offer_count 업데이트
            unique_buyers_count = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='pending'
            ).values('buyer').distinct().count()
            
            phone.offer_count = unique_buyers_count
            phone.save(update_fields=['offer_count'])
        
        # 즉시구매인 경우 자동으로 거래중 상태로 전환
        if is_instant_purchase:
            # 제안 자동 수락
            offer.status = 'accepted'
            offer.save()
            
            # 상품 상태를 거래중으로 변경
            phone.status = 'trading'
            phone.save(update_fields=['status'])
            
            # 다른 제안들은 그대로 pending 상태 유지 (거절하지 않음)
            
            # 즉시구매 응답
            return Response({
                'message': '즉시구매가 완료되었습니다. 판매자와 연락처가 공개됩니다.',
                'type': 'instant_purchase',
                'offer': UsedPhoneOfferSerializer(offer).data,
                'seller_contact': {
                    'phone': phone.seller.phone if hasattr(phone.seller, 'phone') else None,
                    'email': phone.seller.email
                }
            }, status=status.HTTP_201_CREATED)
        
        serializer = UsedPhoneOfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def offer_count(self, request, pk=None):
        """사용자의 제안 횟수 조회"""
        phone = self.get_object()
        count = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user
        ).count()
        
        return Response({'count': count})
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-offer')
    def my_offer(self, request, pk=None):
        """내가 제안한 금액 조회"""
        phone = self.get_object()
        
        # 내가 제안한 최신 제안 조회
        my_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user
        ).order_by('-created_at').first()
        
        if not my_offer:
            return Response({'message': 'No offer found'}, status=status.HTTP_404_NOT_FOUND)
        
        # 사용자의 총 제안 횟수 조회
        user_offer_count = UsedPhoneOffer.objects.filter(
            buyer=request.user,
            status='pending'
        ).count()
        
        return Response({
            'id': my_offer.id,
            'amount': my_offer.amount,
            'message': my_offer.message,
            'status': my_offer.status,
            'created_at': my_offer.created_at,
            'user_offer_count': user_offer_count
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def offers(self, request, pk=None):
        """상품에 대한 제안 목록 조회 (판매자만 가능)"""
        phone = self.get_object()
        
        # 판매자 본인만 조회 가능
        if phone.seller != request.user:
            return Response(
                {'error': '판매자만 제안 목록을 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 각 구매자별 최신 제안만 가져오기
        from django.db.models import Max, OuterRef, Subquery
        
        # 각 구매자의 최신 제안 ID를 가져옴
        latest_offer_ids = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'  # pending 상태만 표시
        ).values('buyer').annotate(
            latest_id=Max('id')
        ).values('latest_id')
        
        # 최신 제안들만 조회
        offers = UsedPhoneOffer.objects.filter(
            id__in=latest_offer_ids
        ).select_related('buyer').order_by('-created_at')
        
        # 직렬화
        offers_data = []
        for offer in offers:
            offers_data.append({
                'id': offer.id,
                'buyer': {
                    'id': offer.buyer.id,
                    'nickname': offer.buyer.nickname if hasattr(offer.buyer, 'nickname') else offer.buyer.username,
                    'profile_image': offer.buyer.profile_image if hasattr(offer.buyer, 'profile_image') else None
                },
                'offered_price': offer.amount,
                'message': offer.message,
                'status': offer.status,
                'created_at': offer.created_at
            })
        
        return Response(offers_data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-listings')
    def my_listings(self, request):
        """내 판매 상품 목록 조회 (MyPage용)"""
        status_filter = request.query_params.get('status')
        
        queryset = UsedPhone.objects.filter(
            seller=request.user
        ).exclude(status='deleted').prefetch_related('images', 'offers').select_related('region')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset.order_by('-created_at')
        
        # 페이지네이션 적용
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UsedPhoneListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = UsedPhoneListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='check-limit')
    def check_limit(self, request):
        """등록 제한 체크 (활성 상품 5개 및 패널티)"""
        from django.utils import timezone
        from datetime import timedelta
        
        # 활성 상품 개수
        active_count = UsedPhone.objects.filter(
            seller=request.user,
            status='active'
        ).count()
        
        # 패널티 체크
        active_penalty = UsedPhoneDeletePenalty.objects.filter(
            user=request.user,
            penalty_end__gt=timezone.now()
        ).first()
        
        can_register = active_count < 5 and not active_penalty
        
        response_data = {
            'active_count': active_count,
            'can_register': can_register,
            'penalty_end': active_penalty.penalty_end.isoformat() if active_penalty else None
        }
        
        return Response(response_data)
    
    def destroy(self, request, *args, **kwargs):
        """삭제 처리 (패널티 적용)"""
        from django.utils import timezone
        from datetime import timedelta
        
        instance = self.get_object()
        
        # 권한 체크
        if instance.seller != request.user:
            return Response(
                {'error': '삭제 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 견적 제안 여부 체크
        has_offers = instance.offers.exists()
        
        if has_offers:
            # 6시간 패널티 적용
            penalty_end = timezone.now() + timedelta(hours=6)
            UsedPhoneDeletePenalty.objects.create(
                user=request.user,
                phone_model=instance.model,
                had_offers=True,
                penalty_end=penalty_end
            )
            
            # 모든 제안을 취소 상태로 변경
            instance.offers.update(status='cancelled')
        
        # 상태를 deleted로 변경 (실제 삭제하지 않음)
        instance.status = 'deleted'
        instance.save(update_fields=['status'])
        
        return Response({
            'message': '상품이 삭제되었습니다.',
            'penalty_applied': has_offers,
            'penalty_end': penalty_end.isoformat() if has_offers else None
        })
    
    def update(self, request, *args, **kwargs):
        """수정 처리 (견적 후 제한 적용)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 권한 체크
        if instance.seller != request.user:
            return Response(
                {'error': '수정 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 견적이 있는 경우 수정 가능 필드 제한
        has_offers = instance.offers.exists()
        
        if has_offers:
            # 수정 가능한 필드만 허용
            allowed_fields = ['price', 'description', 'meeting_place']
            
            # 수정 불가능한 필드 체크
            restricted_fields = []
            for field in request.data.keys():
                if field not in allowed_fields and field not in ['existing_images', 'new_images']:
                    restricted_fields.append(field)
            
            if restricted_fields:
                return Response(
                    {'error': f'견적 제안 후에는 다음 필드를 수정할 수 없습니다: {", ".join(restricted_fields)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 수정됨 플래그 설정
            instance.is_modified = True
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-trading')
    def my_trading(self, request):
        """구매자의 거래중 목록 조회"""
        # 현재 사용자가 구매자이고 accepted 상태인 제안들 찾기
        accepted_offers = UsedPhoneOffer.objects.filter(
            buyer=request.user,
            status='accepted'
        ).select_related('phone', 'phone__seller').prefetch_related('phone__images')
        
        print(f"[DEBUG] my_trading - User: {request.user.username}, Accepted offers count: {accepted_offers.count()}")
        
        trading_items = []
        for offer in accepted_offers:
            phone = offer.phone
            print(f"[DEBUG] Offer ID: {offer.id}, Phone ID: {phone.id}, Phone status: {phone.status}")
            # 거래중 상태인 상품만 포함
            if phone.status == 'trading':
                main_image = phone.images.filter(is_main=True).first() or phone.images.first()
                
                trading_items.append({
                    'id': offer.id,
                    'phone': {
                        'id': phone.id,
                        'title': f"{phone.brand} {phone.model}",
                        'brand': phone.brand,
                        'model': phone.model,
                        'price': phone.price,
                        'images': [{
                            'image_url': main_image.image_url if main_image else None,
                            'is_main': True
                        }] if main_image else [],
                        'status': phone.status,
                        'seller': {
                            'id': phone.seller.id,
                            'nickname': phone.seller.nickname if hasattr(phone.seller, 'nickname') else phone.seller.username,
                            'phone': phone.seller.phone_number if hasattr(phone.seller, 'phone_number') else None,
                            'email': phone.seller.email,
                            'region': phone.seller.address_region.full_name if hasattr(phone.seller, 'address_region') and phone.seller.address_region else None,
                        }
                    },
                    'offered_price': offer.amount,
                    'status': offer.status,
                    'created_at': offer.created_at.isoformat()
                })
        
        return Response(trading_items)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='seller-info')
    def seller_info(self, request, pk=None):
        """거래중인 판매자 정보 조회 (구매자용)"""
        phone = self.get_object()
        
        # 거래중 상태가 아니면 조회 불가
        if phone.status != 'trading':
            return Response(
                {'error': '거래중인 상품만 판매자 정보를 조회할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 수락된 제안이 현재 사용자의 것인지 확인
        accepted_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user,
            status='accepted'
        ).first()
        
        if not accepted_offer:
            return Response(
                {'error': '거래 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        seller = phone.seller
        
        # 판매자 정보 반환
        return Response({
            'id': seller.id,
            'nickname': seller.nickname if hasattr(seller, 'nickname') else seller.username,
            'phone': seller.phone_number if hasattr(seller, 'phone_number') else None,
            'email': seller.email,
            'region': seller.address_region.full_name if hasattr(seller, 'address_region') and seller.address_region else None,
            'profile_image': seller.profile_image if hasattr(seller, 'profile_image') else None,
            'accepted_price': accepted_offer.amount
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='buyer-info')
    def buyer_info(self, request, pk=None):
        """거래중인 구매자 정보 조회 (판매자용)"""
        phone = self.get_object()
        
        # 판매자만 조회 가능
        if phone.seller != request.user:
            return Response(
                {'error': '판매자만 구매자 정보를 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 거래중 상태가 아니면 조회 불가
        if phone.status != 'trading':
            return Response(
                {'error': '거래중인 상품만 구매자 정보를 조회할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 수락된 제안 찾기
        accepted_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='accepted'
        ).select_related('buyer').first()
        
        if not accepted_offer:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        buyer = accepted_offer.buyer
        
        # 구매자 정보 반환
        return Response({
            'id': buyer.id,
            'nickname': buyer.nickname if hasattr(buyer, 'nickname') else buyer.username,
            'phone': buyer.phone_number if hasattr(buyer, 'phone_number') else None,
            'email': buyer.email,
            'region': buyer.address_region.full_name if hasattr(buyer, 'address_region') and buyer.address_region else None,
            'profile_image': buyer.profile_image if hasattr(buyer, 'profile_image') else None,
            'offered_price': accepted_offer.amount,
            'message': accepted_offer.message
        })



class UsedPhoneOfferViewSet(viewsets.ModelViewSet):
    """중고폰 제안 ViewSet"""
    queryset = UsedPhoneOffer.objects.all()
    serializer_class = UsedPhoneOfferSerializer
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        """제안 취소 (구매자 본인만 가능)"""
        offer = self.get_object()
        
        # 본인의 제안만 취소 가능
        if offer.buyer != request.user:
            return Response(
                {'error': '본인의 제안만 취소할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # pending 상태만 취소 가능
        if offer.status != 'pending':
            return Response(
                {'error': '대기중인 제안만 취소할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 제안 삭제
        offer.delete()
        
        # offer_count 업데이트
        phone = offer.phone
        unique_buyers_count = UsedPhoneOffer.objects.filter(
            phone=phone
        ).values('buyer').distinct().count()
        
        phone.offer_count = unique_buyers_count
        phone.save(update_fields=['offer_count'])
        
        return Response(
            {'message': '제안이 취소되었습니다.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'], url_path='sent')
    def sent_offers(self, request):
        """내가 보낸 제안 목록 (구매자 MyPage용)"""
        status_filter = request.query_params.get('status')
        
        queryset = UsedPhoneOffer.objects.filter(
            buyer=request.user
        ).select_related('phone', 'phone__seller').prefetch_related('phone__images')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset.order_by('-created_at')
        
        # 제안 데이터 직렬화
        offers_data = []
        for offer in queryset:
            phone = offer.phone
            main_image = phone.images.filter(is_main=True).first() or phone.images.first()
            
            offers_data.append({
                'id': offer.id,
                'phone': {
                    'id': phone.id,
                    'title': f"{phone.brand} {phone.model}",
                    'brand': phone.brand,
                    'model': phone.model,
                    'price': phone.price,
                    'status': phone.status,  # 상품 상태 추가
                    'images': [{
                        'image_url': main_image.image_url if main_image else None,
                        'is_main': True
                    }] if main_image else [],
                    'seller': {
                        'nickname': phone.seller.nickname if hasattr(phone.seller, 'nickname') else phone.seller.username
                    }
                },
                'offered_price': offer.amount,
                'message': offer.message,
                'status': offer.status,
                'created_at': offer.created_at
            })
        
        return Response({'results': offers_data})
    
    @action(detail=False, methods=['get'], url_path='received')
    def received_offers(self, request):
        """받은 제안 목록 (판매자 MyPage용)"""
        phone_id = request.query_params.get('phone_id')
        
        # 내 상품에 대한 제안만 조회
        my_phones = UsedPhone.objects.filter(seller=request.user).values_list('id', flat=True)
        queryset = UsedPhoneOffer.objects.filter(
            phone__id__in=my_phones
        ).select_related('buyer', 'phone').prefetch_related('phone__images')
        
        if phone_id:
            queryset = queryset.filter(phone__id=phone_id)
        
        queryset = queryset.order_by('-created_at')
        
        # 제안 데이터 직렬화
        offers_data = []
        for offer in queryset:
            offers_data.append({
                'id': offer.id,
                'buyer': {
                    'id': offer.buyer.id,
                    'nickname': offer.buyer.nickname if hasattr(offer.buyer, 'nickname') else offer.buyer.username,
                    'profile_image': offer.buyer.profile_image if hasattr(offer.buyer, 'profile_image') else None
                },
                'offered_price': offer.amount,
                'message': offer.message,
                'status': offer.status,
                'created_at': offer.created_at,
                'phone_id': offer.phone.id
            })
        
        return Response({'results': offers_data})
    
    @action(detail=True, methods=['post'], url_path='respond')
    def respond_to_offer(self, request, pk=None):
        """제안 응답 (수락/거절)"""
        offer = self.get_object()
        action = request.data.get('action')  # 'accept' or 'reject'
        message = request.data.get('message', '')
        
        # 판매자 본인만 응답 가능
        if offer.phone.seller != request.user:
            return Response(
                {'error': '판매자만 제안에 응답할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 응답한 제안인지 확인
        if offer.status != 'pending':
            return Response(
                {'error': '이미 응답한 제안입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 제안 응답 처리 (거절 제거, 수락만 처리)
        if action == 'accept':
            # 제안 수락 = 즉시 거래중으로 전환
            offer.status = 'accepted'
            offer.phone.status = 'trading'
            offer.phone.save(update_fields=['status'])
            
            # 다른 pending 제안들은 그대로 유지 (나중에 다시 수락 가능)
        else:
            return Response(
                {'error': '올바른 응답 유형을 선택해주세요. (accept만 가능)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        offer.seller_message = message
        offer.save(update_fields=['status', 'seller_message'])
        
        return Response({
            'message': '제안이 수락되어 거래가 시작되었습니다.',
            'status': offer.status,
            'phone_status': offer.phone.status
        })
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_offer(self, request, pk=None):
        """제안 취소"""
        offer = self.get_object()
        
        # 본인 제안인지 확인
        if offer.buyer != request.user:
            return Response(
                {"error": "본인의 제안만 취소할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 취소된 제안인지 확인
        if offer.status == "cancelled":
            return Response(
                {"error": "이미 취소된 제안입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 제안 취소
        offer.status = "cancelled"
        offer.save(update_fields=["status"])
        
        # 유니크한 구매자 수로 offer_count 업데이트
        phone = offer.phone
        unique_buyers_count = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'
        ).values('buyer').distinct().count()
        
        phone.offer_count = unique_buyers_count
        phone.save(update_fields=['offer_count'])
        
        return Response({
            "message": "제안이 취소되었습니다.",
            "status": offer.status
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='seller-complete')
    def seller_complete(self, request, pk=None):
        """판매자 거래 완료 처리"""
        phone = self.get_object()
        
        # 판매자만 가능
        if phone.seller != request.user:
            return Response(
                {'error': '판매자만 판매 완료할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 거래중 상태가 아니면 완료 불가
        if phone.status != 'trading':
            return Response(
                {'error': '거래중인 상품만 완료 처리할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이미 판매 완료한 경우
        if phone.seller_completed_at:
            return Response(
                {'error': '이미 판매 완료 처리하셨습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 판매자 완료 시간 기록 및 상태를 판매완료로 변경
        phone.seller_completed_at = timezone.now()
        phone.status = 'sold'
        phone.sold_at = timezone.now()
        phone.save(update_fields=['seller_completed_at', 'status', 'sold_at'])
        
        return Response({
            'message': '판매가 완료되었습니다.',
            'status': phone.status,
            'seller_completed': True
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='buyer-complete')
    def buyer_complete(self, request, pk=None):
        """구매자 거래 완료 처리"""
        phone = self.get_object()
        
        # 거래중 상태가 아니면 완료 불가
        if phone.status != 'trading' and phone.status != 'sold':
            return Response(
                {'error': '거래중이거나 판매완료된 상품만 구매 완료할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 구매자 확인 - 수락된 제안의 구매자인지 확인
        accepted_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            buyer=request.user,
            status='accepted'
        ).first()
        
        if not accepted_offer:
            return Response(
                {'error': '구매자만 구매 완료할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 구매 완료한 경우
        if phone.buyer_completed_at:
            return Response(
                {'error': '이미 구매 완료 처리하셨습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 구매자 완료 시간 기록
        phone.buyer_completed_at = timezone.now()
        phone.save(update_fields=['buyer_completed_at'])
        
        return Response({
            'message': '구매가 완료되었습니다.',
            'buyer_completed': True
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='cancel-trade')
    def cancel_trade(self, request, pk=None):
        """거래 취소 처리 (판매자/구매자 모두 가능)"""
        from .models import TradeCancellation
        
        phone = self.get_object()
        
        # 거래중 상태가 아니면 취소 불가
        if phone.status != 'trading':
            return Response(
                {'error': '거래중인 상품만 취소할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 현재 수락된 제안 찾기
        accepted_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='accepted'
        ).first()
        
        if not accepted_offer:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 판매자 또는 구매자만 취소 가능
        is_seller = phone.seller == request.user
        is_buyer = accepted_offer.buyer == request.user
        
        if not is_seller and not is_buyer:
            return Response(
                {'error': '거래 당사자만 취소할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 취소 사유 받기
        reason = request.data.get('reason', 'other')
        custom_reason = request.data.get('custom_reason', '')
        return_to_sale = request.data.get('return_to_sale', True)  # 판매자의 경우 판매중으로 전환 여부
        
        # 취소 기록 저장
        TradeCancellation.objects.create(
            phone=phone,
            offer=accepted_offer,
            cancelled_by='seller' if is_seller else 'buyer',
            canceller=request.user,
            reason=reason,
            custom_reason=custom_reason if reason == 'other' else None
        )
        
        # 취소 처리
        if is_buyer:
            # 구매자가 취소 - 상품은 자동으로 판매중으로
            phone.status = 'active'
            phone.save(update_fields=['status'])
            
            # 해당 제안만 취소 상태로
            accepted_offer.status = 'cancelled'
            accepted_offer.save()
            
            message = '구매자가 거래를 취소했습니다. 상품이 다시 판매중 상태로 변경되었습니다.'
        else:
            # 판매자가 취소
            if return_to_sale:
                # 판매중으로 전환
                phone.status = 'active'
                phone.save(update_fields=['status'])
                
                # 제안을 취소 상태로 (다른 제안들은 pending 유지)
                accepted_offer.status = 'cancelled'
                accepted_offer.save()
                
                message = '거래가 취소되었습니다. 상품이 다시 판매중 상태로 변경되었습니다.'
            else:
                # 상품 삭제
                phone.status = 'deleted'
                phone.save(update_fields=['status'])
                
                # 모든 제안을 취소 상태로 변경
                UsedPhoneOffer.objects.filter(
                    phone=phone,
                    status__in=['pending', 'accepted']
                ).update(status='cancelled')
                
                message = '거래가 취소되고 상품이 삭제되었습니다.'
        
        return Response({
            'message': message,
            'status': phone.status,
            'cancelled_by': 'buyer' if is_buyer else 'seller'
        })


class UsedPhoneFavoriteViewSet(viewsets.ModelViewSet):
    """중고폰 찜 ViewSet"""
    queryset = UsedPhoneFavorite.objects.all()
    serializer_class = UsedPhoneFavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 찜 목록만 반환"""
        return UsedPhoneFavorite.objects.filter(
            user=self.request.user
        ).select_related('phone', 'phone__seller').prefetch_related('phone__images')
    
    def list(self, request):
        """찜 목록 조회 (MyPage용)"""
        queryset = self.get_queryset().order_by('-created_at')
        
        # 찜 데이터 직렬화
        favorites_data = []
        for favorite in queryset:
            phone = favorite.phone
            main_image = phone.images.filter(is_main=True).first() or phone.images.first()
            
            favorites_data.append({
                'id': favorite.id,
                'phone': {
                    'id': phone.id,
                    'title': f"{phone.brand} {phone.model}",
                    'brand': phone.brand,
                    'model': phone.model,
                    'price': phone.price,
                    'status': phone.status,  # 상품 상태 추가
                    'images': [{
                        'image_url': main_image.image_url if main_image else None,
                        'is_main': True
                    }] if main_image else [],
                    'seller': {
                        'nickname': phone.seller.nickname if hasattr(phone.seller, 'nickname') else phone.seller.username
                    }
                },
                'created_at': favorite.created_at
            })
        
        return Response({'results': favorites_data})
