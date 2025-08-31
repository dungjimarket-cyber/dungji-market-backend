from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Bid, Settlement, GroupBuy, BidToken
from .serializers_bid import BidSerializer, SettlementSerializer
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError

class IsSellerPermission(permissions.BasePermission):
    """
    판매자(사업자회원) 권한 체크 클래스
    """
    message = "판매회원만 접근할 수 있습니다."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'seller'

class BidViewSet(viewsets.ModelViewSet):
    """
    입찰 관리 API 뷰셋
    """
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        현재 로그인한 사용자와 관련된 입찰만 반환
        """
        user = self.request.user
        
        # 판매자인 경우 자신의 입찰만 조회
        if user.role == 'seller':
            return Bid.objects.filter(seller=user).order_by('-created_at')
        
        # 일반 사용자는 공구 생성자인 경우에만 해당 공구의 모든 입찰 조회 가능
        created_groupbuys = GroupBuy.objects.filter(creator=user).values_list('id', flat=True)
        return Bid.objects.filter(groupbuy__in=created_groupbuys).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """
        입찰 생성 API - 중복 입찰 시 기존 입찰 업데이트 기능 추가
        """
        # 현재 공구에 대한 현재 사용자의 기존 입찰 확인
        try:
            groupbuy_id = request.data.get('groupbuy')
            existing_bid = Bid.objects.filter(
                seller=request.user,
                groupbuy_id=groupbuy_id,
                status='pending'  # 대기 상태인 입찰만 업데이트 가능
            ).first()
            
            if existing_bid:
                # 기존 입찰이 있는 경우 업데이트
                serializer = self.get_serializer(existing_bid, data=request.data, partial=True)
                is_update = True
            else:
                # 신규 입찰인 경우
                serializer = self.get_serializer(data=request.data)
                is_update = False
                
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer, is_update)
            
            headers = self.get_success_headers(serializer.data)
            response_data = serializer.data
            response_data['is_updated'] = is_update  # 업데이트 여부 전달
            
            return Response(
                response_data, 
                status=status.HTTP_200_OK if is_update else status.HTTP_201_CREATED,
                headers=headers
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def perform_create(self, serializer, is_update=False):
        """
        입찰 생성 또는 업데이트 시 현재 사용자를 판매자로 설정하고 입찰권 사용 처리
        견적 수정 시에도 견적티켓을 소모함 (기획 요구사항)
        """
        user = self.request.user
        now = timezone.now()
        
        # 견적 수정 시에도 견적티켓 소모 (기획 요구사항에 따라 변경)
        
        # 무제한 입찰권 확인
        unlimited_token = BidToken.objects.filter(
            seller=user,
            token_type='unlimited',
            status='active',
            expires_at__gt=now
        ).first()
        
        if unlimited_token:
            # 무제한 입찰권이 있으면 입찰권을 소비하지 않고 무제한 입찰권 정보만 추가
            bid = serializer.save(seller=user, bid_token=unlimited_token)
            # 무제한 입찰권은 소비하지 않지만 추적을 위해 used_for 필드는 설정
            unlimited_token.used_for = bid
            unlimited_token.save()
            return
        
        # 단품 입찰권 확인
        # 단품 입찰권은 유효기간이 없거나, 유효기간이 있는 경우 현재 시간보다 훨씬 만료일이 더 나중인 경우
        single_token = BidToken.objects.filter(
            seller=user,
            token_type='single',
            status='active',
        ).filter(
            # 유효기간이 없거나(None) 유효기간이 있는 경우 만료일이 현재보다 더 나중인 경우
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).first()
        
        # 입찰권이 없으면 오류 발생
        if not single_token:
            raise ValidationError("사용 가능한 입찰권이 없습니다. 입찰권을 구매하신 후 다시 시도해주세요.")
        
        # 입찰권 사용 처리 및 연결
        # 먼저 입찰을 저장하고, 그 다음에 입찰권을 사용 처리
        bid = serializer.save(seller=user, bid_token=single_token)
        
        # 입찰권 사용 처리 - 실패 시 입찰을 롤백해야 함
        if not single_token.use(bid):
            bid.delete()
            raise ValidationError("입찰권 사용 처리에 실패했습니다.")

    @action(detail=False, methods=['get'], url_path='seller')
    def seller_bids(self, request):
        """
        판매자의 모든 입찰 조회 API
        """
        if request.user.role != 'seller':
            return Response(
                {"detail": "판매회원만 접근할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        bids = Bid.objects.filter(seller=request.user).order_by('-created_at')
        serializer = self.get_serializer(bids, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='seller/confirmed')
    def seller_confirmed_bids(self, request):
        """
        판매자가 판매 확정한 입찰 목록 조회 API
        """
        if request.user.role != 'seller':
            return Response(
                {"detail": "판매회원만 접근할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 판매자가 판매 확정한 입찰만 조회 (정산이 완료되지 않은 것들)
        bids = Bid.objects.filter(
            seller=request.user,
            status='selected',
            final_decision='confirmed',
            groupbuy__status='completed'  # 공구가 완료된 상태
        ).exclude(
            settlement__payment_status='completed'  # 정산 완료된 것은 제외
        ).select_related('groupbuy', 'groupbuy__product', 'settlement').order_by('-updated_at')
        
        # 추가 정보 포함하여 반환
        result = []
        for bid in bids:
            groupbuy = bid.groupbuy
            # 모든 구매자가 확정했는지 확인
            all_buyers_confirmed = groupbuy.participation_set.filter(
                final_decision='pending'
            ).count() == 0
            
            result.append({
                'id': bid.id,
                'groupbuy': groupbuy.id,
                'groupbuy_product_name': groupbuy.product.name if groupbuy.product else groupbuy.product_name,
                'product_category': groupbuy.product.category.name if groupbuy.product and groupbuy.product.category else '',
                'amount': bid.amount,
                'participants_count': groupbuy.current_participants,
                'created_at': bid.created_at,
                'final_decision': bid.final_decision,
                'buyer_confirmed': all_buyers_confirmed,
                'all_buyers_confirmed': all_buyers_confirmed
            })
        
        return Response(result)
    
    @action(detail=False, methods=['post'], url_path='seller/complete-transaction')
    def complete_transaction(self, request):
        """
        판매자의 거래 완료 처리 API
        """
        if request.user.role != 'seller':
            return Response(
                {"detail": "판매회원만 접근할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        groupbuy_id = request.data.get('groupbuy_id')
        if not groupbuy_id:
            return Response(
                {"detail": "공구 ID가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 해당 공구의 판매자 입찰 찾기
            bid = Bid.objects.get(
                seller=request.user,
                groupbuy_id=groupbuy_id,
                status='selected',
                final_decision='confirmed'
            )
            
            # Settlement 생성 또는 업데이트
            settlement, created = Settlement.objects.get_or_create(
                seller=request.user,
                groupbuy_id=groupbuy_id,
                bid=bid,
                defaults={
                    'total_amount': bid.amount * bid.groupbuy.current_participants,
                    'fee_amount': 0,  # 수수료 계산 로직 필요시 추가
                    'net_amount': bid.amount * bid.groupbuy.current_participants,
                    'settlement_date': timezone.now()
                }
            )
            
            # 정산 상태를 완료로 변경
            settlement.payment_status = 'completed'
            settlement.save()
            
            return Response({
                "detail": "거래가 완료되었습니다.",
                "settlement_id": settlement.id
            }, status=status.HTTP_200_OK)
            
        except Bid.DoesNotExist:
            return Response(
                {"detail": "해당 공구의 입찰을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"거래 완료 처리 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='final-decision')
    def final_decision(self, request, pk=None):
        """
        판매자의 최종 판매 결정 (판매확정/판매포기)
        """
        try:
            # 입찰 정보 확인
            bid = self.get_object()
            
            # 본인의 입찰인지 확인
            if bid.seller != request.user:
                return Response(
                    {'error': '본인의 입찰만 결정할 수 있습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # 낙찰된 입찰인지 확인
            if bid.status != 'selected':
                return Response(
                    {'error': '낙찰된 입찰만 최종선택이 가능합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 공구 상태 확인
            if bid.groupbuy.status != 'final_selection':
                return Response(
                    {'error': '최종선택 기간이 아닙니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 이미 결정한 경우
            if bid.final_decision != 'pending':
                return Response(
                    {'error': '이미 최종선택을 완료했습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 결정 유형 검증
            decision = request.data.get('decision')
            if decision not in ['confirmed', 'cancelled']:
                return Response(
                    {'error': '올바르지 않은 선택입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 최종 결정 업데이트
            bid.final_decision = decision
            bid.save()
            
            # 판매 포기 시 패널티 부과
            if decision == 'cancelled':
                # 구매 확정한 참여자가 2명 이상인 경우에만 패널티 부과
                confirmed_count = bid.groupbuy.participation_set.filter(
                    final_decision='confirmed'
                ).count()
                
                if confirmed_count >= 2:
                    try:
                        from api.models import UserProfile
                        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                        user_profile.penalty_points += 10
                        user_profile.save()
                    except:
                        pass
            
            # 알림 생성
            from api.models import Notification
            if decision == 'confirmed':
                Notification.objects.create(
                    user=bid.seller,
                    groupbuy=bid.groupbuy,
                    notification_type='sale_confirmed',
                    message=f"{bid.groupbuy.title} 공구의 판매를 확정했습니다. 구매자 정보를 확인하세요."
                )
            else:
                Notification.objects.create(
                    user=bid.seller,
                    groupbuy=bid.groupbuy,
                    notification_type='sale_cancelled',
                    message=f"{bid.groupbuy.title} 공구의 판매를 포기했습니다."
                )
            
            # 모든 참여자와 판매자가 결정을 완료했는지 확인
            self._check_all_decisions_complete(bid.groupbuy)
            
            return Response({
                'message': '최종선택이 완료되었습니다.',
                'decision': decision
            })
            
        except Bid.DoesNotExist:
            return Response(
                {'error': '입찰 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _check_all_decisions_complete(self, groupbuy):
        """모든 참여자와 판매자의 결정이 완료되었는지 확인"""
        from api.models import Participation
        
        # 참여자들의 결정 확인
        pending_participants = groupbuy.participation_set.filter(final_decision='pending').exists()
        
        # 낙찰된 판매자의 결정 확인
        winning_bid = groupbuy.bid_set.filter(status='selected').first()
        seller_pending = winning_bid and winning_bid.final_decision == 'pending'
        
        # 모두 결정을 완료한 경우
        if not pending_participants and not seller_pending:
            # 구매 확정한 참여자가 있고 판매자도 확정한 경우
            confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
            seller_confirmed = winning_bid and winning_bid.final_decision == 'confirmed'
            
            if confirmed_participants and seller_confirmed:
                groupbuy.status = 'completed'
            else:
                groupbuy.status = 'cancelled'
            
            groupbuy.save()
    
    @action(detail=False, methods=['get'], url_path='seller/final-selection')
    def seller_final_selection(self, request):
        """
        판매자의 최종선택 대기중 입찰 조회 API
        """
        if request.user.role != 'seller':
            return Response(
                {"detail": "판매회원만 접근할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # final_selection_seller 상태이고 선택된 입찰만 조회
        bids = Bid.objects.filter(
            seller=request.user,
            groupbuy__status='final_selection_seller',
            status='selected'
        ).select_related('groupbuy', 'groupbuy__product').order_by('-created_at')
        
        # 직렬화할 때 final_selection_end 포함
        data = []
        for bid in bids:
            bid_data = self.get_serializer(bid).data
            # 판매자 최종선택 종료 시간 사용
            bid_data['final_selection_end'] = bid.groupbuy.seller_selection_end
            bid_data['groupbuy_status'] = bid.groupbuy.status
            bid_data['groupbuy_product_name'] = bid.groupbuy.product.name
            bid_data['participants_count'] = bid.groupbuy.participation_set.count()
            data.append(bid_data)
        
        return Response(data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_bid(self, request, pk=None):
        """
        입찰 확정 API
        """
        bid = self.get_object()
        
        # 자신의 입찰만 확정 가능
        if bid.seller != request.user:
            return Response(
                {"detail": "자신의 입찰만 확정할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 이미 확정 또는 포기된 입찰은 변경 불가
        if bid.status != 'pending':
            return Response(
                {"detail": "대기 중인 입찰만 확정할 수 있습니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        bid.status = 'selected'
        bid.save()
        
        # 해당 공구의 다른 입찰 자동 포기 처리
        Bid.objects.filter(
            Q(groupbuy=bid.groupbuy) & 
            ~Q(id=bid.id) & 
            Q(status='pending')
        ).update(status='rejected')
        
        serializer = self.get_serializer(bid)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_bid(self, request, pk=None):
        """
        입찰 포기 API
        """
        bid = self.get_object()
        
    @action(detail=True, methods=['delete'], url_path='cancel')
    def cancel_bid(self, request, pk=None):
        """
        입찰 취소 API - 입찰 시간 이전에만 취소 가능
        """
        bid = self.get_object()
        
        # 자신의 입찰만 취소 가능
        if bid.seller != request.user:
            return Response(
                {"detail": "자신의 입찰만 취소할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 입찰 상태가 대기중이거나 자격미달인 경우만 취소 가능
        if bid.status not in ['pending', 'ineligible']:
            return Response(
                {"detail": f"입찰 상태가 '{bid.status}'이므로 취소할 수 없습니다. 'pending' 또는 'ineligible' 상태의 입찰만 취소 가능합니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 입찰 시간 확인 - 공구가 아직 입찰 가능 상태인지 확인
        groupbuy = bid.groupbuy
        if groupbuy.status != 'bidding' and groupbuy.status != 'recruiting':
            return Response(
                {"detail": "입찰 시간이 종료된 공구의 입찰은 취소할 수 없습니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 사용한 입찰권이 있으면 상태 복구
        if bid.bid_token:
            token = bid.bid_token
            if token.status == 'used' and token.used_for == bid:
                token.status = 'active'
                token.used_at = None
                token.used_for = None
                token.save()
        
        # 입찰 취소 실행
        bid.delete()
        
        # 단독 입찰 취소 시 공구 상태 확인 및 업데이트
        remaining_bids = Bid.objects.filter(groupbuy=groupbuy, status='pending').count()
        if remaining_bids == 0 and groupbuy.status == 'bidding':
            # 입찰이 0개가 되면 공구 상태를 다시 모집중으로 변경
            groupbuy.status = 'recruiting'
            groupbuy.save()
            
            # 공구 생성자에게 알림 전송
            from api.utils.notification_service import NotificationService
            notification_service = NotificationService()
            notification_service.create_notification(
                user=groupbuy.creator,
                type='bid_cancelled',
                title='모든 입찰이 취소되었습니다',
                message=f'{groupbuy.title} 공구의 모든 견적이 취소되어 다시 모집중 상태로 변경되었습니다.',
                related_object=groupbuy
            )
        
        return Response({"detail": "입찰이 성공적으로 취소되었습니다."}, status=status.HTTP_204_NO_CONTENT)
        
        # 자신의 입찰만 포기 가능
        if bid.seller != request.user:
            return Response(
                {"detail": "자신의 입찰만 포기할 수 있습니다."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 이미 확정 또는 포기된 입찰은 변경 불가
        if bid.status != 'pending':
            return Response(
                {"detail": "대기 중인 입찰만 포기할 수 있습니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        bid.status = 'rejected'
        bid.save()
        
        serializer = self.get_serializer(bid)
        return Response(serializer.data)


class SettlementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    정산 내역 API 뷰셋 (읽기 전용)
    """
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated, IsSellerPermission]

    def get_queryset(self):
        """
        현재 로그인한 판매자와 관련된 정산 내역만 반환
        """
        return Settlement.objects.filter(
            seller=self.request.user
        ).order_by('-settlement_date')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def group_buy_bids(request, groupbuy_id):
    """
    특정 공구의 모든 입찰 조회 API
    """
    groupbuy = get_object_or_404(GroupBuy, id=groupbuy_id)
    
    # 공구 생성자 또는 판매자만 조회 가능
    if request.user != groupbuy.creator and request.user.role != 'seller':
        return Response(
            {"detail": "이 공구의 입찰 기록을 볼 권한이 없습니다."}, 
            status=status.HTTP_403_FORBIDDEN
        )
        
    bids = Bid.objects.filter(groupbuy=groupbuy).order_by('-amount', 'created_at')
    serializer = BidSerializer(bids, many=True)
    
    # 최종선택 전 단계에서만 마스킹 처리 (recruiting, bidding 상태)
    should_mask = groupbuy.status in ['recruiting', 'bidding']
    
    # 구매자(공구 생성자)인 경우
    if request.user == groupbuy.creator:
        if should_mask:
            # 최종선택 전에는 구매자도 입찰 금액을 마스킹된 상태로 봄
            for item in serializer.data:
                # 첫 자리만 보이고 나머지는 * 처리 (예: 600000 -> 6*****원)
                amount = item['amount']
                if amount:
                    amount_str = str(amount)
                    if len(amount_str) > 1:
                        item['amount'] = amount_str[0] + '*' * (len(amount_str) - 1) + '원'
                    else:
                        item['amount'] = amount_str + '원'
                else:
                    item['amount'] = "미입력"
                # 메시지는 유지
    # 판매자인 경우
    elif request.user.role == 'seller':
        for item in serializer.data:
            # 본인 입찰이 아닌 경우만 마스킹
            if item['seller'] != request.user.id:
                if should_mask:
                    # 최종선택 전에는 다른 판매자의 입찰 금액을 마스킹
                    amount = item['amount']
                    if amount:
                        amount_str = str(amount)
                        if len(amount_str) > 1:
                            item['amount'] = amount_str[0] + '*' * (len(amount_str) - 1) + '원'
                        else:
                            item['amount'] = amount_str + '원'
                    else:
                        item['amount'] = "미입력"
                    item['message'] = ""  # 메시지 정보 숨김
    
    return Response(serializer.data)
