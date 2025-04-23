from django.utils import timezone
from datetime import timedelta

def update_groupbuy_status(groupbuy):
    """
    공구 상태를 현재 시간과 참여자 수에 따라 자동으로 업데이트합니다.
    이 함수는 공구 조회, 목록 조회 등의 API 호출 시점에 호출됩니다.
    """
    now = timezone.now()
    
    # 이미 완료된 상태라면 변경하지 않음
    if groupbuy.status in ['completed', 'cancelled']:
        return False
    
    # 모집 중이고 마감 시간이 지난 경우
    if groupbuy.status == 'recruiting' and now > groupbuy.end_time:
        # 최소 참여자 수를 충족한 경우 '확정' 상태로 변경
        if groupbuy.current_participants >= groupbuy.min_participants:
            groupbuy.status = 'completed'
            groupbuy.save(update_fields=['status'])
            return True
        # 최소 참여자 수를 충족하지 못한 경우 '취소' 상태로 변경
        else:
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
            return True
            
    # 투표 중이고 투표 종료 시간이 지난 경우
    if groupbuy.status == 'voting' and groupbuy.voting_end and now > groupbuy.voting_end:
        groupbuy.handle_voting_timeout()
        return True
        
    # 판매자 확정 대기 중이고 24시간이 지난 경우
    if groupbuy.status == 'seller_confirmation' and groupbuy.voting_end:
        if now > groupbuy.voting_end + timedelta(hours=24):
            groupbuy.status = 'completed'
            groupbuy.save(update_fields=['status'])
            return True
            
    return False

def update_groupbuys_status(groupbuys):
    """
    여러 공구의 상태를 일괄적으로 업데이트합니다.
    """
    updated_count = 0
    for groupbuy in groupbuys:
        if update_groupbuy_status(groupbuy):
            updated_count += 1
    
    return updated_count
