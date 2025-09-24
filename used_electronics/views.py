"""
전자제품/가전 Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from .models import (
    UsedElectronics, ElectronicsImage, ElectronicsOffer,
    ElectronicsTransaction
)
from api.models_unified_simple import (
    UnifiedFavorite, UnifiedReview, UnifiedDeletePenalty,
    UnifiedReport, UnifiedPenalty
)
from .serializers import (
    ElectronicsListSerializer, ElectronicsDetailSerializer,
    ElectronicsCreateUpdateSerializer, ElectronicsOfferSerializer
)
import logging

logger = logging.getLogger(__name__)


class UsedElectronicsViewSet(viewsets.ModelViewSet):
    """전자제품/가전 ViewSet"""

    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['brand', 'model_name', 'description']
    ordering_fields = ['price', 'created_at', 'view_count', 'offer_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """쿼리셋 반환 - UsedPhone과 동일한 로직 적용"""
        # list와 retrieve 액션은 sold 포함 (조회는 가능)
        if self.action in ['list', 'retrieve']:
            # 디버깅 로그 추가
            logger.info(f"[UsedElectronicsViewSet] Action: {self.action}")
            logger.info(f"[UsedElectronicsViewSet] Including sold items in queryset")

            queryset = UsedElectronics.objects.exclude(status='deleted')

            # 쿼리셋 상태 확인
            logger.info(f"[UsedElectronicsViewSet] Queryset count: {queryset.count()}")
            sold_count = queryset.filter(status='sold').count()
            logger.info(f"[UsedElectronicsViewSet] Sold items in queryset: {sold_count}")
        else:
            # 다른 액션들(update, delete 등)은 active와 trading만 접근 가능
            queryset = UsedElectronics.objects.filter(
                status__in=['active', 'trading']
            )

        # 관련 데이터 미리 로드 (N+1 쿼리 방지)
        queryset = queryset.select_related('seller', 'region', 'transaction')
        queryset = queryset.prefetch_related('images', 'regions__region')

        # 필터링
        subcategory = self.request.query_params.get('subcategory', None)
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)

        min_price = self.request.query_params.get('min_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get('max_price', None)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        condition = self.request.query_params.get('condition', None)
        if condition:
            queryset = queryset.filter(condition_grade=condition)

        # 지역 필터링 - UsedPhone과 동일한 방식 적용
        region = self.request.query_params.get('region', None)
        if region:
            from api.models import Region
            from django.db.models import Q

            # 상위 지역(시/도)인지 확인
            parent_region = Region.objects.filter(
                name=region,
                parent_id__isnull=True  # parent_id가 null이면 상위 지역
            ).first()

            if parent_region:
                # 상위 지역인 경우: 해당 지역과 모든 하위 지역 포함
                sub_regions = Region.objects.filter(parent_id=parent_region.pk)
                region_codes = [parent_region.pk] + list(sub_regions.values_list('pk', flat=True))

                queryset = queryset.filter(
                    Q(regions__region__code__in=region_codes) |  # ElectronicsRegion을 통한 다중 지역
                    Q(region__code__in=region_codes)  # 메인 region 필드
                ).distinct()
            else:
                # 하위 지역이거나 정확한 매칭
                queryset = queryset.filter(
                    Q(regions__region__name__icontains=region) |  # name으로 검색
                    Q(regions__region__full_name__icontains=region) |  # full_name으로 검색
                    Q(region__name__icontains=region) |  # 메인 region의 name
                    Q(region__full_name__icontains=region)  # 메인 region의 full_name
                ).distinct()

        # include_completed 파라미터 처리 (거래완료 포함/제외)
        # retrieve 액션(상세조회)에서는 include_completed 파라미터 무시
        if self.action == 'list':
            include_completed = self.request.query_params.get('include_completed')
            # 기본값: 거래완료 제외
            # include_completed가 'true'일 때만 거래완료 포함
            if include_completed != 'true':
                # 거래완료 제외 (기본값)
                queryset = queryset.exclude(status='sold')

        # 내 상품만 보기 (판매자용)
        if self.action == 'my_list':
            queryset = UsedElectronics.objects.filter(seller=self.request.user)

        return queryset

    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 클래스 반환"""
        if self.action == 'list' or self.action == 'my_list':
            return ElectronicsListSerializer
        elif self.action == 'retrieve':
            return ElectronicsDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ElectronicsCreateUpdateSerializer
        return ElectronicsListSerializer

    def retrieve(self, request, *args, **kwargs):
        """상세 조회 - 조회수 증가"""
        instance = self.get_object()

        # 조회수 증가 (본인 제외)
        if request.user != instance.seller:
            instance.view_count += 1
            instance.save(update_fields=['view_count'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """생성 시 판매자 설정"""
        # 등록 제한 체크 (최대 5개)
        active_count = UsedElectronics.objects.filter(
            seller=self.request.user,
            status__in=['active', 'trading']
        ).count()

        if active_count >= 5:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('최대 5개까지만 등록 가능합니다.')

        serializer.save(seller=self.request.user)

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

        # 거래중인 경우 삭제 불가
        if instance.status == 'trading':
            return Response(
                {'error': '거래중인 상품은 삭제할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 견적 제안 여부 체크
        has_offers = instance.offers.exists()

        if has_offers:
            # 6시간 패널티 적용
            penalty_end = timezone.now() + timedelta(hours=6)
            UnifiedDeletePenalty.objects.create(
                user=request.user,
                item_name=f"{instance.brand} {instance.model_name}",
                item_type='electronics',
                had_offers=True,
                penalty_end=penalty_end
            )

            # 모든 제안을 취소 상태로 변경
            instance.offers.update(status='cancelled')

        # 상태를 deleted로 변경 (실제 삭제하지 않음)
        instance.status = 'deleted'
        instance.save(update_fields=['status'])

        response_data = {'message': '삭제되었습니다.'}
        if has_offers:
            response_data['penalty'] = '견적이 있는 상품을 삭제하여 6시간 동안 등록이 제한됩니다.'

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_list(self, request):
        """내 상품 목록"""
        # my_list는 내 상품이므로 모든 status를 포함해야 함
        queryset = UsedElectronics.objects.filter(seller=request.user)

        # 관련 데이터 미리 로드
        queryset = queryset.select_related('seller')
        queryset = queryset.prefetch_related('images', 'regions__region')

        # status 필터링 (쿼리 파라미터로 받음)
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 최신순으로 정렬
        queryset = queryset.order_by('-created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def check_limit(self, request):
        """등록 제한 체크"""
        from django.utils import timezone

        # 활성 상품 수 체크
        active_count = UsedElectronics.objects.filter(
            seller=request.user,
            status='active'
        ).count()

        # 패널티 체크
        active_penalty = UnifiedDeletePenalty.objects.filter(
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def offer(self, request, pk=None):
        """가격 제안"""
        electronics = self.get_object()

        # 거래중인 상품에는 제안 불가
        if electronics.status == 'trading':
            return Response(
                {'error': '거래중인 상품에는 제안할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 본인 상품에는 제안 불가
        if electronics.seller == request.user:
            return Response(
                {'error': '본인 상품에는 제안할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 제안 횟수 체크 (상품당 5회) - 모든 제안 카운트 (cancelled 포함)
        offer_count = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user
        ).count()
        if offer_count >= 5:
            return Response(
                {'error': '해당 상품에 최대 5회까지만 제안 가능합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 제안 금액 검증
        offered_price = request.data.get('offered_price')  # 프론트엔드와 일치
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
        if electronics.min_offer_price and offered_price < electronics.min_offer_price:
            return Response(
                {'error': f'최소 제안 금액은 {electronics.min_offer_price:,}원입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 즉시 구매가보다 높으면 차단 (같은 경우는 즉시구매로 허용)
        if offered_price > electronics.price:
            return Response(
                {'error': f'제안 금액은 즉시 구매가({electronics.price:,}원)를 초과할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 기존 제안 취소 처리
        existing_offer = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user,
            status='pending'
        ).first()

        # 즉시구매 여부 확인 (즉시판매가와 동일한 금액 제안)
        is_instant_purchase = (offered_price == electronics.price)

        if existing_offer:
            # 기존 제안은 cancelled로 변경하고 새로 생성
            existing_offer.status = 'cancelled'
            existing_offer.save()

        # 항상 새 제안 생성
        offer = ElectronicsOffer.objects.create(
            electronics=electronics,
            buyer=request.user,
            offer_price=offered_price,
            message=request.data.get('message', '')
        )

        # 제안 수 업데이트 (유니크한 구매자 수)
        unique_buyers_count = ElectronicsOffer.objects.filter(
            electronics=electronics,
            status='pending'
        ).values('buyer').distinct().count()

        electronics.offer_count = unique_buyers_count
        electronics.save(update_fields=['offer_count'])

        # 즉시구매인 경우 자동으로 거래중 상태로 전환
        if is_instant_purchase:
            # 제안 자동 수락
            offer.status = 'accepted'
            offer.save()

            # 상품 상태를 거래중으로 변경
            electronics.status = 'trading'
            electronics.save(update_fields=['status'])

            # 기존 취소된 거래가 있는지 확인하고 삭제 또는 업데이트
            try:
                existing_transaction = ElectronicsTransaction.objects.get(
                    electronics=electronics
                )
                # 기존 거래가 취소 상태인 경우 재사용
                if existing_transaction.status == 'cancelled':
                    existing_transaction.buyer = request.user
                    existing_transaction.seller = electronics.seller
                    existing_transaction.final_price = offer.offer_price
                    existing_transaction.status = 'in_progress'
                    existing_transaction.cancelled_by = None
                    existing_transaction.cancellation_reason = ''
                    existing_transaction.cancellation_detail = ''
                    existing_transaction.save()
                else:
                    # 이미 진행중인 거래가 있으면 에러
                    return Response(
                        {'error': '이미 진행중인 거래가 있습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ElectronicsTransaction.DoesNotExist:
                # 거래가 없으면 새로 생성
                ElectronicsTransaction.objects.create(
                    electronics=electronics,
                    seller=electronics.seller,
                    buyer=request.user,
                    final_price=offer.offer_price,
                    status='in_progress'
                )

            # 다른 제안들은 그대로 pending 상태 유지

            # 즉시구매 응답
            return Response({
                'message': '즉시구매가 완료되었습니다. 판매자와 연락처가 공개됩니다.',
                'type': 'instant_purchase',
                'offer': ElectronicsOfferSerializer(offer).data,
                'seller_contact': {
                    'phone': electronics.seller.phone if hasattr(electronics.seller, 'phone') else None,
                    'email': electronics.seller.email
                }
            }, status=status.HTTP_201_CREATED)

        serializer = ElectronicsOfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def my_offer(self, request, pk=None):
        """내가 제안한 금액 조회"""
        electronics = self.get_object()

        # 내가 제안한 최신 제안 조회
        my_offer = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user
        ).order_by('-created_at').first()

        if not my_offer:
            return Response({'message': 'No offer found', 'offer': None}, status=status.HTTP_200_OK)

        # 해당 상품에 대한 사용자의 제안 횟수 조회
        user_offer_count = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user
        ).count()

        return Response({
            'id': my_offer.id,
            'offered_price': my_offer.offer_price,  # 프론트엔드와 일치
            'message': my_offer.message,
            'status': my_offer.status,
            'created_at': my_offer.created_at,
            'user_offer_count': user_offer_count
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def offer_count(self, request, pk=None):
        """사용자의 제안 횟수 조회"""
        electronics = self.get_object()
        count = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user
        ).count()
        return Response({'count': count})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def offers(self, request, pk=None):
        """상품에 대한 제안 목록 조회 (판매자만 가능)"""
        electronics = self.get_object()

        # 판매자 본인만 조회 가능
        if electronics.seller != request.user:
            return Response(
                {'error': '판매자만 제안 목록을 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 각 구매자별 최신 제안만 가져오기
        from django.db.models import Max, OuterRef, Subquery

        # 각 구매자의 최신 제안 ID를 가져옴
        latest_offer_ids = ElectronicsOffer.objects.filter(
            electronics=electronics,
            status='pending'  # pending 상태만 표시
        ).values('buyer').annotate(
            latest_id=Max('id')
        ).values('latest_id')

        # 최신 제안들만 조회
        offers = ElectronicsOffer.objects.filter(
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
                'offered_price': offer.offer_price,  # 프론트엔드와 일치하도록 필드명 변경
                'message': offer.message,
                'status': offer.status,
                'created_at': offer.created_at
            })

        return Response(offers_data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """찜하기/찜 해제 - 통합 모델 사용"""
        electronics = self.get_object()

        if request.method == 'POST':
            # 찜하기
            favorite, created = UnifiedFavorite.objects.get_or_create(
                user=request.user,
                item_type='electronics',
                item_id=electronics.id
            )

            if created:
                # 찜 카운트 증가
                electronics.favorite_count = UnifiedFavorite.objects.filter(
                    item_type='electronics',
                    item_id=electronics.id
                ).count()
                electronics.save(update_fields=['favorite_count'])

                return Response({'status': 'favorited', 'message': '찜 목록에 추가되었습니다.'})
            else:
                return Response({'status': 'already_favorited', 'message': '이미 찜한 상품입니다.'})

        elif request.method == 'DELETE':
            # 찜 해제
            deleted_count, _ = UnifiedFavorite.objects.filter(
                user=request.user,
                item_type='electronics',
                item_id=electronics.id
            ).delete()

            if deleted_count > 0:
                # 찜 카운트 감소
                electronics.favorite_count = UnifiedFavorite.objects.filter(
                    item_type='electronics',
                    item_id=electronics.id
                ).count()
                electronics.save(update_fields=['favorite_count'])

                return Response({'status': 'unfavorited', 'message': '찜 목록에서 제거되었습니다.'})
            else:
                return Response({'status': 'not_favorited', 'message': '찜하지 않은 상품입니다.'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        """찜 목록 - 통합 모델 사용"""
        favorites = UnifiedFavorite.objects.filter(
            user=request.user,
            item_type='electronics'
        )

        # 찜 목록 데이터 구성
        result = []
        for favorite in favorites:
            electronics = favorite.get_item()
            if electronics:
                result.append({
                    'id': favorite.id,
                    'electronics': ElectronicsListSerializer(electronics).data,
                    'created_at': favorite.created_at
                })

        return Response({'results': result})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def accept_offer(self, request, pk=None):
        """제안 수락 (판매자)"""
        electronics = self.get_object()
        offer_id = request.data.get('offer_id')

        # 판매자 확인
        if electronics.seller != request.user:
            return Response(
                {'error': '판매자만 수락할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            offer = ElectronicsOffer.objects.get(id=offer_id, electronics=electronics)
        except ElectronicsOffer.DoesNotExist:
            return Response(
                {'error': '제안을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 제안 수락
        offer.status = 'accepted'
        offer.save()

        # 다른 제안들 거절
        ElectronicsOffer.objects.filter(
            electronics=electronics
        ).exclude(id=offer_id).update(status='rejected')

        # 상품 상태 변경
        electronics.status = 'trading'
        electronics.save()

        # 거래 생성
        ElectronicsTransaction.objects.create(
            electronics=electronics,
            seller=electronics.seller,
            buyer=offer.buyer,
            final_price=offer.offer_price
        )

        return Response({'message': '제안을 수락했습니다.'})

    @action(detail=True, methods=['post'], url_path='complete-trade', permission_classes=[IsAuthenticated])
    def complete_transaction(self, request, pk=None):
        """거래 완료 (판매자)"""
        # get_object() 대신 직접 조회 (거래중 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 거래 정보 확인
        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '진행 중인 거래를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 판매자만 거래 완료 가능
        if transaction.seller != request.user:
            return Response(
                {'error': '판매자만 거래를 완료할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 이미 완료된 거래인지 확인
        if transaction.seller_completed:
            return Response({
                'message': '이미 거래가 완료되었습니다.',
                'status': 'already_completed'
            })

        # 판매자 완료 처리 시 자동으로 구매자도 완료 처리
        from django.utils import timezone
        now = timezone.now()

        transaction.seller_completed = True
        transaction.buyer_completed = True  # 자동 설정
        transaction.seller_completed_at = now
        transaction.buyer_completed_at = now
        transaction.status = 'completed'
        transaction.completed_at = now
        transaction.save()

        # 상품 상태를 sold로 변경
        electronics.status = 'sold'
        electronics.sold_at = now
        electronics.save()

        return Response({
            'message': '거래가 완료되었습니다.',
            'status': 'completed',
            'transaction_id': transaction.id
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_listings(self, request):
        """내 판매 상품 목록 조회"""
        status_filter = request.query_params.get('status')
        queryset = UsedElectronics.objects.filter(seller=request.user)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = queryset.order_by('-created_at')
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='offers/received', permission_classes=[IsAuthenticated])
    def received_offers(self, request):
        """받은 제안 목록 조회 (판매자)"""
        offers = ElectronicsOffer.objects.filter(
            electronics__seller=request.user,
            status='pending'
        ).select_related('electronics', 'buyer')

        page = self.paginate_queryset(offers)
        if page is not None:
            serializer = ElectronicsOfferSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ElectronicsOfferSerializer(offers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='offers/(?P<offer_id>[^/.]+)/respond', permission_classes=[IsAuthenticated])
    def respond_to_offer(self, request, offer_id=None):
        """제안 응답 (수락/거절) - 휴대폰과 동일한 로직"""
        action = request.data.get('action')  # 'accept' or 'reject'
        message = request.data.get('message', '')

        try:
            offer = ElectronicsOffer.objects.get(
                id=offer_id,
                electronics__seller=request.user
            )
        except ElectronicsOffer.DoesNotExist:
            return Response(
                {'error': '제안을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
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
            offer.electronics.status = 'trading'
            offer.electronics.save(update_fields=['status'])

            # 기존 거래가 있는지 확인 (OneToOneField 때문에 하나만 존재 가능)
            try:
                existing_transaction = ElectronicsTransaction.objects.get(
                    electronics=offer.electronics
                )
                # 기존 거래가 취소 상태인 경우 재사용
                if existing_transaction.status == 'cancelled':
                    existing_transaction.buyer = offer.buyer
                    existing_transaction.seller = offer.electronics.seller
                    existing_transaction.final_price = offer.offer_price
                    existing_transaction.status = 'in_progress'
                    existing_transaction.cancelled_by = None
                    existing_transaction.cancellation_reason = ''
                    existing_transaction.cancellation_detail = ''
                    existing_transaction.save()
                else:
                    # 이미 진행중인 거래가 있으면 에러
                    return Response(
                        {'error': '이미 진행중인 거래가 있습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ElectronicsTransaction.DoesNotExist:
                # 거래가 없으면 새로 생성
                ElectronicsTransaction.objects.create(
                    electronics=offer.electronics,
                    seller=offer.electronics.seller,
                    buyer=offer.buyer,
                    final_price=offer.offer_price,  # 전자제품은 offer_price
                    status='in_progress'  # 전자제품은 in_progress
                )

            # 다른 pending 제안들은 그대로 유지 (나중에 다시 수락 가능)
        else:
            return Response(
                {'error': '잘못된 액션입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        offer.save(update_fields=['status'])
        return Response({'message': '제안을 수락했습니다.', 'status': offer.status})


    @action(detail=True, methods=['get'], url_path='buyer-info', permission_classes=[IsAuthenticated])
    def buyer_info(self, request, pk=None):
        """구매자 정보 조회 (거래중인 판매자용)"""
        # get_object() 대신 직접 조회 (거래중 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if electronics.seller != request.user:
            return Response(
                {'error': '판매자만 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        buyer = transaction.buyer

        # 전자제품의 제안 찾기 (거래 시작 시 수락된 제안)
        accepted_offer = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=buyer,
            status='accepted'
        ).first()

        # 구매자 정보 반환 (휴대폰과 동일한 형식)
        return Response({
            'id': buyer.id,
            'nickname': buyer.nickname if hasattr(buyer, 'nickname') else buyer.username,
            'phone': buyer.phone_number if hasattr(buyer, 'phone_number') else None,
            'email': buyer.email,
            'region': buyer.address_region.full_name if hasattr(buyer, 'address_region') and buyer.address_region else None,
            'profile_image': buyer.profile_image if hasattr(buyer, 'profile_image') else None,
            'offered_price': transaction.final_price,  # 거래 가격
            'message': accepted_offer.message if accepted_offer else ''  # 제안 메시지
        })

    @action(detail=True, methods=['get'], url_path='seller-info', permission_classes=[IsAuthenticated])
    def seller_info(self, request, pk=None):
        """판매자 정보 조회 (거래중인 구매자용)"""
        # get_object() 대신 직접 조회 (거래중 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                buyer=request.user,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        seller = electronics.seller

        # 전자제품의 제안 찾기 (거래 시작 시 수락된 제안)
        accepted_offer = ElectronicsOffer.objects.filter(
            electronics=electronics,
            buyer=request.user,
            status='accepted'
        ).first()

        # 판매자 정보 반환 (휴대폰과 동일한 형식)
        return Response({
            'id': seller.id,
            'nickname': seller.nickname if hasattr(seller, 'nickname') else seller.username,
            'phone': seller.phone_number if hasattr(seller, 'phone_number') else None,
            'email': seller.email,
            'region': seller.address_region.full_name if hasattr(seller, 'address_region') and seller.address_region else None,
            'profile_image': seller.profile_image if hasattr(seller, 'profile_image') else None,
            'offered_price': transaction.final_price,  # 거래 가격
            'message': accepted_offer.message if accepted_offer else ''  # 제안 메시지
        })

    @action(detail=True, methods=['get'], url_path='transaction-info', permission_classes=[IsAuthenticated])
    def transaction_info(self, request, pk=None):
        """거래 정보 조회 (후기 작성용)"""
        # get_object() 대신 직접 조회 (거래완료 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                status='completed'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '완료된 거래가 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 거래 당사자인지 확인
        if request.user not in [transaction.seller, transaction.buyer]:
            return Response(
                {'error': '거래 당사자만 조회할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        transaction_data = {
            'id': transaction.id,
            'electronics_id': electronics.id,
            'seller_id': transaction.seller.id,
            'buyer_id': transaction.buyer.id,
            'final_price': transaction.final_price,
            'completed_at': transaction.completed_at
        }

        return Response(transaction_data)

    @action(detail=True, methods=['post'], url_path='seller-complete', permission_classes=[IsAuthenticated])
    def seller_complete(self, request, pk=None):
        """판매 완료 (판매자용)"""
        electronics = self.get_object()

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                seller=request.user,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 판매자 완료 처리 - 당근마켓 방식: 판매자가 완료하면 자동으로 거래 완료
        from django.utils import timezone
        now = timezone.now()

        transaction.seller_completed = True
        transaction.buyer_completed = True  # 자동 완료
        transaction.seller_completed_at = now
        transaction.buyer_completed_at = now
        transaction.status = 'completed'
        transaction.completed_at = now

        # 상품 상태도 sold로 변경
        electronics.status = 'sold'
        electronics.sold_at = now
        electronics.save(update_fields=['status', 'sold_at'])

        transaction.save()

        return Response({'message': '거래가 완료되었습니다.'})

    @action(detail=True, methods=['post'], url_path='buyer-complete', permission_classes=[IsAuthenticated])
    def buyer_complete(self, request, pk=None):
        """구매 완료 (구매자용)"""
        # get_object() 대신 직접 조회 (거래중 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                buyer=request.user,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 구매자는 거래 완료 버튼이 없음 - 판매자만 최종 완료 가능
        return Response(
            {'error': '구매자는 거래를 완료할 수 없습니다. 판매자가 거래를 완료해야 합니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['post'], url_path='cancel-trade', permission_classes=[IsAuthenticated])
    def cancel_trade(self, request, pk=None):
        """거래 취소"""
        # get_object() 대신 직접 조회 (거래중 상태도 포함)
        try:
            electronics = UsedElectronics.objects.get(pk=pk)
        except UsedElectronics.DoesNotExist:
            return Response(
                {'error': '전자제품을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        reason = request.data.get('reason', '')
        custom_reason = request.data.get('custom_reason', '')
        return_to_sale = request.data.get('return_to_sale', True)  # 기본값 True

        try:
            transaction = ElectronicsTransaction.objects.get(
                electronics=electronics,
                status='in_progress'
            )
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 거래 당사자인지 확인
        if request.user not in [transaction.seller, transaction.buyer]:
            return Response(
                {'error': '거래 당사자만 취소할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # 거래 취소
            transaction.status = 'cancelled'
            transaction.cancelled_by = request.user
            transaction.cancellation_reason = reason if reason else 'other'
            transaction.cancellation_detail = custom_reason if custom_reason else ''
            transaction.save()

            # return_to_sale이 True인 경우 상품을 다시 활성으로 (판매자/구매자 모두)
            if return_to_sale:
                electronics.status = 'active'
                electronics.save()

            # 제안 상태도 초기화
            ElectronicsOffer.objects.filter(
                electronics=electronics,
                status='accepted'
            ).update(status='cancelled')

            return Response({'message': '거래가 취소되었습니다.'})
        except Exception as e:
            logger.error(f"거래 취소 중 오류 발생: {str(e)}")
            return Response(
                {'error': f'거래 취소 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='my-offers', permission_classes=[IsAuthenticated])
    def my_sent_offers(self, request):
        """내가 보낸 제안 목록 조회 (구매자)"""
        status_filter = request.query_params.get('status')

        offers = ElectronicsOffer.objects.filter(buyer=request.user)

        if status_filter:
            offers = offers.filter(status=status_filter)

        offers = offers.select_related('electronics', 'electronics__seller').prefetch_related('electronics__images')
        offers = offers.order_by('-created_at')

        # 제안 데이터 직렬화 (휴대폰과 동일한 구조로)
        offers_data = []
        for offer in offers:
            electronics = offer.electronics
            main_image = electronics.images.filter(is_primary=True).first() or electronics.images.first()
            offers_data.append({
                'id': offer.id,
                'electronics': {
                    'id': electronics.id,
                    'brand': electronics.brand,
                    'model_name': electronics.model_name,
                    'price': electronics.price,
                    'status': electronics.status,  # 상품 상태 추가
                    'images': [{
                        'imageUrl': main_image.image.url if main_image and main_image.image else None,
                        'is_primary': True
                    }] if main_image else [],
                    'seller': {
                        'nickname': electronics.seller.nickname if hasattr(electronics.seller, 'nickname') else electronics.seller.username
                    }
                },
                'offered_price': offer.offer_price,  # 프론트엔드 기대 필드명으로 매핑
                'message': offer.message,
                'status': offer.status,
                'created_at': offer.created_at
            })

        return Response({'results': offers_data})

    @action(detail=False, methods=['get'], url_path='my-trading', permission_classes=[IsAuthenticated])
    def my_trading_items(self, request):
        """내 거래중 목록 조회 (구매자)"""
        # 현재 사용자가 구매자이고 accepted 상태인 제안들 찾기
        accepted_offers = ElectronicsOffer.objects.filter(
            buyer=request.user,
            status='accepted'
        ).select_related('electronics', 'electronics__seller').prefetch_related('electronics__images')

        print(f"[DEBUG] Electronics my_trading - User: {request.user.username}, Accepted offers count: {accepted_offers.count()}")

        trading_items = []
        for offer in accepted_offers:
            electronics = offer.electronics
            print(f"[DEBUG] Offer ID: {offer.id}, Electronics ID: {electronics.id}, Electronics status: {electronics.status}")
            # 트랜잭션 찾기
            transaction = ElectronicsTransaction.objects.filter(
                electronics=electronics,
                buyer=request.user
            ).exclude(status='cancelled').order_by('-created_at').first()

            # 거래중이거나 판매완료된 상품 포함 (구매자가 완료하지 않은 경우)
            if electronics.status == 'trading' or (electronics.status == 'sold' and transaction and not transaction.buyer_completed):
                main_image = electronics.images.filter(is_primary=True).first() or electronics.images.first()

                # 리뷰 작성 여부 확인 (에러 방지)
                has_review = False
                try:
                    if transaction and electronics.status == 'sold':
                        has_review = UnifiedReview.objects.filter(
                            item_type='electronics',
                            transaction_id=transaction.id,
                            reviewer=request.user
                        ).exists()
                except Exception as e:
                    print(f"[ERROR] Failed to check review status: {e}")
                    has_review = False

                trading_items.append({
                    'id': transaction.id if transaction else offer.id,  # transaction ID 우선, 없으면 offer ID
                    'offer_id': offer.id,  # offer ID도 별도로 제공
                    'transaction_id': transaction.id if transaction else None,  # 명시적으로 transaction ID 제공
                    'has_review': has_review,  # 후기 작성 여부
                    'electronics': {
                        'id': electronics.id,
                        'brand': electronics.brand,
                        'model_name': electronics.model_name,
                        'price': electronics.price,
                        'images': [{
                            'imageUrl': main_image.image.url if main_image and main_image.image else None,
                            'is_primary': True
                        }] if main_image else [],
                        'status': electronics.status,
                        'seller_completed': transaction.seller_completed if transaction else False,
                        'buyer_completed': transaction.buyer_completed if transaction else False,
                        'seller': {
                            'id': electronics.seller.id,
                            'nickname': electronics.seller.nickname if hasattr(electronics.seller, 'nickname') else electronics.seller.username,
                            'phone': electronics.seller.phone_number if hasattr(electronics.seller, 'phone_number') else None,
                            'email': electronics.seller.email,
                            'region': electronics.seller.address_region.full_name if hasattr(electronics.seller, 'address_region') and electronics.seller.address_region else None,
                        }
                    },
                    'offered_price': offer.offer_price,
                    'status': 'accepted',
                    'created_at': offer.created_at,
                })

        return Response(trading_items)

    @action(detail=False, methods=['post'], url_path='offers/(?P<offer_id>[^/.]+)/cancel', permission_classes=[IsAuthenticated])
    def cancel_offer(self, request, offer_id=None):
        """제안 취소 (구매자)"""
        try:
            offer = ElectronicsOffer.objects.get(
                id=offer_id,
                buyer=request.user,
                status='pending'
            )
        except ElectronicsOffer.DoesNotExist:
            return Response(
                {'error': '제안을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        offer.status = 'cancelled'
        offer.save(update_fields=['status'])

        # 유니크한 구매자 수로 offer_count 업데이트
        electronics = offer.electronics
        unique_buyers_count = ElectronicsOffer.objects.filter(
            electronics=electronics,
            status='pending'
        ).values('buyer').distinct().count()

        electronics.offer_count = unique_buyers_count
        electronics.save(update_fields=['offer_count'])

        return Response({
            "message": "제안이 취소되었습니다.",
            "status": offer.status
        })