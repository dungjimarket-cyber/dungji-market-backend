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
        """쿼리셋 반환"""
        queryset = UsedElectronics.objects.filter(status='active')

        # 관련 데이터 미리 로드 (N+1 쿼리 방지)
        queryset = queryset.select_related('seller', 'region')
        queryset = queryset.prefetch_related('images', 'regions__region', 'favorites')

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

        region = self.request.query_params.get('region', None)
        if region:
            queryset = queryset.filter(regions__region__id=region).distinct()

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
        queryset = self.get_queryset()
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
        offered_price = request.data.get('offer_price')
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

            # ElectronicsTransaction 생성
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
            'offer_price': my_offer.offer_price,
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
                'offer_price': offer.offer_price,
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_transaction(self, request, pk=None):
        """거래 완료 (판매자)"""
        electronics = self.get_object()

        # 판매자 또는 구매자 확인
        try:
            transaction = ElectronicsTransaction.objects.get(electronics=electronics)
        except ElectronicsTransaction.DoesNotExist:
            return Response(
                {'error': '거래 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user not in [transaction.seller, transaction.buyer]:
            return Response(
                {'error': '거래 당사자만 완료할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 거래 완료
        transaction.status = 'completed'
        transaction.save()

        electronics.status = 'sold'
        electronics.save()

        return Response({'message': '거래가 완료되었습니다.'})

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
        """제안 응답 (수락/거절)"""
        action_type = request.data.get('action')  # 'accept' or 'reject'
        message = request.data.get('message')

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

        if action_type == 'accept':
            offer.status = 'accepted'
            # 다른 제안들 거절
            ElectronicsOffer.objects.filter(
                electronics=offer.electronics
            ).exclude(id=offer_id).update(status='rejected')
        elif action_type == 'reject':
            offer.status = 'rejected'
        else:
            return Response(
                {'error': '잘못된 액션입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        offer.save()
        return Response({'message': f'제안이 {action_type}되었습니다.'})

    @action(detail=False, methods=['post'], url_path='offers/(?P<offer_id>[^/.]+)/proceed-trade', permission_classes=[IsAuthenticated])
    def proceed_trade(self, request, offer_id=None):
        """거래 진행 (수락된 제안을 거래중으로 전환)"""
        try:
            offer = ElectronicsOffer.objects.get(
                id=offer_id,
                electronics__seller=request.user,
                status='accepted'
            )
        except ElectronicsOffer.DoesNotExist:
            return Response(
                {'error': '수락된 제안을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 상품 상태를 거래중으로 변경
        electronics = offer.electronics
        electronics.status = 'trading'
        electronics.save()

        # 거래 생성
        ElectronicsTransaction.objects.create(
            electronics=electronics,
            seller=electronics.seller,
            buyer=offer.buyer,
            final_price=offer.offer_price,
            status='in_progress'
        )

        return Response({'message': '거래가 시작되었습니다.'})

    @action(detail=True, methods=['get'], url_path='buyer-info', permission_classes=[IsAuthenticated])
    def buyer_info(self, request, pk=None):
        """구매자 정보 조회 (거래중인 판매자용)"""
        electronics = self.get_object()

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

        buyer_data = {
            'id': transaction.buyer.id,
            'nickname': getattr(transaction.buyer, 'nickname', transaction.buyer.username),
            'phone': getattr(transaction.buyer, 'phone', None),
            'email': transaction.buyer.email,
            'region': getattr(transaction.buyer, 'region_name', None),
            'accepted_price': transaction.final_price
        }

        return Response(buyer_data)

    @action(detail=True, methods=['get'], url_path='seller-info', permission_classes=[IsAuthenticated])
    def seller_info(self, request, pk=None):
        """판매자 정보 조회 (거래중인 구매자용)"""
        electronics = self.get_object()

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
        seller_data = {
            'id': seller.id,
            'nickname': getattr(seller, 'nickname', seller.username),
            'phone': getattr(seller, 'phone', None),
            'email': seller.email,
            'region': getattr(seller, 'region_name', None),
            'accepted_price': transaction.final_price
        }

        return Response(seller_data)

    @action(detail=True, methods=['get'], url_path='transaction-info', permission_classes=[IsAuthenticated])
    def transaction_info(self, request, pk=None):
        """거래 정보 조회 (후기 작성용)"""
        electronics = self.get_object()

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

    @action(detail=True, methods=['post'], url_path='buyer-complete', permission_classes=[IsAuthenticated])
    def buyer_complete(self, request, pk=None):
        """구매 완료 (구매자용)"""
        electronics = self.get_object()

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

        # 구매자 완료 처리
        transaction.buyer_completed = True

        # 양쪽 모두 완료한 경우 거래 완료
        if transaction.seller_completed:
            transaction.status = 'completed'
            electronics.status = 'sold'
            electronics.save()

        transaction.save()

        return Response({'message': '구매 확정되었습니다.'})

    @action(detail=True, methods=['post'], url_path='cancel-trade', permission_classes=[IsAuthenticated])
    def cancel_trade(self, request, pk=None):
        """거래 취소"""
        electronics = self.get_object()
        reason = request.data.get('reason')
        custom_reason = request.data.get('custom_reason')

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

        # 거래 취소
        transaction.status = 'cancelled'
        transaction.cancelled_by = request.user
        transaction.cancellation_reason = reason
        transaction.cancellation_detail = custom_reason
        transaction.save()

        # 상품 상태를 다시 활성으로 변경
        electronics.status = 'active'
        electronics.save()

        # 제안 상태도 초기화
        ElectronicsOffer.objects.filter(
            electronics=electronics,
            status='accepted'
        ).update(status='cancelled')

        return Response({'message': '거래가 취소되었습니다.'})

    @action(detail=False, methods=['get'], url_path='my-offers', permission_classes=[IsAuthenticated])
    def my_sent_offers(self, request):
        """내가 보낸 제안 목록 조회 (구매자)"""
        status_filter = request.query_params.get('status')

        offers = ElectronicsOffer.objects.filter(buyer=request.user)

        if status_filter:
            offers = offers.filter(status=status_filter)

        offers = offers.select_related('electronics', 'electronics__seller')
        offers = offers.order_by('-created_at')

        page = self.paginate_queryset(offers)
        if page is not None:
            serializer = ElectronicsOfferSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ElectronicsOfferSerializer(offers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-trading', permission_classes=[IsAuthenticated])
    def my_trading_items(self, request):
        """내 거래중 목록 조회 (구매자)"""
        transactions = ElectronicsTransaction.objects.filter(
            buyer=request.user,
            status__in=['in_progress', 'completed']
        ).select_related('electronics', 'seller')

        page = self.paginate_queryset(transactions)
        if page is not None:
            # Transaction 데이터를 적절한 형식으로 변환
            data = []
            for transaction in page:
                offer_data = {
                    'id': transaction.id,
                    'electronics': ElectronicsDetailSerializer(transaction.electronics).data,
                    'offered_price': transaction.final_price,
                    'status': 'accepted' if transaction.status == 'in_progress' else 'completed',
                    'created_at': transaction.created_at,
                    'has_review': False  # TODO: 리뷰 모델 추가 후 수정
                }
                data.append(offer_data)
            return self.get_paginated_response(data)

        return Response([])

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