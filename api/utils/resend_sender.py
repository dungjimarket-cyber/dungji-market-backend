import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
import os

logger = logging.getLogger(__name__)

class ResendSender:
    """
    Resend를 사용한 이메일 발송 유틸리티 클래스
    
    무료 플랜: 월 3,000통
    우수한 전달률과 현대적인 API 제공
    """
    
    def __init__(self):
        # Resend API 키 설정
        self.api_key = os.getenv('RESEND_API_KEY')
        if self.api_key:
            resend.api_key = self.api_key
    
    @staticmethod
    def send_notification_email(recipient_email, subject, template_name, context, from_email=None):
        """
        Resend를 통해 알림 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            subject (str): 이메일 제목  
            template_name (str): 이메일 템플릿 이름
            context (dict): 템플릿에 전달할 컨텍스트
            from_email (str, optional): 발신자 이메일 (기본값: settings에서 가져옴)
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        try:
            # HTML 이메일 내용 렌더링
            html_message = render_to_string(template_name, context)
            # 텍스트 버전 생성
            plain_message = strip_tags(html_message)
            
            # 개발 환경에서는 시뮬레이션
            if settings.DEBUG:
                logger.info(f"[DEBUG] Resend 이메일 발송 시뮬레이션: {recipient_email}, 제목: {subject}")
                logger.info(f"[DEBUG] 이메일 내용 (첫 100자): {plain_message[:100]}...")
                return True
            
            # Resend API 키 확인
            api_key = os.getenv('RESEND_API_KEY')
            if not api_key:
                logger.error("RESEND_API_KEY 환경변수가 설정되지 않았습니다.")
                return False
            
            # 발신자 이메일 설정
            if not from_email:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@dungjimarket.com')
            
            # Resend를 통해 이메일 발송
            resend.api_key = api_key
            
            params = {
                "from": from_email,
                "to": [recipient_email],
                "subject": subject,
                "html": html_message,
                "text": plain_message,
            }
            
            email = resend.Emails.send(params)
            
            logger.info(f"Resend 이메일 발송 성공: {recipient_email}, 제목: {subject}, ID: {email.get('id', 'N/A')}")
            return True
            
        except Exception as e:
            logger.error(f"Resend 이메일 발송 실패: {recipient_email}, 제목: {subject}, 오류: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_verification(recipient_email, username, verification_code):
        """
        비밀번호 재설정 인증번호 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            username (str): 사용자명
            verification_code (str): 6자리 인증번호
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        subject = '[둥지마켓] 비밀번호 재설정 인증번호'
        context = {
            'verification_code': verification_code,
            'expires_minutes': 5,
            'username': username,
            'site_url': getattr(settings, 'SITE_URL', 'https://dungjimarket.com')
        }
        
        return ResendSender.send_notification_email(
            recipient_email=recipient_email,
            subject=subject,
            template_name='emails/password_reset_verification.html',
            context=context
        )
    
    @staticmethod
    def send_password_changed_confirmation(recipient_email, username, changed_at, ip_address=None):
        """
        비밀번호 변경 완료 확인 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            username (str): 사용자명
            changed_at (datetime): 변경 시각
            ip_address (str, optional): 변경한 IP 주소
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        subject = '[둥지마켓] 비밀번호가 변경되었습니다'
        context = {
            'username': username,
            'changed_at': changed_at,
            'ip_address': ip_address or '알 수 없음',
            'site_url': getattr(settings, 'SITE_URL', 'https://dungjimarket.com')
        }
        
        return ResendSender.send_notification_email(
            recipient_email=recipient_email,
            subject=subject,
            template_name='emails/password_changed_confirmation.html',
            context=context
        )
    
    @staticmethod
    def send_business_verification_result(recipient_email, username, is_approved, business_name=None, rejection_reason=None):
        """
        사업자 인증 결과 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            username (str): 사용자명
            is_approved (bool): 승인 여부
            business_name (str, optional): 상호명
            rejection_reason (str, optional): 거부 사유
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        if is_approved:
            subject = '[둥지마켓] 사업자 인증이 승인되었습니다'
            template_name = 'emails/business_verification_approved.html'
        else:
            subject = '[둥지마켓] 사업자 인증이 거부되었습니다'
            template_name = 'emails/business_verification_rejected.html'
        
        context = {
            'username': username,
            'business_name': business_name,
            'rejection_reason': rejection_reason,
            'site_url': getattr(settings, 'SITE_URL', 'https://dungjimarket.com')
        }
        
        return ResendSender.send_notification_email(
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            context=context
        )
    
    @staticmethod 
    def send_group_buy_notification(recipient_email, notification_type, groupbuy_title, groupbuy_id, **kwargs):
        """
        공동구매 관련 알림 이메일을 발송합니다.
        
        Args:
            recipient_email (str): 수신자 이메일
            notification_type (str): 알림 타입 (bid_reminder, bid_won, bid_lost 등)
            groupbuy_title (str): 공구 제목
            groupbuy_id (int): 공구 ID
            **kwargs: 추가 컨텍스트
            
        Returns:
            bool: 이메일 발송 성공 여부
        """
        notification_config = {
            'bid_reminder': {
                'subject': '[둥지마켓] 제안 마감 알림',
                'template': 'emails/bid_reminder.html'
            },
            'bid_won': {
                'subject': '[둥지마켓] 판매자 선정 알림', 
                'template': 'emails/bid_won.html'
            },
            'bid_lost': {
                'subject': '[둥지마켓] 판매자 미선정 알림',
                'template': 'emails/bid_lost.html'
            },
            'bid_confirmation_reminder': {
                'subject': '[둥지마켓] 제안 확정 알림',
                'template': 'emails/bid_confirmation_reminder.html'
            },
            'seller_confirmation_reminder': {
                'subject': '[둥지마켓] 판매자 확정 알림',
                'template': 'emails/seller_confirmation_reminder.html'
            }
        }
        
        config = notification_config.get(notification_type)
        if not config:
            logger.error(f"알 수 없는 알림 타입: {notification_type}")
            return False
        
        context = {
            'groupbuy_title': groupbuy_title,
            'groupbuy_id': groupbuy_id,
            'site_url': getattr(settings, 'SITE_URL', 'https://dungjimarket.com'),
            **kwargs
        }
        
        return ResendSender.send_notification_email(
            recipient_email=recipient_email,
            subject=config['subject'],
            template_name=config['template'],
            context=context
        )