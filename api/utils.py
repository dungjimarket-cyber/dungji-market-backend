from django.utils import timezone
from datetime import timedelta

def update_groupbuy_status(groupbuy):
    """
    공구 상태를 현재 시간과 참여자 수에 따라 자동으로 업데이트합니다.
    이 함수는 공구 조회, 목록 조회 등의 API 호출 시점에 호출됩니다.
    
    상태 전환 플로우:
    1. recruiting (모집중) -> bidding (입찰진행중): 시작 시간 도달 시
    2. bidding (입찰진행중) -> voting (최종선택중): 종료 시간 도달 시 (12시간 타이머 시작)
    3. voting (최종선택중) -> seller_confirmation/cancelled: 12시간 후
    4. seller_confirmation -> completed: 추가 24시간 후
    """
    now = timezone.now()
    
    # 이미 완료된 상태라면 변경하지 않음
    if groupbuy.status in ['completed', 'cancelled']:
        return False
    
    # 모집 중이고 시작 시간이 지난 경우 -> 입찰 진행중으로 변경
    if groupbuy.status == 'recruiting' and now >= groupbuy.start_time:
        groupbuy.status = 'bidding'
        groupbuy.save(update_fields=['status'])
        return True
    
    # 입찰 진행중이고 종료 시간이 지난 경우 -> 최종선택중으로 변경 (12시간 타이머 시작)
    if groupbuy.status == 'bidding' and now > groupbuy.end_time:
        # 최소 참여자 수를 충족하지 못한 경우 취소
        if groupbuy.current_participants < groupbuy.min_participants:
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
            return True
        
        # 최종선택 상태로 변경하고 12시간 타이머 설정
        groupbuy.status = 'voting'
        groupbuy.voting_end = now + timedelta(hours=12)
        groupbuy.save(update_fields=['status', 'voting_end'])
        
        # 참여자들에게 알림 보내기
        try:
            from .models import Notification
            for participant in groupbuy.participants.all():
                Notification.objects.create(
                    user=participant,
                    groupbuy=groupbuy,
                    notification_type='voting_start',
                    message=f"{groupbuy.title} 공구의 최종 선택 시간이 시작되었습니다. 12시간 내에 판매자를 선택해주세요."
                )
        except Exception as e:
            print(f"알림 생성 중 오류: {e}")
        
        return True
            
    # 투표 중이고 투표 종료 시간(12시간)이 지난 경우
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
