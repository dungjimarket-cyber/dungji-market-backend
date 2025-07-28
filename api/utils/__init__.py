# api/utils/__init__.py

from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def update_groupbuy_status(groupbuy):
    """
    단일 공구의 상태를 업데이트합니다.
    
    현재 시간과 공구의 각종 마감 시간을 비교하여 상태를 자동으로 업데이트합니다.
    
    상태 전환 규칙:
    1. recruiting: 입찰이 없는 상태
    2. bidding: 입찰이 1건 이상 있는 상태  
    3. voting (최종선택중): 공구 마감 후 12시간 동안
    4. completed (공구종료): 최종선택 기간 종료 후
    
    Args:
        groupbuy: 업데이트할 GroupBuy 객체
        
    Returns:
        bool: 상태가 변경되었는지 여부
    """
    now = timezone.now()
    original_status = groupbuy.status
    changed = False
    
    # 이미 종료된 상태면 변경하지 않음
    if groupbuy.status in ['completed', 'cancelled']:
        return False
    
    # 1. recruiting 상태에서 입찰이 생기면 bidding으로 변경
    if groupbuy.status == 'recruiting':
        from api.models import Bid
        if Bid.objects.filter(groupbuy=groupbuy).exists():
            groupbuy.status = 'bidding'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: recruiting -> bidding (입찰 발생)")
            changed = True
    
    # 2. 공구 마감 시간이 지났으면 voting으로 변경
    if groupbuy.status in ['recruiting', 'bidding'] and now > groupbuy.end_time:
        from api.models import Bid
        # 입찰이 있는 경우만 voting으로, 없으면 cancelled
        if Bid.objects.filter(groupbuy=groupbuy).exists():
            groupbuy.status = 'voting'
            groupbuy.voting_end = groupbuy.end_time + timedelta(hours=12)
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> voting")
            groupbuy.notify_status_change()
            changed = True
        else:
            groupbuy.status = 'cancelled'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> cancelled (입찰 없음)")
            changed = True
    
    # 투표 단계 -> 판매자 확정 대기 또는 취소
    elif groupbuy.status == 'voting' and now > groupbuy.voting_end:
        # 투표 결과 확인 및 낙찰자 선정
        from ..models_voting import BidVote
        from ..models import Bid
        from django.db.models import Count
        
        # 투표 수 집계
        total_votes = BidVote.objects.filter(groupbuy=groupbuy).count()
        
        if total_votes > 0:
            # 각 입찰별 투표 수 집계
            bid_votes = Bid.objects.filter(groupbuy=groupbuy).annotate(
                vote_count=Count('votes')
            ).order_by('-vote_count')
            
            # 최다 득표 입찰 확인
            if bid_votes:
                winning_bid = bid_votes.first()
                max_votes = winning_bid.vote_count
                
                # 동점자 확인
                tied_bids = [bid for bid in bid_votes if bid.vote_count == max_votes]
                
                if len(tied_bids) == 1:
                    # 단독 최다 득표자가 낙찰
                    winning_bid.is_winner = True
                    winning_bid.save()
                    logger.info(f"공구 '{groupbuy.title}' 낙찰자 선정: {winning_bid.seller.username} (득표수: {max_votes})")
                    
                    # 낙찰자에게 알림 발송
                    from ..models import Notification
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message=f"축하합니다! '{groupbuy.product.name}' 공구에 낙찰되셨습니다. 24시간 내에 판매 확정을 진행해주세요.",
                        notification_type='bid_winner'
                    )
                else:
                    # 동점자가 있는 경우: 먼저 입찰한 사람이 낙찰
                    winning_bid = min(tied_bids, key=lambda b: b.created_at)
                    winning_bid.is_winner = True
                    winning_bid.save()
                    logger.info(f"공구 '{groupbuy.title}' 동점 상황 - 선착순 낙찰자: {winning_bid.seller.username}")
                    
                    # 낙찰자에게 알림 발송
                    from ..models import Notification
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message=f"축하합니다! '{groupbuy.product.name}' 공구에 낙찰되셨습니다. (동점 - 선착순 선정) 24시간 내에 판매 확정을 진행해주세요.",
                        notification_type='bid_winner'
                    )
                
                # 낙찰되지 않은 입찰자들에게 알림
                for bid in bid_votes:
                    if not bid.is_winner:
                        Notification.objects.create(
                            user=bid.seller,
                            groupbuy=groupbuy,
                            message=f"'{groupbuy.product.name}' 공구의 최종 선정 결과, 아쉽게도 낙찰되지 않으셨습니다.",
                            notification_type='bid_not_selected'
                        )
            
            groupbuy.status = 'seller_confirmation'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
            groupbuy.notify_status_change()
            return True
        else:
            # 투표가 없으면 공구 취소
            groupbuy.status = 'cancelled'
            groupbuy.save()
            logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status} (투표 없음)")
            groupbuy.notify_status_change()
            
            # 모든 입찰자에게 취소 알림
            from ..models import Notification
            bids = Bid.objects.filter(groupbuy=groupbuy)
            for bid in bids:
                Notification.objects.create(
                    user=bid.seller,
                    groupbuy=groupbuy,
                    message=f"'{groupbuy.product.name}' 공구가 참여자 투표 부족으로 취소되었습니다.",
                    notification_type='groupbuy_cancelled'
                )
            
            return True
    
    # 3. 판매자 확정 대기 -> 완료
    elif groupbuy.status == 'seller_confirmation' and now > (groupbuy.voting_end + timedelta(hours=24)):
        groupbuy.status = 'completed'
        groupbuy.save()
        logger.info(f"공구 '{groupbuy.title}' 상태 변경: {original_status} -> {groupbuy.status}")
        groupbuy.notify_status_change()
        return True
    
    return changed or original_status != groupbuy.status

def update_groupbuys_status():
    """
    모든 진행 중인 공구의 상태를 업데이트합니다.
    
    Returns:
        int: 상태가 변경된 공구의 수
    """
    from ..models import GroupBuy  # 순환 참조 방지를 위해 함수 내에서 import
    
    # 진행 중인 모든 공구 조회 (recruiting 포함)
    active_statuses = ['recruiting', 'bidding', 'voting', 'seller_confirmation']
    active_groupbuys = GroupBuy.objects.filter(status__in=active_statuses)
    
    updated_count = 0
    for groupbuy in active_groupbuys:
        if update_groupbuy_status(groupbuy):
            updated_count += 1
    
    logger.info(f"총 {active_groupbuys.count()}개 공구 중 {updated_count}개 상태 업데이트 완료")
    return updated_count
