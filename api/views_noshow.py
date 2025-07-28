"""
노쇼 신고 관련 API 뷰
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .models import NoShowReport, GroupBuy, User
from .serializers import NoShowReportSerializer
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class NoShowReportViewSet(ModelViewSet):
    """
    노쇼 신고 관리 ViewSet
    """
    serializer_class = NoShowReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        현재 사용자가 신고한 내역 또는 받은 신고 내역 조회
        """
        user = self.request.user
        queryset = NoShowReport.objects.select_related(
            'reporter', 'reported_user', 'groupbuy', 'bid', 'participation'
        )
        
        # 쿼리 파라미터로 필터링
        report_type = self.request.query_params.get('type')
        if report_type == 'made':
            # 내가 신고한 내역
            queryset = queryset.filter(reporter=user)
        elif report_type == 'received':
            # 내가 받은 신고 내역
            queryset = queryset.filter(reported_user=user)
        else:
            # 기본: 내가 관련된 모든 신고 내역
            queryset = queryset.filter(Q(reporter=user) | Q(reported_user=user))
        
        # 공구별 필터링
        groupbuy_id = self.request.query_params.get('groupbuy_id')
        if groupbuy_id:
            queryset = queryset.filter(groupbuy_id=groupbuy_id)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """
        신고 생성 시 신고자 자동 설정
        """
        serializer.save(reporter=self.request.user)
        
        # 노쇼 신고 알림 발송
        instance = serializer.instance
        logger.info(f"노쇼 신고 생성: {instance.reporter} -> {instance.reported_user} ({instance.groupbuy.title})")
        
        # TODO: 알림 서비스 연동
        # notification_service.send_noshow_report_notification(instance)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_noshow_report_eligibility(request):
    """
    노쇼 신고 가능 여부 확인
    
    Query Parameters:
    - groupbuy_id: 공구 ID
    - user_id: 신고 대상 사용자 ID
    - report_type: 신고 유형 (buyer_noshow, seller_noshow)
    """
    groupbuy_id = request.query_params.get('groupbuy_id')
    user_id = request.query_params.get('user_id')
    report_type = request.query_params.get('report_type')
    
    if not all([groupbuy_id, user_id, report_type]):
        return Response({
            'error': '필수 파라미터가 누락되었습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        groupbuy = GroupBuy.objects.get(id=groupbuy_id)
        reported_user = User.objects.get(id=user_id)
    except (GroupBuy.DoesNotExist, User.DoesNotExist):
        return Response({
            'error': '잘못된 공구 또는 사용자 ID입니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # 이미 신고했는지 확인
    existing_report = NoShowReport.objects.filter(
        reporter=user,
        reported_user=reported_user,
        groupbuy=groupbuy
    ).exists()
    
    if existing_report:
        return Response({
            'eligible': False,
            'reason': '이미 해당 사용자를 신고했습니다.'
        })
    
    # 신고 유형별 자격 확인
    if report_type == 'buyer_noshow':
        # 판매자가 구매자를 신고
        if user.role != 'seller':
            return Response({
                'eligible': False,
                'reason': '구매자 노쇼는 판매자만 신고할 수 있습니다.'
            })
        
        # 해당 공구에서 선택된 입찰이 있는지 확인
        from .models_bid import Bid
        selected_bid = Bid.objects.filter(
            groupbuy=groupbuy,
            seller=user,
            status='selected'
        ).exists()
        
        if not selected_bid:
            return Response({
                'eligible': False,
                'reason': '해당 공구에서 선택된 입찰이 없습니다.'
            })
        
        # 신고 대상이 참여자인지 확인
        from .models import Participation
        is_participant = Participation.objects.filter(
            user=reported_user,
            groupbuy=groupbuy
        ).exists()
        
        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 해당 공구 참여자가 아닙니다.'
            })
        
    elif report_type == 'seller_noshow':
        # 구매자가 판매자를 신고
        if user.role != 'buyer':
            return Response({
                'eligible': False,
                'reason': '판매자 노쇼는 구매자만 신고할 수 있습니다.'
            })
        
        # 신고자가 참여자인지 확인
        from .models import Participation
        is_participant = Participation.objects.filter(
            user=user,
            groupbuy=groupbuy
        ).exists()
        
        if not is_participant:
            return Response({
                'eligible': False,
                'reason': '해당 공구에 참여하지 않았습니다.'
            })
        
        # 신고 대상이 선택된 판매자인지 확인
        from .models_bid import Bid
        is_selected_seller = Bid.objects.filter(
            groupbuy=groupbuy,
            seller=reported_user,
            status='selected'
        ).exists()
        
        if not is_selected_seller:
            return Response({
                'eligible': False,
                'reason': '신고 대상이 선택된 판매자가 아닙니다.'
            })
    
    else:
        return Response({
            'eligible': False,
            'reason': '잘못된 신고 유형입니다.'
        })
    
    return Response({
        'eligible': True,
        'message': '노쇼 신고가 가능합니다.'
    })