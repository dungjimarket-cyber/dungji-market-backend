# api/utils/__init__.py

from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def update_groupbuy_status(groupbuy):
    """
    단일 공구의 상태를 업데이트합니다.
    
    현재 시간과 공구의 각종 마감 시간을 비교하여 상태를 자동으로 업데이트합니다.
    
    Args:
        groupbuy: 업데이트할 GroupBuy 객체
        
    Returns:
        bool: 상태가 변경되었는지 여부
    """
    now = timezone.now()
    original_status = groupbuy.status
    
    # 입찰 중 -> 입찰 확정 대기 (투표 단계)
    if groupbuy.status == 'bidding' and now > groupbuy.end_time:
        groupbuy.status = 'voting'
        groupbuy.voting_end = now + timedelta(hours=12)
        groupbuy.save()
        logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
        groupbuy.notify_status_change()
        return True
    
    # 투표 단계 -> 판매자 확정 대기 또는 취소
    elif groupbuy.status == 'voting' and now > groupbuy.voting_end:
        # 확정된 입찰이 있는지 확인 (투표 결과)
        confirmed_votes = groupbuy.vote_set.filter(choice='confirm').count()
        if confirmed_votes >= 1:
            # 낙찰자 선정 로직은 GroupBuy.handle_voting_timeout에서 처리됨
            groupbuy.status = 'seller_confirmation'
            # 판매자 확정 기한은 투표 종료 후 24시간
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
            groupbuy.notify_status_change()
            return True
        else:
            # 확정된 입찰이 없으면 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status} (확정된 투표 없음)")
            groupbuy.notify_status_change()
            return True
    
    # 판매자 확정 대기 -> 완료
    elif groupbuy.status == 'seller_confirmation' and now > (groupbuy.voting_end + timedelta(hours=24)):
        groupbuy.status = 'completed'
        groupbuy.save()
        logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
        groupbuy.notify_status_change()
        return True
    
    return False

def update_groupbuys_status():
    """
    모든 진행 중인 공구의 상태를 업데이트합니다.
    
    Returns:
        int: 상태가 변경된 공구의 수
    """
    from ..models import GroupBuy  # 순환 참조 방지를 위해 함수 내에서 import
    
    # 진행 중인 모든 공구 조회
    active_statuses = ['bidding', 'voting', 'seller_confirmation']
    active_groupbuys = GroupBuy.objects.filter(status__in=active_statuses)
    
    updated_count = 0
    for groupbuy in active_groupbuys:
        if update_groupbuy_status(groupbuy):
            updated_count += 1
    
    logger.info(f"총 {active_groupbuys.count()}개 공구 중 {updated_count}개 상태 업데이트 완료")
    return updated_count
