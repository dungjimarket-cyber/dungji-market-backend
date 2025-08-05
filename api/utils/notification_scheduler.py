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
        
        # 구매자 최종선택 단계 중인 공구 조회
        confirmation_groupbuys = GroupBuy.objects.filter(
            status='final_selection_buyers',
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
                            message=f"구매자 최종선택 마감까지 {hours_left}시간 남았습니다. 구매 확정/포기를 선택해주세요.",
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
    
    @staticmethod
    def send_seller_confirmation_reminders():
        """
        판매자 확정 전 알림을 발송합니다.
        
        판매자 확정 시간이 가까워지는 공구에 대해 판매자에게 알림을 발송합니다.
        """
        now = timezone.now()
        
        # 판매자 최종선택 단계 중인 공구 조회
        seller_confirmation_groupbuys = GroupBuy.objects.filter(
            status='final_selection_seller',
            seller_selection_end__gt=now,
            seller_selection_end__lte=now + timedelta(hours=6)
        )
        
        for groupbuy in seller_confirmation_groupbuys:
            # 마감까지 남은 시간 계산 (시간 단위)
            hours_left = int((groupbuy.seller_selection_end - now).total_seconds() / 3600)
                
            # 1시간 간격으로 알림 발송 (6, 5, 4, 3, 2, 1시간 전)
            if hours_left in [6, 5, 4, 3, 2, 1] and hours_left > 0:
                logger.info(f"공구 '{groupbuy.title}' 판매자 확정 {hours_left}시간 전 알림 발송")
                
                # 낙찰된 입찰 조회
                winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
                
                if winning_bid and winning_bid.final_decision == 'pending':
                    seller = winning_bid.seller
                    # 알림 생성
                    Notification.objects.create(
                        user=seller,
                        groupbuy=groupbuy,
                        message=f"판매자 최종선택 마감까지 {hours_left}시간 남았습니다. 판매 확정/포기를 선택해주세요.",
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
        기한이 만료된 구매자 최종선택 단계의 공구를 처리합니다.
        
        구매자 최종선택 기한이 지난 공구를 처리하고 판매자 단계로 진행하거나 취소합니다.
        """
        now = timezone.now()
        
        # 구매자 최종선택 기한이 지난 공구 조회
        expired_groupbuys = GroupBuy.objects.filter(
            status='final_selection_buyers',
            final_selection_end__lt=now
        )
        
        for groupbuy in expired_groupbuys:
            logger.info(f"공구 '{groupbuy.title}' 구매자 최종선택 기한 만료 처리")
            
            # 선택하지 않은 참여자 조회 및 취소 처리
            participants = groupbuy.participation_set.all()
            not_confirmed_participants = participants.filter(final_decision='pending')
            
            # 선택하지 않은 참여자들을 포기로 처리 (패널티는 나중에 구매 확정률 기준으로 부여)
            for participant in not_confirmed_participants:
                # 참여 상태를 취소로 변경
                participant.final_decision = 'cancelled'
                participant.save()
                
                # 알림 생성
                Notification.objects.create(
                    user=participant.user,
                    groupbuy=groupbuy,
                    message="구매자 최종선택 기한이 만료되어 자동으로 포기 처리되었습니다.",
                    notification_type='warning'
                )
            
            # 확정한 참여자가 있는지 확인
            confirmed_count = participants.filter(final_decision='confirmed').count()
            total_count = participants.count()
            
            if confirmed_count > 0:
                # 확정한 참여자가 있으면 판매자 최종선택 단계로 진행
                groupbuy.status = 'final_selection_seller'
                groupbuy.seller_selection_end = now + timedelta(hours=6)
                groupbuy.save()
                
                # 낙찰된 입찰 조회
                winning_bid = Bid.objects.filter(groupbuy=groupbuy, status='selected').first()
                
                if winning_bid and winning_bid.seller:
                    # 판매자에게 알림
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message=f"{groupbuy.title} 공구의 판매자 최종 선택이 시작되었습니다. 6시간 내에 판매 확정/포기를 선택해주세요. (구매확정: {confirmed_count}/{total_count}명)",
                        notification_type='seller_selection_start'
                    )
                    
                    # 이메일 발송
                    if winning_bid.seller.email:
                        EmailSender.send_notification_email(
                            winning_bid.seller.email,
                            "[둥지마켓] 판매자 최종선택 시작 안내",
                            'emails/seller_selection_start.html',
                            {
                                'groupbuy_title': groupbuy.title,
                                'groupbuy_id': groupbuy.id,
                                'confirmed_count': confirmed_count,
                                'total_count': total_count,
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
                        message="구매자 최종선택 기한 내에 확정한 참여자가 없어 공구가 취소되었습니다.",
                        notification_type='failure'
                    )
                
                # 모든 입찰자들에게 알림
                all_bids = Bid.objects.filter(groupbuy=groupbuy)
                for bid in all_bids:
                    if bid.seller:
                        Notification.objects.create(
                            user=bid.seller,
                            groupbuy=groupbuy,
                            message="공구 참여자들이 구매를 포기하여 공구가 취소되었습니다.",
                            notification_type='failure'
                        )
    
    @staticmethod
    def process_expired_seller_confirmations():
        """
        기한이 만료된 판매자 최종선택 단계의 공구를 처리합니다.
        
        판매자 최종선택 기한이 지난 공구를 처리하고 공구를 완료/취소 처리합니다.
        """
        now = timezone.now()
        
        # 판매자 최종선택 기한이 지난 공구 조회
        expired_groupbuys = GroupBuy.objects.filter(
            status='final_selection_seller',
            seller_selection_end__lt=now
        )
        
        for groupbuy in expired_groupbuys:
            logger.info(f"공구 '{groupbuy.title}' 판매자 최종선택 기한 만료 처리")
            
            # 낙찰된 입찰 조회
            winning_bid = Bid.objects.filter(
                groupbuy=groupbuy,
                status='selected'
            ).first()
            
            # 판매자가 선택하지 않은 경우
            if winning_bid and winning_bid.final_decision == 'pending':
                winning_bid.final_decision = 'cancelled'
                winning_bid.save()
                
                # 구매 확정률 계산
                confirmed_count = groupbuy.participation_set.filter(final_decision='confirmed').count()
                total_count = groupbuy.participation_set.count()
                confirmation_rate = confirmed_count / total_count if total_count > 0 else 0
                
                # 50% 이하인 경우 패널티 면제
                if confirmation_rate > 0.5:
                    # 판매자에게 패널티 부여
                    try:
                        seller_profile = winning_bid.seller.userprofile
                        seller_profile.penalty_points += 10  # 패널티 점수 부과
                        seller_profile.save()
                        
                        # 패널티 알림
                        Notification.objects.create(
                            user=winning_bid.seller,
                            groupbuy=groupbuy,
                            message=f"판매자 최종선택 기한이 만료되어 공구가 취소되었습니다. 패널티 10점이 부여되었습니다. (구매확정률: {int(confirmation_rate*100)}%)",
                            notification_type='warning'
                        )
                    except:
                        pass
                else:
                    # 패널티 면제 알림
                    Notification.objects.create(
                        user=winning_bid.seller,
                        groupbuy=groupbuy,
                        message=f"판매자 최종선택 기한이 만료되어 공구가 취소되었습니다. 구매확정률이 50% 이하여서 패널티가 면제되었습니다. (구매확정률: {int(confirmation_rate*100)}%)",
                        notification_type='info'
                    )
                    
                    # 입찰권 환불 처리 (단품 입찰권만 환불, 무제한 구독권 제외)
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
                            
                            # 환불 알림 추가
                            Notification.objects.create(
                                user=winning_bid.seller,
                                groupbuy=groupbuy,
                                message=f"구매확정률이 50% 이하여서 사용한 입찰권이 환불되었습니다.",
                                notification_type='info'
                            )
                            logger.info(f"입찰권 자동 환불 완료 - 판매자: {winning_bid.seller.id}, 공구: {groupbuy.id}")
                        except Exception as e:
                            logger.error(f"입찰권 자동 환불 실패: {str(e)}")
            
            # 최종 상태 결정
            seller_confirmed = winning_bid and winning_bid.final_decision == 'confirmed'
            confirmed_participants = groupbuy.participation_set.filter(final_decision='confirmed').exists()
            
            if confirmed_participants and seller_confirmed:
                groupbuy.status = 'completed'
                
                # 모든 참여자에게 알림
                participants = groupbuy.participation_set.filter(final_decision='confirmed')
                for participant in participants:
                    Notification.objects.create(
                        user=participant.user,
                        groupbuy=groupbuy,
                        message="공구가 성공적으로 완료되었습니다!",
                        notification_type='success'
                    )
            else:
                groupbuy.status = 'cancelled'
                
                # 구매자 패널티 처리 (구매 확정 후 판매자가 포기한 경우에는 면제)
                if seller_confirmed or (winning_bid and winning_bid.final_decision == 'pending'):
                    # 판매자가 확정했거나 미선택인 경우에만 구매자 패널티
                    cancelled_participations = groupbuy.participation_set.filter(final_decision='cancelled')
                    for participation in cancelled_participations:
                        try:
                            user_profile = participation.user.userprofile
                            user_profile.penalty_points += 5  # 구매자 패널티
                            user_profile.save()
                            
                            Notification.objects.create(
                                user=participation.user,
                                groupbuy=groupbuy,
                                message="구매를 포기하여 패널티 5점이 부여되었습니다.",
                                notification_type='warning'
                            )
                        except:
                            pass
                
                # 공구 취소 알림
                all_participants = groupbuy.participation_set.all()
                for participant in all_participants:
                    Notification.objects.create(
                        user=participant.user,
                        groupbuy=groupbuy,
                        message="공구가 취소되었습니다.",
                        notification_type='failure'
                    )
            
            groupbuy.save(update_fields=['status'])
    
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


def send_reminder_notifications():
    """
    모든 리마인더 알림을 발송합니다.
    Vercel cron job에서 호출되는 함수입니다.
    """
    sent_count = 0
    try:
        # NotificationScheduler의 리마인더 작업 실행
        scheduler = NotificationScheduler()
        
        # 각 알림 발송 메서드 실행
        scheduler.send_bid_reminders()
        scheduler.send_bid_confirmation_reminders()
        scheduler.send_seller_confirmation_reminders()
        
        # 발송된 알림 수 집계 (최근 5분간 생성된 reminder 타입 알림)
        from datetime import timedelta
        recent_time = timezone.now() - timedelta(minutes=5)
        sent_count = Notification.objects.filter(
            notification_type='reminder',
            created_at__gte=recent_time
        ).count()
        
        logger.info(f"리마인더 알림 발송 완료: {sent_count}개")
        
    except Exception as e:
        logger.error(f"리마인더 알림 발송 실패: {str(e)}")
    
    return sent_count
