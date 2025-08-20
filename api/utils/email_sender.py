from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    """
    이메일 발송 유틸리티 클래스
    
    다양한 알림 이메일을 발송하는 기능을 제공합니다.
    """
    
    @staticmethod
    def send_notification_email(recipient_email, subject, template_name, context):
        """
        알림 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            subject (str): 이메일 제목
            template_name (str): 이메일 템플릿 이름
            context (dict): 템플릿에 전달할 컨텍스트
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        try:
            # HTML 이메일 내용 렌더링
            html_message = render_to_string(template_name, context)
            # 텍스트 버전 생성
            plain_message = strip_tags(html_message)
            
            # 개발 환경에서는 실제 이메일 발송 대신 로그만 출력
            if settings.DEBUG:
                logger.info(f"[DEBUG] 이메일 발송 시뮬레이션: {recipient_email}, 제목: {subject}")
                logger.info(f"[DEBUG] 이메일 내용 (첫 100자): {plain_message[:100]}...")
                return True
            
            # 이메일 발송
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"이메일 발송 성공: {recipient_email}, 제목: {subject}")
            return True
        except Exception as e:
            logger.error(f"이메일 발송 실패: {recipient_email}, 제목: {subject}, 오류: {str(e)}")
            return False
    
    @staticmethod
    def send_bid_reminder(user_email, groupbuy_title, groupbuy_id, hours_left):
        """
        입찰 마감 알림 이메일을 발송합니다.
        
        Args:
            user_email (str): 사용자 이메일
            groupbuy_title (str): 공구 제목
            groupbuy_id (int): 공구 ID
            hours_left (int): 남은 시간(시간)
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        subject = f"[둥지마켓] 입찰 마감 {hours_left}시간 전 알림"
        context = {
            'groupbuy_title': groupbuy_title,
            'groupbuy_id': groupbuy_id,
            'hours_left': hours_left,
            'site_url': settings.SITE_URL,
        }
        return EmailSender.send_notification_email(
            user_email, 
            subject, 
            'emails/bid_reminder.html', 
            context
        )
    
    @staticmethod
    def send_bid_confirmation_reminder(user_email, groupbuy_title, groupbuy_id, hours_left):
        """
        입찰 확정 알림 이메일을 발송합니다.
        
        Args:
            user_email (str): 사용자 이메일
            groupbuy_title (str): 공구 제목
            groupbuy_id (int): 공구 ID
            hours_left (int): 남은 시간(시간)
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        subject = f"[둥지마켓] 입찰 확정 {hours_left}시간 전 알림"
        context = {
            'groupbuy_title': groupbuy_title,
            'groupbuy_id': groupbuy_id,
            'hours_left': hours_left,
            'site_url': settings.SITE_URL,
        }
        return EmailSender.send_notification_email(
            user_email, 
            subject, 
            'emails/bid_confirmation_reminder.html', 
            context
        )
    
    @staticmethod
    def send_seller_confirmation_reminder(user_email, groupbuy_title, groupbuy_id, hours_left):
        """
        판매자 확정 알림 이메일을 발송합니다.
        
        Args:
            user_email (str): 사용자 이메일
            groupbuy_title (str): 공구 제목
            groupbuy_id (int): 공구 ID
            hours_left (int): 남은 시간(시간)
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        subject = f"[둥지마켓] 판매자 확정 {hours_left}시간 전 알림"
        context = {
            'groupbuy_title': groupbuy_title,
            'groupbuy_id': groupbuy_id,
            'hours_left': hours_left,
            'site_url': settings.SITE_URL,
        }
        return EmailSender.send_notification_email(
            user_email, 
            subject, 
            'emails/seller_confirmation_reminder.html', 
            context
        )
