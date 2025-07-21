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
        """
        user = self.request.user
        now = timezone.now()
        
        # 업데이트인 경우 입찰권을 소비하지 않음
        if is_update:
            serializer.save(seller=user)
            return
        
        # 무제한 입찰권 확인
        unlimited_token = BidToken.objects.filter(
            seller=user,
            token_type='unlimited',
            status='active',
            expires_at__gt=now
        ).first()
        
        if unlimited_token:
            # 무제한 입찰권이 있으면 입찰권을 소비하지 않고 무제한 입찰권 정보만 추가
            bid = serializer.save(seller=user)
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
        bid = serializer.save(seller=user, bid_token=single_token)
        single_token.use(bid)

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
        
    bids = Bid.objects.filter(groupbuy=groupbuy).order_by('-created_at')
    
    # 판매자인 경우 모든 입찰 정보 표시
    if request.user == groupbuy.creator:
        serializer = BidSerializer(bids, many=True)
    # 판매자인 경우 자신의 입찰은 전체 정보, 다른 판매자의 입찰은 일부 정보만 표시
    else:
        serializer = BidSerializer(bids, many=True)
        for item in serializer.data:
            # 다른 판매자의 입찰인 경우 금액 정보 마스킹
            if item['seller'] != request.user.id:
                if item['bid_type'] == 'price':
                    item['amount'] = "**********"  # 금액 마스킹
                item['message'] = ""  # 메시지 정보 숨김
    
    return Response(serializer.data)
