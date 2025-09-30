"""
끌올 기능 API Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from .models_unified_simple import UnifiedBump
from used_phones.models import UsedPhone
from used_electronics.models import UsedElectronics
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bump_status(request, item_type, item_id):
    """
    끌올 가능 상태 조회
    GET /api/bump/{item_type}/{item_id}/status/
    Version: 2025-01-30-v2
    """
    try:
        # 상품 존재 여부 확인
        if item_type == 'phone':
            item = UsedPhone.objects.filter(id=item_id).first()
        elif item_type == 'electronics':
            item = UsedElectronics.objects.filter(id=item_id).first()
        else:
            return Response({'error': '잘못된 상품 타입입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if not item:
            return Response({'error': '상품을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 본인 상품인지 확인
        if item.seller.id != request.user.id:
            return Response({'error': '본인의 상품만 끌올할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 활성 상태 확인
        if item.status != 'active':
            return Response({
                'can_bump': False,
                'reason': '판매중 상품만 끌올 가능합니다.',
                'status': item.status
            }, status=status.HTTP_200_OK)

        # 오늘 사용한 무료 끌올 횟수
        today = timezone.now().date()
        today_count = UnifiedBump.objects.filter(
            user=request.user,
            bumped_at__date=today,
            is_free=True
        ).count()

        # 마지막 끌올 시간 체크 (1시간 쿨다운)
        last_bump = UnifiedBump.objects.filter(
            item_type=item_type,
            item_id=item_id
        ).order_by('-bumped_at').first()

        can_bump = True
        reason = None
        next_available_at = None

        # 하루 3회 제한 체크
        if today_count >= 3:
            can_bump = False
            reason = '오늘의 무료 끌올을 모두 사용했습니다.'
            # 내일 자정
            tomorrow = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            next_available_at = tomorrow.isoformat()

        # 쿨다운 체크 (1시간)
        elif last_bump:
            time_passed = timezone.now() - last_bump.bumped_at
            if time_passed < timedelta(hours=1):
                can_bump = False
                remaining = timedelta(hours=1) - time_passed
                minutes = int(remaining.total_seconds() / 60)
                reason = f'{minutes}분 후에 끌올 가능합니다.'
                next_available_at = (last_bump.bumped_at + timedelta(hours=1)).isoformat()

        return Response({
            'can_bump': can_bump,
            'bump_type': 'free',
            'remaining_free_bumps_today': 3 - today_count,
            'next_bump_available_at': next_available_at,
            'total_bump_count': item.bump_count,
            'last_bumped_at': item.last_bumped_at.isoformat() if item.last_bumped_at else None,
            'reason': reason
        })

    except Exception as e:
        logger.error(f"Bump status error: {e}")
        error_detail = str(e)
        if 'UnifiedBump' in error_detail and 'does not exist' in error_detail:
            return Response({
                'can_bump': True,
                'bump_type': 'free',
                'remaining_free_bumps_today': 3,
                'next_bump_available_at': None,
                'total_bump_count': 0,
                'last_bumped_at': None,
                'reason': '마이그레이션 대기중'
            })
        return Response({'error': f'상태 조회 중 오류: {error_detail}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def perform_bump(request, item_type, item_id):
    """
    끌올 실행
    POST /api/bump/{item_type}/{item_id}/
    """
    try:
        # 상품 조회
        if item_type == 'phone':
            item = UsedPhone.objects.filter(id=item_id).first()
        elif item_type == 'electronics':
            item = UsedElectronics.objects.filter(id=item_id).first()
        else:
            return Response({'error': '잘못된 상품 타입입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if not item:
            return Response({'error': '상품을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # 본인 상품인지 확인
        if item.seller.id != request.user.id:
            return Response({'error': '본인의 상품만 끌올할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

        # 활성 상태 확인
        if item.status != 'active':
            return Response({'error': '판매중 상품만 끌올 가능합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 끌올 가능 여부 체크
        today = timezone.now().date()
        today_count = UnifiedBump.objects.filter(
            user=request.user,
            bumped_at__date=today,
            is_free=True
        ).count()

        if today_count >= 3:
            return Response({
                'error': '오늘의 무료 끌올을 모두 사용했습니다.',
                'remaining_free_bumps_today': 0
            }, status=status.HTTP_400_BAD_REQUEST)

        # 쿨다운 체크
        last_bump = UnifiedBump.objects.filter(
            item_type=item_type,
            item_id=item_id
        ).order_by('-bumped_at').first()

        if last_bump:
            time_passed = timezone.now() - last_bump.bumped_at
            if time_passed < timedelta(hours=1):
                remaining = timedelta(hours=1) - time_passed
                minutes = int(remaining.total_seconds() / 60)
                return Response({
                    'error': f'{minutes}분 후에 끌올 가능합니다.',
                    'next_available_at': (last_bump.bumped_at + timedelta(hours=1)).isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)

        # 끌올 실행
        bump = UnifiedBump.objects.create(
            user=request.user,
            item_type=item_type,
            item_id=item_id,
            is_free=True
        )

        # 상품 업데이트
        now = timezone.now()
        if item_type == 'phone':
            UsedPhone.objects.filter(id=item_id).update(
                last_bumped_at=now,
                bump_count=F('bump_count') + 1
            )
        else:
            UsedElectronics.objects.filter(id=item_id).update(
                last_bumped_at=now,
                bump_count=F('bump_count') + 1
            )

        # 업데이트된 상품 정보 다시 조회
        if item_type == 'phone':
            item = UsedPhone.objects.get(id=item_id)
        else:
            item = UsedElectronics.objects.get(id=item_id)

        return Response({
            'success': True,
            'message': '끌올이 완료되었습니다.',
            'bump_type': 'free',
            'remaining_free_bumps_today': 2 - today_count,
            'next_bump_available_at': (now + timedelta(hours=1)).isoformat(),
            'total_bump_count': item.bump_count,
            'bumped_at': now.isoformat()
        })

    except Exception as e:
        logger.error(f"Perform bump error: {e}")
        import traceback
        error_detail = str(e)
        if 'UnifiedBump' in error_detail and 'does not exist' in error_detail:
            return Response({'error': '끌올 기능이 아직 준비 중입니다. 마이그레이션이 필요합니다.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'error': f'끌올 처리 중 오류: {error_detail}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_today_bump_count(request):
    """
    오늘 사용한 끌올 횟수 조회
    GET /api/bump/today-count/
    """
    try:
        today = timezone.now().date()
        count = UnifiedBump.objects.filter(
            user=request.user,
            bumped_at__date=today,
            is_free=True
        ).count()

        return Response({
            'today_count': count,
            'remaining': 3 - count,
            'max_free_per_day': 3
        })

    except Exception as e:
        logger.error(f"Today bump count error: {e}")
        return Response({'error': '조회 중 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)