"""
Used Phones API Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Avg, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import logging
from .models import (
    UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer,
    UsedPhoneDeletePenalty, UsedPhoneTransaction, UsedPhoneReview, TradeCancellation,
    UsedPhoneReport, UsedPhonePenalty
)

logger = logging.getLogger(__name__)
from .serializers import (
    UsedPhoneListSerializer, UsedPhoneDetailSerializer,
    UsedPhoneCreateSerializer, UsedPhoneOfferSerializer,
    UsedPhoneFavoriteSerializer, UsedPhoneTransactionSerializer,
    UsedPhoneReviewSerializer, UsedPhoneReportSerializer,
    UsedPhonePenaltySerializer, UserRatingSerializer
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
        
        # list 액션일 때는 deleted 상태만 제외하고 모든 상품 표시
        # active(판매중), trading(거래중), sold(판매완료) 모두 포함
        if self.action == 'list':
            queryset = queryset.exclude(status='deleted')
        
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
        offered_price = request.data.get('offered_price')
        if not offered_price:
            return Response(
                {'error': '제안 금액을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            offered_price = int(offered_price)
        except ValueError:
            return Response(
                {'error': '올바른 금액을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최소 제안가 체크
        if phone.min_offer_price and offered_price < phone.min_offer_price:
            return Response(
                {'error': f'최소 제안 금액은 {phone.min_offer_price}원입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 최대 990만원 제한
        if offered_price > 9900000:
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
        is_instant_purchase = (offered_price == phone.price)
        
        if existing_offer:
            # 기존 제안 업데이트
            existing_offer.offered_price = offered_price
            existing_offer.message = request.data.get('message', '')
            existing_offer.save()
            offer = existing_offer
        else:
            # 새 제안 생성
            offer = UsedPhoneOffer.objects.create(
                phone=phone,
                buyer=request.user,
                offered_price=offered_price,
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

            # UsedPhoneTransaction 생성
            from .models import UsedPhoneTransaction
            UsedPhoneTransaction.objects.create(
                phone=phone,
                offer=offer,
                seller=phone.seller,
                buyer=request.user,
                final_price=offer.offered_price,
                status='trading'
            )

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
            return Response({'message': 'No offer found', 'offer': None}, status=status.HTTP_200_OK)
        
        # 사용자의 총 제안 횟수 조회
        user_offer_count = UsedPhoneOffer.objects.filter(
            buyer=request.user,
            status='pending'
        ).count()
        
        return Response({
            'id': my_offer.id,
            'offered_price': my_offer.offered_price,
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
        
        # 디버깅: 모든 제안 상태 확인
        all_offers = UsedPhoneOffer.objects.filter(phone=phone)
        print(f"[DEBUG] Phone {phone.id} offers: {[(o.id, o.buyer.username, o.status) for o in all_offers]}")

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
                'offered_price': offer.offered_price,
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
            # 거래중이거나 판매완료된 상품 포함 (구매자가 완료하지 않은 경우)
            if phone.status == 'trading' or (phone.status == 'sold' and not phone.buyer_completed_at):
                main_image = phone.images.filter(is_main=True).first() or phone.images.first()

                # 트랜잭션 찾기
                transaction = UsedPhoneTransaction.objects.filter(
                    phone=phone,
                    buyer=request.user
                ).exclude(status='cancelled').order_by('-created_at').first()

                trading_items.append({
                    'id': transaction.id if transaction else offer.id,  # transaction ID 우선, 없으면 offer ID
                    'offer_id': offer.id,  # offer ID도 별도로 제공
                    'transaction_id': transaction.id if transaction else None,  # 명시적으로 transaction ID 제공
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
                        'seller_completed': bool(phone.seller_completed_at),
                        'buyer_completed': bool(phone.buyer_completed_at),
                        'seller': {
                            'id': phone.seller.id,
                            'nickname': phone.seller.nickname if hasattr(phone.seller, 'nickname') else phone.seller.username,
                            'phone': phone.seller.phone_number if hasattr(phone.seller, 'phone_number') else None,
                            'email': phone.seller.email,
                            'region': phone.seller.address_region.full_name if hasattr(phone.seller, 'address_region') and phone.seller.address_region else None,
                        }
                    },
                    'offered_price': offer.offered_price,
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
            'accepted_price': accepted_offer.offered_price
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
            'offered_price': accepted_offer.offered_price,  # API 응답 일관성을 위해 offered_price 사용
            'message': accepted_offer.message
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='complete-trade')
    def complete_trade(self, request, pk=None):
        """거래 완료 처리 (판매자/구매자 양방향 확인)"""
        phone = self.get_object()

        # 거래중 상태 확인
        if phone.status != 'trading':
            return Response(
                {'error': '거래중인 상품만 완료 처리할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 현재 거래 확인
        accepted_offer = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='accepted'
        ).first()

        if not accepted_offer:
            # 취소된 제안이 있는지 확인
            cancelled_offer = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='cancelled'
            ).order_by('-updated_at').first()

            if cancelled_offer:
                return Response(
                    {'error': '거래가 이미 취소되었습니다. 목록을 새로고침해주세요.',
                     'code': 'transaction_already_cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 거래 당사자 확인
        is_seller = phone.seller == request.user
        is_buyer = accepted_offer.buyer == request.user

        if not is_seller and not is_buyer:
            return Response(
                {'error': '거래 당사자만 완료 처리할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 거래 레코드 찾기 또는 생성
        transaction, created = UsedPhoneTransaction.objects.get_or_create(
            phone=phone,
            offer=accepted_offer,
            defaults={
                'seller': phone.seller,
                'buyer': accepted_offer.buyer,
                'final_price': accepted_offer.offered_price,  # amount로 수정
                'status': 'trading'
            }
        )

        # 당근마켓 방식: 판매자만 거래완료 처리
        if is_seller:
            if not transaction.seller_confirmed:
                # 판매자 확인 시 자동으로 구매자도 확인 처리
                transaction.seller_confirmed = True
                transaction.buyer_confirmed = True  # 자동 설정
                transaction.seller_confirmed_at = timezone.now()
                transaction.buyer_confirmed_at = timezone.now()
                transaction.status = 'completed'
                transaction.save()

                # 상품 상태를 sold로 변경
                phone.status = 'sold'
                phone.sold_at = timezone.now()
                phone.save(update_fields=['status', 'sold_at'])

                return Response({
                    'message': '거래가 완료되었습니다.',
                    'status': 'completed',
                    'transaction_id': transaction.id
                })
            else:
                return Response({
                    'message': '이미 거래가 완료되었습니다.',
                    'status': 'already_completed'
                })
        elif is_buyer:
            # 구매자는 거래완료 버튼 없음
            return Response(
                {'error': '구매자는 거래완료를 처리할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='transaction-info')
    def transaction_info(self, request, pk=None):
        """거래 정보 조회 (후기 작성용)"""
        from .models import UsedPhoneTransaction

        phone = self.get_object()

        # 거래중이거나 완료된 상태가 아니면 조회 불가
        if phone.status not in ['trading', 'sold']:
            return Response(
                {'error': '거래 정보가 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 현재 진행중인 거래 찾기
        transaction = UsedPhoneTransaction.objects.filter(
            phone=phone,
            status__in=['completed', 'in_progress', 'trading']
        ).select_related('buyer', 'seller').first()

        if not transaction:
            # 거래 내역이 없으면 accepted offer에서 정보 가져와서 transaction 생성
            accepted_offer = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='accepted'
            ).select_related('buyer').first()

            if not accepted_offer:
                return Response(
                    {'error': '거래 정보를 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 거래중/판매완료 상태에서는 반드시 transaction이 있어야 함 - 생성
            transaction = UsedPhoneTransaction.objects.create(
                phone=phone,
                offer=accepted_offer,
                seller=phone.seller,
                buyer=accepted_offer.buyer,
                final_price=accepted_offer.offered_price,
                status='completed' if phone.status == 'sold' else 'trading',
                seller_confirmed=True if phone.status == 'sold' else False,
                buyer_confirmed=True if phone.status == 'sold' else False,
                seller_confirmed_at=timezone.now() if phone.status == 'sold' else None,
                buyer_confirmed_at=timezone.now() if phone.status == 'sold' else None
            )

        # 거래 정보 반환
        return Response({
            'id': transaction.id,
            'buyer': {
                'id': transaction.buyer.id,
                'nickname': transaction.buyer.nickname if hasattr(transaction.buyer, 'nickname') else transaction.buyer.username
            },
            'seller': {
                'id': transaction.seller.id,
                'nickname': transaction.seller.nickname if hasattr(transaction.seller, 'nickname') else transaction.seller.username
            },
            'final_price': transaction.final_price,
            'status': transaction.status
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

        # 판매자가 이미 완료한 경우 취소 불가 (당근마켓 방식)
        if phone.seller_completed_at:
            return Response(
                {'error': '판매자가 거래를 확정한 후에는 취소할 수 없습니다.'},
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

        # UsedPhoneTransaction이 있다면 상태 업데이트
        from .models import UsedPhoneTransaction
        transaction = UsedPhoneTransaction.objects.filter(
            phone=phone,
            offer=accepted_offer,
            status__in=['trading', 'in_progress']
        ).first()

        if transaction:
            transaction.status = 'cancelled'
            transaction.save(update_fields=['status'])

        # 취소 처리
        if is_buyer:
            # 구매자가 취소 - 상품은 자동으로 판매중으로
            phone.status = 'active'
            phone.save(update_fields=['status'])

            # 해당 제안만 취소 상태로
            accepted_offer.status = 'cancelled'
            accepted_offer.save()

            # offer_count 업데이트 (pending 상태만 카운트)
            unique_buyers_count = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='pending'
            ).values('buyer').distinct().count()
            phone.offer_count = unique_buyers_count
            phone.save(update_fields=['offer_count'])

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

                # offer_count 업데이트 (pending 상태만 카운트)
                unique_buyers_count = UsedPhoneOffer.objects.filter(
                    phone=phone,
                    status='pending'
                ).values('buyer').distinct().count()
                phone.offer_count = unique_buyers_count
                phone.save(update_fields=['offer_count'])

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
        
        # offer_count 업데이트 (pending 상태만 카운트)
        phone = offer.phone
        unique_buyers_count = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'  # pending 상태만 카운트
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
                'offered_price': offer.offered_price,
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
                'offered_price': offer.offered_price,
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

            # UsedPhoneTransaction 생성 (취소된 거래가 있어도 새로 생성)
            from .models import UsedPhoneTransaction

            # 기존 trading 상태 트랜잭션이 있는지 확인
            existing_trading = UsedPhoneTransaction.objects.filter(
                phone=offer.phone,
                offer=offer,
                status='trading'
            ).first()

            if not existing_trading:
                # 취소된 트랜잭션이 있더라도 새로운 트랜잭션 생성
                UsedPhoneTransaction.objects.create(
                    phone=offer.phone,
                    offer=offer,
                    seller=offer.phone.seller,
                    buyer=offer.buyer,
                    final_price=offer.offered_price,
                    status='trading'
                )

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


class UsedPhoneTransactionViewSet(viewsets.ModelViewSet):
    """중고폰 거래 ViewSet"""
    queryset = UsedPhoneTransaction.objects.all()
    serializer_class = UsedPhoneTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 거래만 반환"""
        user = self.request.user
        return UsedPhoneTransaction.objects.filter(
            Q(seller=user) | Q(buyer=user)
        ).select_related('phone', 'offer', 'seller', 'buyer')

    @action(detail=False, methods=['get'], url_path='my-transactions')
    def my_transactions(self, request):
        """내 거래 목록"""
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """거래 확인"""
        transaction = self.get_object()

        # 거래 당사자 확인
        is_seller = transaction.seller == request.user
        is_buyer = transaction.buyer == request.user

        if not is_seller and not is_buyer:
            return Response(
                {'error': '거래 당사자만 확인할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 확인 처리
        if is_seller:
            transaction.seller_confirmed = True
            transaction.seller_confirmed_at = timezone.now()
        else:
            transaction.buyer_confirmed = True
            transaction.buyer_confirmed_at = timezone.now()

        transaction.save()

        # 양방향 확인 시 거래 완료
        if transaction.complete_trade():
            return Response({
                'message': '거래가 완료되었습니다.',
                'status': 'completed'
            })

        return Response({
            'message': '거래 확인이 등록되었습니다.',
            'seller_confirmed': transaction.seller_confirmed,
            'buyer_confirmed': transaction.buyer_confirmed
        })


class UsedPhoneReviewViewSet(viewsets.ModelViewSet):
    """중고폰 거래 후기 ViewSet"""
    queryset = UsedPhoneReview.objects.all()
    serializer_class = UsedPhoneReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자 관련 리뷰만 반환"""
        user = self.request.user
        return UsedPhoneReview.objects.filter(
            Q(reviewer=user) | Q(reviewee=user)
        ).select_related('transaction', 'reviewer', 'reviewee')

    def create(self, request, *args, **kwargs):
        """리뷰 작성"""
        # 디버깅을 위한 로깅 추가
        print(f"[DEBUG] Review creation request data: {request.data}")

        transaction_id = request.data.get('transaction')
        print(f"[DEBUG] Extracted transaction_id: {transaction_id}, type: {type(transaction_id)}")

        # transaction_id가 없거나 잘못된 형식인 경우 체크
        if not transaction_id:
            return Response(
                {'error': 'transaction_id가 제공되지 않았습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # transaction_id를 정수로 변환 시도
            transaction_id = int(transaction_id)
            print(f"[DEBUG] Converted transaction_id to int: {transaction_id}")

            # 모든 트랜잭션 확인 (디버깅용)
            all_transactions = UsedPhoneTransaction.objects.all()
            print(f"[DEBUG] All transaction IDs in DB: {list(all_transactions.values_list('id', flat=True))}")

            transaction = UsedPhoneTransaction.objects.get(id=transaction_id)
        except UsedPhoneTransaction.DoesNotExist:
            return Response(
                {'error': '거래를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 거래 완료 확인
        if transaction.status != 'completed':
            return Response(
                {'error': '거래가 완료된 후에만 리뷰를 작성할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 리뷰어와 리뷰이 결정
        if transaction.seller == request.user:
            reviewee = transaction.buyer
        elif transaction.buyer == request.user:
            reviewee = transaction.seller
        else:
            return Response(
                {'error': '거래 당사자만 리뷰를 작성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 이미 리뷰를 작성했는지 확인
        existing_review = UsedPhoneReview.objects.filter(
            transaction=transaction,
            reviewer=request.user
        ).first()

        if existing_review:
            return Response(
                {'error': '이미 리뷰를 작성하셨습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 리뷰 생성
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            transaction=transaction,
            reviewer=request.user,
            reviewee=reviewee
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='user-stats')
    def user_stats(self, request):
        """사용자 평가 통계"""
        try:
            # 사용자 ID 가져오기 (쿼리 파라미터 또는 현재 로그인 사용자)
            user_id = request.query_params.get('user_id')
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = request.user
                if not user.is_authenticated:
                    return Response(
                        {'error': '로그인이 필요합니다.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )

            # 받은 리뷰 통계
            reviews = UsedPhoneReview.objects.filter(reviewee=user)

            # 기본 통계값 설정
            stats = {
                'avg_rating': 0.0,
                'total_reviews': 0,
                'five_star': 0,
                'four_star': 0,
                'three_star': 0,
                'two_star': 0,
                'one_star': 0,
                'is_punctual_count': 0,
                'is_friendly_count': 0,
                'is_honest_count': 0,
                'is_fast_response_count': 0
            }

            if reviews.exists():
                # 집계 통계
                aggregated = reviews.aggregate(
                    avg_rating=Avg('rating'),
                    total_reviews=Count('id'),
                    five_star=Count('id', filter=Q(rating=5)),
                    four_star=Count('id', filter=Q(rating=4)),
                    three_star=Count('id', filter=Q(rating=3)),
                    two_star=Count('id', filter=Q(rating=2)),
                    one_star=Count('id', filter=Q(rating=1))
                )
                stats.update(aggregated)

                # 평가 항목 통계
                stats['is_punctual_count'] = reviews.filter(is_punctual=True).count()
                stats['is_friendly_count'] = reviews.filter(is_friendly=True).count()
                stats['is_honest_count'] = reviews.filter(is_honest=True).count()
                stats['is_fast_response_count'] = reviews.filter(is_fast_response=True).count()

            return Response(stats)

        except User.DoesNotExist:
            return Response(
                {'error': '사용자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'통계 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


class UsedPhoneReportViewSet(viewsets.ModelViewSet):
    """중고폰 신고 ViewSet"""
    queryset = UsedPhoneReport.objects.all()
    serializer_class = UsedPhoneReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """권한에 따른 쿼리셋 필터링"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            # 관리자는 모든 신고 조회 가능
            return UsedPhoneReport.objects.select_related(
                'reported_user', 'reporter', 'processed_by'
            ).prefetch_related('penalties')
        else:
            # 일반 사용자는 자신이 제출한 신고만 조회 가능
            return UsedPhoneReport.objects.filter(
                reporter=user
            ).select_related('reported_user', 'processed_by')

    def perform_create(self, serializer):
        """신고 생성"""
        # 신고자를 현재 사용자로 설정
        serializer.save(reporter=self.request.user)

        # 자동 패널티 처리 로직
        reported_user = serializer.validated_data['reported_user']
        self._check_auto_penalty(reported_user, serializer.instance)

    def _check_auto_penalty(self, reported_user, current_report):
        """신고 누적에 따른 자동 패널티 처리"""
        # 최근 30일 내 해당 사용자에 대한 신고 수 확인
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)

        recent_reports = UsedPhoneReport.objects.filter(
            reported_user=reported_user,
            created_at__gte=thirty_days_ago,
            status__in=['pending', 'processing', 'resolved']
        )

        report_count = recent_reports.count()

        # 3건 이상 신고 시 자동 7일 패널티
        if report_count >= 3:
            # 이미 활성 패널티가 있는지 확인
            active_penalty = reported_user.used_phone_penalties.filter(
                status='active'
            ).first()

            if not active_penalty or not active_penalty.is_active():
                penalty = UsedPhonePenalty.objects.create(
                    user=reported_user,
                    penalty_type='auto_report',
                    reason=f'신고 누적 {report_count}건으로 인한 자동 패널티',
                    duration_days=7,
                    issued_by=None  # 시스템 자동 발령
                )

                # 관련 신고들을 패널티에 연결
                penalty.related_reports.set(recent_reports)

                logger.info(f"사용자 {reported_user.username}에게 자동 패널티 부여 (신고 {report_count}건)")

    @action(detail=False, methods=['get'])
    def my_reports(self, request):
        """내가 제출한 신고 목록"""
        reports = self.get_queryset().filter(reporter=request.user)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)


