from django.utils import timezone
from datetime import timedelta
import logging
from ..models import GroupBuy, Notification, Bid
from .email_sender import EmailSender

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """
    알림 스케줄러 유틸리티 클래스
    
    주기적인 알림 및 상태 업데이트를 처리합니다.
    """
    
    @staticmethod
    def send_bid_reminders():
        """
        입찰 마감 전 알림을 발송합니다.
        
        입찰 마감 시간이 가까워지는 공구에 대해 참여자들에게 알림을 발송합니다.
        """
        now = timezone.now()
        
        # 입찰 중인 공구 중 마감 시간이 12시간 이내인 공구 조회
        active_groupbuys = GroupBuy.objects.filter(
            status='bidding',
            end_time__gt=now,
            end_time__lte=now + timedelta(hours=12)
        )
        
        for groupbuy in active_groupbuys:
            # 마감까지 남은 시간 계산 (시간 단위)
            hours_left = int((groupbuy.end_time - now).total_seconds() / 3600)
            
            # 2시간 간격으로 알림 발송 (12, 10, 8, 6, 4, 2시간 전)
            if hours_left in [12, 10, 8, 6, 4, 2] and hours_left > 0:
                logger.info(f"공구 '{groupbuy.title}' 입찰 마감 {hours_left}시간 전 알림 발송")
                
                # 참여자 목록 조회
                participants = groupbuy.participation_set.all()
                
                for participant in participants:
                    user = participant.user
                    
                    # 알림 생성
                    Notification.objects.create(
                        user=user,
                        groupbuy=groupbuy,
                        message=f"입찰 마감까지 {hours_left}시간 남았습니다. 입찰에 참여해주세요.",
                        notification_type='reminder'
                    )
                    
                    # 이메일 발송
                    if user.email:
                        EmailSender.send_bid_reminder(
                            user.email,
                            groupbuy.title,
                            groupbuy.id,
                            hours_left
                        )
    
    @staticmethod
    def send_bid_confirmation_reminders():
        """
        입찰 확정 전 알림을 발송합니다.
        
        입찰 확정 시간이 가까워지는 공구에 대해 입찰자들에게 알림을 발송합니다.
        """
        now = timezone.now()
        
        # 최종선택 단계 중인 공구 조회
        confirmation_groupbuys = GroupBuy.objects.filter(
            status='final_selection',
            final_selection_end__gt=now,
            final_selection_end__lte=now + timedelta(hours=12)
        )
        
        for groupbuy in confirmation_groupbuys:
            # 마감까지 남은 시간 계산 (시간 단위)
            hours_left = int((groupbuy.final_selection_end - now).total_seconds() / 3600)
            
            # 2시간 간격으로 알림 발송 (12, 10, 8, 6, 4, 2시간 전)
            if hours_left in [12, 10, 8, 6, 4, 2] and hours_left > 0:
                logger.info(f"공구 '{groupbuy.title}' 투표 마감 {hours_left}시간 전 알림 발송")
                
                # 참여자 중 결정하지 않은 사람들 조회
                participants = groupbuy.participation_set.filter(final_decision='pending')
                
                for participant in participants:
                        user = participant.user
                        
                        # 알림 생성
                        Notification.objects.create(
                            user=user,
                            groupbuy=groupbuy,
                            message=f"투표 마감까지 {hours_left}시간 남았습니다. 확정/포기 여부를 선택해주세요.",
                            notification_type='reminder'
                        )
                        
                        # 이메일 발송
                        if user.email:
                            EmailSender.send_bid_confirmation_reminder(
                                user.email,
                                groupbuy.title,
                                groupbuy.id,
                                hours_left
                            )
                    
                    # 이메일 발송
                    if user.email:
                        EmailSender.send_bid_confirmation_reminder(
                            user.email,
                            groupbuy.title,
                            groupbuy.id,
                            hours_left
                        )
    
    @staticmethod
    def send_seller_confirmation_reminders():
        """
        판매자 확정 전 알림을 발송합니다.
        
        판매자 확정 시간이 가까워지는 공구에 대해 판매자에게 알림을 발송합니다.
        """
        now = timezone.now()
        
        # 판매자 확정 대기 중인 공구 조회
        # final_selection_end + 24시간이 판매자 확정 마감 시간
        seller_confirmation_groupbuys = GroupBuy.objects.filter(
            status='seller_confirmation'
        )
        
        for groupbuy in seller_confirmation_groupbuys:
            # 판매자 확정 마감 시간 계산
            seller_deadline = groupbuy.final_selection_end + timedelta(hours=24)
            
            # 현재 시간과 마감 시간 비교
            if now <= seller_deadline <= now + timedelta(hours=12):
                # 마감까지 남은 시간 계산 (시간 단위)
                hours_left = int((seller_deadline - now).total_seconds() / 3600)
                
                # 2시간 간격으로 알림 발송 (12, 10, 8, 6, 4, 2시간 전)
                if hours_left in [12, 10, 8, 6, 4, 2] and hours_left > 0:
                    logger.info(f"공구 '{groupbuy.title}' 판매자 확정 {hours_left}시간 전 알림 발송")
                    
                    # 낙찰자 조회 (이기는 입찰자 중 is_winner=True인 사람)
                    winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_winner=True).first()
                    
                    if winning_bid:
                        seller = winning_bid.seller
                        
                        # 알림 생성
                        Notification.objects.create(
                            user=seller,
                            groupbuy=groupbuy,
                            message=f"판매자 확정까지 {hours_left}시간 남았습니다. 확정 여부를 선택해주세요.",
                            notification_type='reminder'
                        )
                        
                        # 이메일 발송
                        if seller.email:
                            EmailSender.send_seller_confirmation_reminder(
                                seller.email,
                                groupbuy.title,
                                groupbuy.id,
                                hours_left
                            )
    
    @staticmethod
    def process_expired_confirmations():
        """
        기한이 만료된 최종선택 단계의 공구를 처리합니다.
        
        최종선택 기한이 지난 공구를 처리하고 확정하지 않은 참여자에게 패널티를 부여합니다.
        """
        now = timezone.now()
        
        # 최종선택 기한이 지난 공구 조회
        expired_groupbuys = GroupBuy.objects.filter(
            status='final_selection',
            final_selection_end__lt=now
        )
        
        for groupbuy in expired_groupbuys:
            logger.info(f"공구 '{groupbuy.title}' 최종선택 기한 만료 처리")
            
            # 선택하지 않은 참여자 조회
            participants = groupbuy.participation_set.all()
            not_confirmed_participants = participants.filter(final_decision='pending')
            
            # 선택하지 않은 참여자들에게 패널티 부여
            for participant in not_confirmed_participants:
                # 패널티 부여
                participant.user.penalty_points = participant.user.penalty_points + 10
                participant.user.save()
                
                # 참여 상태를 취소로 변경
                participant.final_decision = 'cancelled'
                participant.save()
                # 알림 생성
                Notification.objects.create(
                    user=participant.user,
                    groupbuy=groupbuy,
                    message="최종선택 기한이 만료되어 자동으로 취소 처리되었습니다. 패널티 10점이 부여되었습니다.",
                    notification_type='warning'
                )
                
                # 이메일 발송
                if participant.user.email:
                    EmailSender.send_notification_email(
                        participant.user.email,
                        "[둥지마켓] 최종선택 기한 만료 및 패널티 부여 안내",
                        'emails/final_selection_expired.html',
                        {
                            'groupbuy_title': groupbuy.title,
                            'groupbuy_id': groupbuy.id,
                            'penalty_points': 10,
                            'site_url': 'https://dungji-market.com',
                        }
                    )
            
            # 확정한 참여자가 있는지 확인
            confirmed_participants = participants.filter(final_decision='confirmed').count()
            
            if confirmed_participants >= 1:
                # 확정한 참여자가 있으면 판매자 확정 단계로 진행
                groupbuy.status = 'seller_confirmation'
                groupbuy.save()
                
                # 낙찰자 선정 로직은 GroupBuy.handle_final_selection_timeout에서 처리됨
                # 낙찰자 조회
                winning_bid = Bid.objects.filter(groupbuy=groupbuy, is_winner=True).first()
                
                if winning_bid and winning_bid.seller:
                    # 낙찰자에게 알림
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message="축하합니다! 귀하의 입찰이 낙찰되었습니다. 판매 확정 여부를 선택해주세요.",
                        notification_type='success'
                    )
                    
                    # 이메일 발송
                    if winning_bid.seller.email:
                        EmailSender.send_notification_email(
                            winning_bid.seller.email,
                            "[둥지마켓] 입찰 낙찰 안내",
                            'emails/bid_won.html',
                            {
                                'groupbuy_title': groupbuy.title,
                                'groupbuy_id': groupbuy.id,
                                'site_url': 'https://dungji-market.com',
                            }
                        )
            else:
                # 확정한 참여자가 없으면 공구 취소
                groupbuy.status = 'cancelled'
                groupbuy.save()
                
                # 모든 참여자에게 알림
                for participant in participants:
                    Notification.objects.create(
                        user=participant.user,
                        groupbuy=groupbuy,
                        message="최종선택 기한 내에 확정한 참여자가 없어 공구가 취소되었습니다.",
                        notification_type='failure'
                    )
                
                # 다른 입찰자들에게 알림
                other_bids = Bid.objects.filter(groupbuy=groupbuy).exclude(is_selected=True)
                for bid in other_bids:
                    if bid.seller:
                        Notification.objects.create(
                            user=bid.seller,
                            groupbuy=groupbuy,
                            message="아쉽게도 귀하의 입찰이 낙찰되지 않았습니다.",
                            notification_type='failure'
                        )
                        
                        # 이메일 발송
                        if bid.seller.email:
                            EmailSender.send_notification_email(
                                bid.seller.email,
                                "[둥지마켓] 입찰 결과 안내",
                                'emails/bid_lost.html',
                                {
                                    'groupbuy_title': groupbuy.title,
                                    'groupbuy_id': groupbuy.id,
                                    'site_url': 'https://dungji-market.com',
                                }
                            )
    
    @staticmethod
    def process_expired_seller_confirmations():
        """
        기한이 만료된 판매자 확정 대기 상태의 공구를 처리합니다.
        
        판매자 확정 기한이 지난 공구를 자동으로 완료 처리합니다.
        """
        now = timezone.now()
        
        # 판매자 확정 대기 상태의 공구 조회
        expired_groupbuys = GroupBuy.objects.filter(
            status='seller_confirmation'
        )
        
        for groupbuy in expired_groupbuys:
            # 판매자 확정 마감 시간 계산 (final_selection_end + 24시간)
            seller_deadline = groupbuy.final_selection_end + timedelta(hours=24)
            
            # 현재 시간이 판매자 확정 마감 시간을 지났는지 확인
            if now > seller_deadline:
                logger.info(f"공구 '{groupbuy.title}' 판매자 확정 기한 만료 처리")
                
                # 낙찰된 입찰 조회
                winning_bid = Bid.objects.filter(
                    groupbuy=groupbuy,
                    is_selected=True
                ).first()
                
                # 판매자가 확정하지 않은 경우 패널티 부여
                if winning_bid and winning_bid.final_decision == 'pending':
                    winning_bid.seller.penalty_points = winning_bid.seller.penalty_points + 20
                    winning_bid.seller.save()
                    winning_bid.final_decision = 'cancelled'
                    winning_bid.save()
                    
                    # 공구 취소 처리
                    groupbuy.status = 'cancelled'
                    groupbuy.save()
                    
                    # 판매자에게 패널티 알림
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message="판매 확정 기한이 만료되어 공구가 취소되었습니다. 패널티 20점이 부여되었습니다.",
                        notification_type='warning'
                    )
                else:
                    # 판매자가 이미 확정했다면 공구 완료 처리
                    groupbuy.status = 'completed'
                    groupbuy.save()
                
                if winning_bid and winning_bid.seller:
                    # 판매자에게 알림
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message="판매자 확정 기한이 만료되어 자동으로 판매가 확정되었습니다.",
                        notification_type='info'
                    )
                    
                    # 이메일 발송
                    if winning_bid.seller.email:
                        EmailSender.send_notification_email(
                            winning_bid.seller.email,
                            "[둥지마켓] 판매 자동 확정 안내",
                            'emails/seller_auto_confirmed.html',
                            {
                                'groupbuy_title': groupbuy.title,
                                'groupbuy_id': groupbuy.id,
                                'site_url': 'https://dungji-market.com',
                            }
                        )
                
                # 모든 참여자에게 알림
                participants = groupbuy.participation_set.all()
                for participant in participants:
                    # 판매자가 아닌 참여자에게만 알림 발송
                    if winning_bid and winning_bid.seller and participant.user.id == winning_bid.seller.id:
                        continue
                    
                    Notification.objects.create(
                        user=participant.user,
                        groupbuy=groupbuy,
                        message="공구가 완료되었습니다.",
                        notification_type='info'
                    )
    
    @staticmethod
    def run_all_tasks():
        """
        모든 스케줄링 작업을 실행합니다.
        """
        logger.info("알림 스케줄러 작업 시작")
        
        try:
            # 입찰 마감 알림
            NotificationScheduler.send_bid_reminders()
            
            # 입찰 확정 알림
            NotificationScheduler.send_bid_confirmation_reminders()
            
            # 판매자 확정 알림
            NotificationScheduler.send_seller_confirmation_reminders()
            
            # 기한 만료 처리
            NotificationScheduler.process_expired_confirmations()
            NotificationScheduler.process_expired_seller_confirmations()
            
            logger.info("알림 스케줄러 작업 완료")
        except Exception as e:
            logger.error(f"알림 스케줄러 작업 실패: {str(e)}")
