from django.utils import timezone
from datetime import timedelta

def update_groupbuy_status(groupbuy):
    """
    공구 상태를 현재 시간과 참여자 수에 따라 자동으로 업데이트합니다.
    이 함수는 공구 조회, 목록 조회 등의 API 호출 시점에 호출됩니다.
    
    상태 전환 플로우:
    1. recruiting (모집중) -> bidding (입찰진행중): 시작 시간 도달 시
    2. bidding (입찰진행중) -> final_selection_buyers (구매자 최종선택중): 종료 시간 도달 시 (12시간 타이머)
    3. final_selection_buyers -> final_selection_seller (판매자 최종선택중): 구매자 전원 선택 완료 시 (6시간 타이머)
    4. final_selection_seller -> completed/cancelled: 판매자 선택 완료 또는 시간 초과 시
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
        
        # 입찰이 있는지 확인하고 최고 입찰자 선정
        from .models import Bid
        bids = groupbuy.bid_set.filter(status='pending').order_by('-amount', 'created_at')
        
        if bids.exists():
            # 가장 높은 지원금을 제시한 입찰자를 낙찰자로 선정
            winning_bid = bids.first()
            winning_bid.status = 'selected'
            winning_bid.is_selected = True  # is_selected 플래그도 설정
            winning_bid.save(update_fields=['status', 'is_selected'])
            
            # 다른 입찰자들의 상태를 'not_selected'로 변경  
            bids.exclude(id=winning_bid.id).update(status='not_selected', is_selected=False)
            # 구매자 최종선택 상태로 변경하고 12시간 타이머 설정
            groupbuy.status = 'final_selection_buyers'
            groupbuy.final_selection_end = now + timedelta(hours=12)
            groupbuy.save(update_fields=['status', 'final_selection_end'])
            
            # 구매자들에게만 알림 보내기
            try:
                from .models import Notification
                for participant in groupbuy.participants.all():
                    Notification.objects.create(
                        user=participant,
                        groupbuy=groupbuy,
                        notification_type='buyer_selection_start',
                        message=f"{groupbuy.title} 공구의 구매자 최종 선택이 시작되었습니다. 12시간 내에 구매 확정/포기를 선택해주세요."
                    )
                
                # 낙찰자에게 알림
                Notification.objects.create(
                    user=winning_bid.seller,
                    groupbuy=groupbuy,
                    notification_type='bid_winner',
                    message=f"축하합니다! {groupbuy.title} 공구에 낙찰되셨습니다. 구매자들의 최종 선택 후 판매 확정을 진행해주세요."
                )
                
                # 낙찰되지 않은 입찰자들에게 알림
                for bid in bids.exclude(id=winning_bid.id):
                    Notification.objects.create(
                        user=bid.seller,
                        groupbuy=groupbuy,
                        notification_type='bid_not_selected',
                        message=f"{groupbuy.title} 공구에 낙찰되지 않으셨습니다. (낙찰 지원금: {winning_bid.amount:,}원)"
                    )
            except Exception as e:
                print(f"알림 생성 중 오류: {e}")
        else:
            # 입찰이 없으면 취소
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
        
        return True
    
    # 구매자 최종선택 중이고 12시간이 지난 경우
    if groupbuy.status == 'final_selection_buyers' and groupbuy.final_selection_end and now > groupbuy.final_selection_end:
        # 시간 내 선택하지 않은 참여자들을 포기로 처리
        from .models import Participation
        unconfirmed_participations = groupbuy.participation_set.filter(final_decision='pending')
        unconfirmed_participations.update(final_decision='cancelled')
        
        # 구매 확정한 참여자가 있는지 확인
        confirmed_count = groupbuy.participation_set.filter(final_decision='confirmed').count()
        total_count = groupbuy.participation_set.count()
        
        if confirmed_count > 0:
            # 판매자 최종선택 단계로 전환
            groupbuy.status = 'final_selection_seller'
            groupbuy.seller_selection_end = now + timedelta(hours=6)
            groupbuy.save(update_fields=['status', 'seller_selection_end'])
            
            # 판매자에게 알림 보내기
            try:
                from .models import Bid, Notification
                winning_bid = groupbuy.bid_set.filter(status='selected').first()
                if winning_bid:
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        notification_type='seller_selection_start',
                        message=f"{groupbuy.title} 공구의 판매자 최종 선택이 시작되었습니다. 6시간 내에 판매 확정/포기를 선택해주세요. (구매확정: {confirmed_count}/{total_count}명)"
                    )
            except Exception as e:
                print(f"판매자 알림 생성 중 오류: {e}")
        else:
            # 구매 확정한 참여자가 없으면 취소
            groupbuy.status = 'cancelled'
            groupbuy.save(update_fields=['status'])
        
        return True
    
    # 판매자 최종선택 중이고 6시간이 지난 경우
    if groupbuy.status == 'final_selection_seller' and groupbuy.seller_selection_end and now > groupbuy.seller_selection_end:
        from .models import Bid, Participation
        
        # 낙찰된 입찰 확인
        winning_bid = groupbuy.bid_set.filter(status='selected').first()
        
        # 판매자가 시간 내 선택하지 않은 경우
        if winning_bid and winning_bid.final_decision == 'pending':
            winning_bid.final_decision = 'cancelled'
            winning_bid.save()
            
            # 구매 확정률 계산
            confirmed_count = groupbuy.participation_set.filter(final_decision='confirmed').count()
            total_count = groupbuy.participation_set.count()
            confirmation_rate = confirmed_count / total_count if total_count > 0 else 0
            
            # 50% 이하인 경우 패널티 면제
            if confirmation_rate > 0.5:
                # 판매자에게 패널티 부과
                try:
                    seller_profile = winning_bid.seller.userprofile
                    seller_profile.penalty_points += 10  # 패널티 점수 부과
                    seller_profile.save()
                except:
                    pass
            else:
                # 패널티 면제 및 입찰권 환불 (단품 입찰권만)
                if winning_bid.bid_token and winning_bid.bid_token.token_type == 'single':
                    try:
                        # 입찰권 상태를 다시 활성으로 변경
                        winning_bid.bid_token.status = 'active'
                        winning_bid.bid_token.used_at = None
                        winning_bid.bid_token.used_for = None
                        winning_bid.bid_token.save()
                        
                        # 입찰과 입찰권 연결 해제
                        winning_bid.bid_token = None
                        winning_bid.save()
                    except:
                        pass
        
        # 최종 상태 결정
        seller_confirmed = winning_bid and winning_bid.final_decision == 'confirmed'
        confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
        
        if confirmed_participants and seller_confirmed:
            groupbuy.status = 'completed'
        else:
            groupbuy.status = 'cancelled'
            
            # 구매자 패널티 처리 (구매 확정 후 판매자가 포기한 경우에는 면제)
            if seller_confirmed or winning_bid.final_decision == 'pending':
                # 판매자가 확정했거나 미선택인 경우에만 구매자 패널티
                cancelled_participations = groupbuy.participation_set.filter(final_decision='cancelled')
                for participation in cancelled_participations:
                    try:
                        user_profile = participation.user.userprofile
                        user_profile.penalty_points += 5  # 구매자 패널티
                        user_profile.save()
                    except:
                        pass
        
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
