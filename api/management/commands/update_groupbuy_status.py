from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import GroupBuy
from api.models_voting import BidVote
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '공구 상태를 자동으로 업데이트하고 투표 기간을 설정합니다'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1. 모집 마감 시간이 지난 recruiting 상태의 공구를 voting으로 변경
        recruiting_expired = GroupBuy.objects.filter(
            status='recruiting',
            end_time__lte=now
        )
        
        for groupbuy in recruiting_expired:
            # 입찰이 있는 경우에만 voting으로 변경
            if groupbuy.bid_set.exists():
                groupbuy.status = 'voting'
                # 투표 종료 시간 설정 (공구 마감 후 12시간)
                groupbuy.voting_end = groupbuy.end_time + timedelta(hours=12)
                groupbuy.save()
                logger.info(f"공구 {groupbuy.id}의 상태를 voting으로 변경하고 투표 종료 시간을 설정했습니다.")
            else:
                # 입찰이 없으면 cancelled로 변경
                groupbuy.status = 'cancelled'
                groupbuy.save()
                logger.info(f"입찰이 없는 공구 {groupbuy.id}를 취소 처리했습니다.")
        
        # 2. 투표 시간이 종료된 voting 상태의 공구 처리
        voting_expired = GroupBuy.objects.filter(
            status='voting',
            voting_end__lte=now
        )
        
        for groupbuy in voting_expired:
            # 투표 결과 집계
            vote_results = BidVote.objects.filter(groupbuy=groupbuy).values('bid').annotate(
                vote_count=Count('id')
            ).order_by('-vote_count')
            
            if vote_results:
                # 최다 득표 입찰 찾기
                winning_bid_id = vote_results[0]['bid']
                winning_bid = groupbuy.bid_set.get(id=winning_bid_id)
                
                # 낙찰 처리
                winning_bid.is_selected = True
                winning_bid.save()
                
                # 공구 상태를 final_selection으로 변경하고 12시간 타이머 설정
                groupbuy.status = 'final_selection'
                groupbuy.voting_end = now + timedelta(hours=12)  # 최종선택 12시간 타이머
                groupbuy.save()
                
                logger.info(f"공구 {groupbuy.id}의 투표가 종료되어 판매자 {winning_bid.seller.username}가 선정되었습니다. 최종선택 단계로 진입합니다.")
            else:
                # 투표가 없으면 첫 번째 입찰자를 자동 선정
                first_bid = groupbuy.bid_set.order_by('created_at').first()
                if first_bid:
                    first_bid.is_selected = True
                    first_bid.save()
                    groupbuy.status = 'final_selection'
                    groupbuy.voting_end = now + timedelta(hours=12)  # 최종선택 12시간 타이머
                    groupbuy.save()
                    logger.info(f"공구 {groupbuy.id}의 투표가 없어 첫 번째 입찰자를 자동 선정하고 최종선택 단계로 진입합니다.")
                else:
                    # 입찰도 없으면 취소
                    groupbuy.status = 'cancelled'
                    groupbuy.save()
                    logger.info(f"입찰이 없는 공구 {groupbuy.id}를 취소 처리했습니다.")
        
        # 3. 최종선택 시간이 종료된 final_selection 상태의 공구 처리
        final_selection_expired = GroupBuy.objects.filter(
            status='final_selection',
            voting_end__lte=now
        )
        
        for groupbuy in final_selection_expired:
            # 최종선택을 완료한 참여자들과 판매자 확인
            confirmed_participations = groupbuy.participation_set.filter(final_decision='confirmed')
            selected_bid = groupbuy.bid_set.filter(is_selected=True, final_decision='confirmed').first()
            
            if confirmed_participations.exists() and selected_bid:
                # 상호 확정된 경우 완료 처리
                groupbuy.status = 'completed'
                groupbuy.save()
                logger.info(f"공구 {groupbuy.id}의 최종선택이 완료되어 완료 상태로 변경되었습니다.")
            else:
                # 확정되지 않은 경우 취소 처리
                groupbuy.status = 'cancelled'
                groupbuy.save()
                logger.info(f"공구 {groupbuy.id}의 최종선택 시간이 만료되어 취소 처리되었습니다.")
        
        # 3. bidding 상태 처리 (필요시)
        # bidding 상태는 현재 사용하지 않지만, 향후 확장을 위해 남겨둠
        
        self.stdout.write(self.style.SUCCESS('공구 상태 업데이트가 완료되었습니다.'))