class UsedPhonePenaltyViewSet(viewsets.ModelViewSet):
    """중고폰 패널티 ViewSet"""
    queryset = UsedPhonePenalty.objects.all()
    serializer_class = UsedPhonePenaltySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['penalty_type', 'status', 'user']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """권한에 따른 쿼리셋 필터링"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            # 관리자는 모든 패널티 조회 가능
            return UsedPhonePenalty.objects.select_related(
                'user', 'issued_by', 'revoked_by'
            ).prefetch_related('related_reports')
        else:
            # 일반 사용자는 자신의 패널티만 조회 가능
            return UsedPhonePenalty.objects.filter(user=user)

    def perform_create(self, serializer):
        """패널티 생성 (관리자만)"""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionError("관리자만 패널티를 생성할 수 있습니다.")

        serializer.save(issued_by=self.request.user)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """패널티 해제 (관리자만)"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "관리자만 패널티를 해제할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN
            )

        penalty = self.get_object()
        if penalty.status == 'active':
            penalty.status = 'revoked'
            penalty.revoked_by = request.user
            penalty.revoked_at = timezone.now()
            penalty.save()

            return Response({"message": "패널티가 해제되었습니다."})
        else:
            return Response(
                {"error": "이미 만료되거나 해제된 패널티입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def my_penalties(self, request):
        """내 패널티 목록"""
        penalties = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(penalties, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check_active(self, request):
        """현재 활성 패널티 확인"""
        user = request.user
        active_penalty = user.used_phone_penalties.filter(status='active').first()

        if active_penalty and active_penalty.is_active():
            serializer = self.get_serializer(active_penalty)
            return Response({
                'has_active_penalty': True,
                'penalty': serializer.data
            })
        else:
            return Response({'has_active_penalty': False})


class UserRatingView(APIView):
    """사용자 평점 정보 API"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, user_id):
        """특정 사용자의 평점 정보 조회"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
            serializer = UserRatingSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "사용자를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )


# 간단한 리뷰 작성 API - 기존 ViewSet과 별도로 작동
from rest_framework.decorators import api_view, permission_classes

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_simple_review(request):
    """
    간단한 리뷰 작성 API
    기존 ViewSet이 작동하지 않을 때 대체용
    """
    print(f"[SIMPLE REVIEW] Request data: {request.data}")
    print(f"[SIMPLE REVIEW] User: {request.user}")

    try:
        transaction_id = request.data.get('transaction')
        rating = request.data.get('rating', 5)
        comment = request.data.get('comment', '')

        # transaction_id 검증
        if not transaction_id:
            return Response(
                {'error': 'transaction_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Transaction 찾기
        try:
            transaction = UsedPhoneTransaction.objects.get(id=transaction_id)
        except UsedPhoneTransaction.DoesNotExist:
            # Transaction이 없으면 Offer ID로 시도
            try:
                offer = UsedPhoneOffer.objects.get(id=transaction_id, status='accepted')
                # Offer에서 phone과 buyer를 통해 transaction 찾기
                transaction = UsedPhoneTransaction.objects.filter(
                    phone=offer.phone,
                    buyer=offer.buyer
                ).exclude(status='cancelled').first()

                if not transaction:
                    # Transaction이 없으면 생성 (거래는 진행중이지만 트랜잭션이 없는 경우)
                    transaction = UsedPhoneTransaction.objects.create(
                        phone=offer.phone,
                        seller=offer.phone.seller,
                        buyer=offer.buyer,
                        price=offer.offered_price,
                        status='completed'
                    )
                    print(f"[SIMPLE REVIEW] Created transaction from offer: {transaction.id}")
            except UsedPhoneOffer.DoesNotExist:
                # Offer도 없으면 Phone ID로 시도
                try:
                    phone = UsedPhone.objects.get(id=transaction_id)
                    transaction = UsedPhoneTransaction.objects.filter(
                        phone=phone,
                        status='completed'
                    ).first()
                    if not transaction:
                        return Response(
                            {'error': f'거래를 찾을 수 없습니다. (ID: {transaction_id})'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                except:
                    return Response(
                        {'error': f'거래를 찾을 수 없습니다. (ID: {transaction_id})'},
                        status=status.HTTP_404_NOT_FOUND
                    )

        # 거래 당사자 확인
        if transaction.seller == request.user:
            reviewer = transaction.seller
            reviewee = transaction.buyer
        elif transaction.buyer == request.user:
            reviewer = transaction.buyer
            reviewee = transaction.seller
        else:
            return Response(
                {'error': '거래 당사자만 리뷰를 작성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 이미 리뷰를 작성했는지 확인
        existing_review = UsedPhoneReview.objects.filter(
            transaction=transaction,
            reviewer=reviewer
        ).first()

        if existing_review:
            return Response(
                {'error': '이미 리뷰를 작성하셨습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 리뷰 생성
        review = UsedPhoneReview.objects.create(
            transaction=transaction,
            reviewer=reviewer,
            reviewee=reviewee,
            rating=rating,
            comment=comment,
            # 평가 태그들 (선택사항)
            is_punctual=request.data.get('is_punctual', False),
            is_friendly=request.data.get('is_friendly', False),
            is_honest=request.data.get('is_honest', False),
            is_fast_response=request.data.get('is_fast_response', False),
        )

        print(f"[SIMPLE REVIEW] Created review: {review.id}")

        return Response({
            'id': review.id,
            'message': '리뷰가 성공적으로 작성되었습니다.',
            'rating': review.rating,
            'comment': review.comment
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"[SIMPLE REVIEW] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'리뷰 작성 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
