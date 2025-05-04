from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Bid, Settlement, GroupBuy
from .serializers_bid import BidSerializer, SettlementSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q

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

    def perform_create(self, serializer):
        """
        입찰 생성 시 현재 사용자를 판매자로 설정
        """
        serializer.save(seller=self.request.user)

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
