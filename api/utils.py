from django.utils import timezone
from datetime import timedelta

def update_groupbuy_status(groupbuy):
    """
    공구 상태를 현재 시간과 참여자 수에 따라 자동으로 업데이트합니다.
    이 함수는 공구 조회, 목록 조회 등의 API 호출 시점에 호출됩니다.
    
    상태 전환 플로우:
    1. recruiting (모집중) -> bidding (입찰진행중): 시작 시간 도달 시
    2. bidding (입찰진행중) -> final_selection (최종선택중): 종료 시간 도달 시 (12시간 타이머 시작)
    3. final_selection (최종선택중) -> seller_confirmation/cancelled: 12시간 후
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
    
    # 입찰 진행중이고 종료 시간이 지난 경우
    if groupbuy.status == 'bidding' and now > groupbuy.end_time:
        # 최소 참여자 수를 충족하지 못한 경우 취소
        if groupbuy.current_participants < groupbuy.min_participants:
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
            return True
        
        # 낙찰된 입찰이 있는지 확인
        from .models import Bid
        winning_bid = groupbuy.bid_set.filter(status='selected').first()
        
        if winning_bid:
            # 최종선택 상태로 변경하고 12시간 타이머 설정
            groupbuy.status = 'final_selection'
            groupbuy.final_selection_end = now + timedelta(hours=12)
            groupbuy.save(update_fields=['status', 'final_selection_end'])
            
            # 참여자들에게 알림 보내기
            try:
                from .models import Notification
                # 구매자들에게 알림
                for participant in groupbuy.participants.all():
                    Notification.objects.create(
                        user=participant,
                        groupbuy=groupbuy,
                        notification_type='final_selection_start',
                        message=f"{groupbuy.title} 공구의 최종 선택이 시작되었습니다. 12시간 내에 구매 확정/포기를 선택해주세요."
                    )
                # 낙찰된 판매자에게 알림
                Notification.objects.create(
                    user=winning_bid.seller,
                    groupbuy=groupbuy,
                    notification_type='final_selection_start',
                    message=f"{groupbuy.title} 공구에 낙찰되었습니다. 12시간 내에 판매 확정/포기를 선택해주세요."
                )
            except Exception as e:
                print(f"알림 생성 중 오류: {e}")
        else:
            # 낙찰된 입찰이 없으면 취소
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
        
        return True
            
    # 최종선택 중이고 최종선택 종료 시간(12시간)이 지난 경우
    if groupbuy.status == 'final_selection' and groupbuy.final_selection_end and now > groupbuy.final_selection_end:
        # 최종선택 시간 초과 처리
        from .models import Bid, Participation
        
        # 시간 내 선택하지 않은 참여자들을 포기로 처리
        unconfirmed_participations = groupbuy.participation_set.filter(final_decision='pending')
        unconfirmed_participations.update(final_decision='cancelled')
        
        # 시간 내 선택하지 않은 판매자를 포기로 처리 (패널티 부과)
        winning_bid = groupbuy.bid_set.filter(status='selected').first()
        if winning_bid and winning_bid.final_decision == 'pending':
            winning_bid.final_decision = 'cancelled'
            winning_bid.save()
            
            # 판매자에게 패널티 부과
            try:
                seller_profile = winning_bid.seller.userprofile
                seller_profile.penalty_points += 10  # 패널티 점수 부과
                seller_profile.save()
            except:
                pass
        
        # 구매 확정한 참여자와 판매 확정한 판매자가 모두 있는 경우 completed
        confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
        seller_confirmed = winning_bid and winning_bid.final_decision == 'confirmed'
        
        if confirmed_participants and seller_confirmed:
            groupbuy.status = 'completed'
        else:
            groupbuy.status = 'cancelled'
            
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
