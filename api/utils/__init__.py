from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def update_groupbuy_status(groupbuy):
    """
    공구의 상태를 자동으로 업데이트합니다.
    
    상태 전환 규칙:
    1. recruiting (모집중): 시작 ~ 종료 시간 전
    2. bidding (입찰진행중): 첫 입찰 발생 시
    3. final_selection (최종선택중): 공구 마감 후 12시간 동안
    4. seller_confirmation (판매자확정대기): 최종선택 종료 후 ~ 24시간
    5. completed (완료): 모든 확정 완료
    6. cancelled (취소됨): 입찰 없거나 확정 실패
    
    Args:
        groupbuy: 업데이트할 GroupBuy 인스턴스
        
    Returns:
        bool: 상태가 변경되었으면 True, 아니면 False
    """
    if groupbuy.status in ['completed', 'cancelled']:
        return False
        
    now = timezone.now()
    original_status = groupbuy.status
    changed = False
    
    # v3.0: bidding 상태 제거 - recruiting에서 바로 final_selection_buyers로
    # 공구 마감 시간이 지났으면 final_selection_buyers로 변경
    if groupbuy.status == 'recruiting' and now > groupbuy.end_time:
        from api.models import Bid
        # 입찰이 있는 경우만 final_selection_buyers로, 없으면 cancelled
        if Bid.objects.filter(groupbuy=groupbuy).exists():
            groupbuy.status = 'final_selection_buyers'
            groupbuy.final_selection_end = groupbuy.end_time + timedelta(hours=12)
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: recruiting -> final_selection_buyers")
            groupbuy.notify_status_change()
            changed = True
        else:
            groupbuy.status = 'cancelled'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: recruiting -> cancelled (입찰 없음)")
            changed = True
    
    # 구매자 최종선택 단계 -> 판매자 최종선택 또는 취소
    elif groupbuy.status == 'final_selection_buyers' and groupbuy.final_selection_end and now > groupbuy.final_selection_end:
        # 최종선택 결과 확인 및 낙찰자 선정
        from ..models import Bid, Participation
        from django.db.models import Count
        
        # 확정한 참여자 수 집계
        confirmed_participants = Participation.objects.filter(
            groupbuy=groupbuy,
            final_decision='confirmed'
        ).count()
        
        if confirmed_participants > 0:
            # 최다 지원금을 제시한 입찰 선택
            bids = Bid.objects.filter(groupbuy=groupbuy).order_by('-amount', 'created_at')
            
            if bids:
                winning_bid = bids.first()
                winning_bid.is_selected = True
                winning_bid.save()
                logger.info(f"공구 '{groupbuy.title}' 낙찰자 선정: {winning_bid.seller.username} (지원금: {winning_bid.amount}원)")
                
                # 낙찰자에게 알림 발송
                from ..models import Notification
                Notification.objects.create(
                    user=winning_bid.seller,
                    groupbuy=groupbuy,
                    message=f"축하합니다! '{groupbuy.product.name}' 공구에 낙찰되셨습니다. 24시간 내에 판매 확정을 진행해주세요.",
                    notification_type='bid_winner'
                )
                
                # 낙찰되지 않은 입찰자들에게 알림
                for bid in bids:
                    if not bid.is_selected:
                        Notification.objects.create(
                            user=bid.seller,
                            groupbuy=groupbuy,
                            message=f"'{groupbuy.product.name}' 공구의 최종 선정 결과, 아쉽게도 낙찰되지 않으셨습니다.",
                            notification_type='bid_not_selected'
                        )
            
            groupbuy.status = 'final_selection_seller'
            groupbuy.seller_selection_end = now + timedelta(hours=6)  # 판매자 최종선택 6시간
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
            groupbuy.notify_status_change()
            changed = True
        else:
            # 확정한 참여자가 없으면 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status} (참여자 확정 없음)")
            groupbuy.notify_status_change()
            
            # 모든 입찰자에게 취소 알림
            from ..models import Notification
            bids = Bid.objects.filter(groupbuy=groupbuy)
            for bid in bids:
                Notification.objects.create(
                    user=bid.seller,
                    groupbuy=groupbuy,
                    message=f"'{groupbuy.product.name}' 공구가 참여자 확정 부족으로 취소되었습니다.",
                    notification_type='groupbuy_cancelled'
                )
            
            changed = True
    
    # 3. 판매자 최종선택 시간 만료 처리
    elif groupbuy.status == 'final_selection_seller' and groupbuy.seller_selection_end and now > groupbuy.seller_selection_end:
        from ..models import Bid
        # 낙찰된 입찰자가 판매확정했는지 확인
        winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_selected=True).first()
        if not winning_bid:
            winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
        
        if winning_bid and winning_bid.final_decision == 'confirmed':
            # 판매자가 확정한 경우 -> 거래중
            groupbuy.status = 'in_progress'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> in_progress")
        else:
            # 판매자가 미선택 또는 포기한 경우 -> 취소
            groupbuy.status = 'cancelled'
            groupbuy.cancellation_reason = '낙찰자의 판매포기로 인한 공구 진행 취소' if winning_bid and winning_bid.final_decision == 'cancelled' else '판매자 최종선택 기간 만료'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> cancelled (판매자 미선택/포기)")
            
            # 참여자들에게 취소 알림
            from ..models import Notification, Participation
            participants = Participation.objects.filter(groupbuy=groupbuy)
            for participant in participants:
                Notification.objects.create(
                    user=participant.user,
                    groupbuy=groupbuy,
                    message=f"'{groupbuy.product.name}' 공구가 판매자 미선택으로 취소되었습니다.",
                    notification_type='groupbuy_cancelled'
                )
        
        groupbuy.notify_status_change()
        changed = True
    
    return changed or original_status != groupbuy.status

def update_groupbuys_status():
    """
    모든 진행 중인 공구의 상태를 업데이트합니다.
    
    Returns:
        int: 상태가 변경된 공구의 수
    """
    from ..models import GroupBuy  # 순환 참조 방지를 위해 함수 내에서 import
    
    active_statuses = ['recruiting', 'final_selection_buyers', 'final_selection_seller']  # v3.0: 새로운 상태 이름 사용
    active_groupbuys = GroupBuy.objects.filter(status__in=active_statuses)
    
    changed_count = 0
    
    for groupbuy in active_groupbuys:
        if update_groupbuy_status(groupbuy):
            changed_count += 1
            
    return changed_count

# 기존 함수들을 위한 alias
update_groupbuy_status_if_needed = update_groupbuy_status