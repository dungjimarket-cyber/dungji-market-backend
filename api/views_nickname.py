"""
닉네임 변경 관련 API 뷰
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models_nickname import NicknameChangeHistory
from django.utils import timezone

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nickname_change_status(request):
    """
    사용자의 닉네임 변경 가능 상태를 확인하는 API
    
    Returns:
        - can_change: 변경 가능 여부
        - remaining_changes: 남은 변경 가능 횟수
        - next_available_date: 다음 변경 가능 날짜 (변경 불가능한 경우)
        - recent_changes: 최근 30일 이내 변경 이력
    """
    try:
        user = request.user
        
        # 변경 가능 여부 확인
        can_change = NicknameChangeHistory.can_change_nickname(user)
        remaining_changes = NicknameChangeHistory.get_remaining_changes(user)
        next_available = NicknameChangeHistory.get_next_available_date(user) if not can_change else None
        
        # 최근 30일 이내 변경 이력
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_changes = NicknameChangeHistory.objects.filter(
            user=user,
            changed_at__gte=thirty_days_ago
        ).values('old_nickname', 'new_nickname', 'changed_at').order_by('-changed_at')
        
        return Response({
            'can_change': can_change,
            'remaining_changes': remaining_changes,
            'next_available_date': next_available.isoformat() if next_available else None,
            'recent_changes': list(recent_changes),
            'message': f'30일 이내 {remaining_changes}회 변경 가능합니다.' if can_change else '30일 이내 변경 제한에 도달했습니다.'
        })
        
    except Exception as e:
        logger.error(f"닉네임 변경 상태 확인 오류: {str(e)}")
        return Response(
            {'error': '닉네임 변경 상태 확인 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nickname_change_history(request):
    """
    사용자의 전체 닉네임 변경 이력을 조회하는 API
    """
    try:
        user = request.user
        
        # 전체 변경 이력 조회
        history = NicknameChangeHistory.objects.filter(
            user=user
        ).values(
            'old_nickname', 
            'new_nickname', 
            'changed_at'
        ).order_by('-changed_at')
        
        return Response({
            'history': list(history),
            'total_changes': history.count()
        })
        
    except Exception as e:
        logger.error(f"닉네임 변경 이력 조회 오류: {str(e)}")
        return Response(
            {'error': '닉네임 변경 이력 조회 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )