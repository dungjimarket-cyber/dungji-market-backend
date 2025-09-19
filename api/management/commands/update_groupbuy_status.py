from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import GroupBuy, Participation
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '공구 상태를 자동으로 업데이트합니다'

    def handle(self, *args, **options):
        now = timezone.now()
        updated_count = 0
        
        # 1. 시간이 지난 recruiting/bidding 상태의 공구를 final_selection_buyers로 변경
        time_expired_groupbuys = GroupBuy.objects.filter(
            status__in=['recruiting', 'bidding'],
            end_time__lte=now
        )
        
        for groupbuy in time_expired_groupbuys:
            # 입찰이 있는 경우에만 final_selection_buyers로 변경
            bids = groupbuy.bid_set.filter(status='pending').order_by('-amount', 'created_at')
            if bids.exists():
                # 최고 입찰자를 낙찰자로 선정
                winning_bid = bids.first()
                winning_bid.status = 'selected'
                winning_bid.is_selected = True
                winning_bid.save()
                
                # 다른 입찰자들의 상태 변경
                bids.exclude(id=winning_bid.id).update(status='not_selected', is_selected=False)
                
                groupbuy.status = 'final_selection_buyers'
                # 최종선택 종료 시간 설정 (공구 마감 후 12시간)
                groupbuy.final_selection_end = groupbuy.end_time + timedelta(hours=12)
                groupbuy.save()
                logger.info(f"공구 {groupbuy.id}의 상태를 final_selection_buyers로 변경하고 최종선택 종료 시간을 설정했습니다.")
                updated_count += 1
            else:
                # 입찰이 없으면 cancelled로 변경
                groupbuy.status = 'cancelled'
                groupbuy.save()
                logger.info(f"입찰이 없는 공구 {groupbuy.id}를 취소 처리했습니다.")
                updated_count += 1
        
        # 2. 최종선택 시간이 종료된 final_selection_buyers 상태의 공구 처리
        final_selection_expired = GroupBuy.objects.filter(
            status='final_selection_buyers',
            final_selection_end__lte=now
        )
        
        for groupbuy in final_selection_expired:
            # 확정한 참여자가 있는지 확인
            confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').count()

            if confirmed_participants > 0:
                # 이미 선정된 낙찰자가 있는지 확인
                winning_bid = groupbuy.bid_set.filter(status='selected', is_selected=True).first()

                if not winning_bid:
                    # 낙찰자가 없는 경우에만 새로 선정
                    winning_bid = groupbuy.bid_set.order_by('-amount', 'created_at').first()
                    if winning_bid:
                        winning_bid.status = 'selected'
                        winning_bid.is_selected = True
                        winning_bid.save()

                if winning_bid:
                    groupbuy.status = 'final_selection_seller'
                    groupbuy.seller_selection_end = now + timedelta(hours=6)
                    groupbuy.save()
                    logger.info(f"공구 {groupbuy.id}를 판매자 확정 대기 상태로 변경했습니다. (낙찰자: {winning_bid.seller.username})")
                    updated_count += 1
            else:
                # 확정한 참여자가 없으면 취소
                groupbuy.status = 'cancelled'
                groupbuy.save()
                logger.info(f"확정한 참여자가 없는 공구 {groupbuy.id}를 취소 처리했습니다.")
                updated_count += 1
        
        # 3. 판매자 확정 시간이 종료된 final_selection_seller 상태의 공구 처리
        seller_confirmation_expired = GroupBuy.objects.filter(
            status='final_selection_seller'
        )
        
        for groupbuy in seller_confirmation_expired:
            # seller_selection_end가 지났는지 확인
            if groupbuy.seller_selection_end and now > groupbuy.seller_selection_end:
                winning_bid = groupbuy.bid_set.filter(status='selected').first()
                
                if winning_bid:
                    # 판매자가 시간 내에 선택하지 않은 경우 자동으로 판매포기 처리
                    if winning_bid.final_decision == 'pending':
                        winning_bid.final_decision = 'rejected'
                        winning_bid.final_decision_at = now
                        winning_bid.save()
                        logger.info(f"공구 {groupbuy.id}의 판매자가 시간 내 미선택으로 자동 판매포기 처리되었습니다.")
                    
                    if winning_bid.final_decision == 'confirmed':
                        # 판매자가 확정했으면 진행중 상태로
                        groupbuy.status = 'in_progress'
                        groupbuy.save()
                        logger.info(f"공구 {groupbuy.id}를 거래 진행중 상태로 변경했습니다.")
                    else:
                        # 판매자가 포기했으면 취소
                        groupbuy.status = 'cancelled'
                        groupbuy.save()
                        logger.info(f"판매자가 판매포기한 공구 {groupbuy.id}를 취소 처리했습니다.")
                else:
                    # 낙찰자가 없으면 취소
                    groupbuy.status = 'cancelled'
                    groupbuy.save()
                    logger.info(f"낙찰자가 없는 공구 {groupbuy.id}를 취소 처리했습니다.")
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'총 {updated_count}개의 공구 상태가 업데이트되었습니다.'))