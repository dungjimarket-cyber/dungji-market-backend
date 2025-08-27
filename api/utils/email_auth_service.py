"""
이메일 인증 서비스
비밀번호 재설정, 이메일 확인 등을 위한 인증 코드 발송
"""

import random
import string
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.cache import cache
import hashlib
import logging
import resend

logger = logging.getLogger(__name__)


class EmailAuthService:
    """
    이메일 인증 관련 서비스
    """
    
    # 인증 코드 유효 시간 (분)
    CODE_EXPIRY_MINUTES = 10
    TOKEN_EXPIRY_HOURS = 24
    
    def __init__(self):
        """서비스 초기화"""
        # Resend API 키 설정
        if hasattr(settings, 'RESEND_API_KEY'):
            resend.api_key = settings.RESEND_API_KEY
            self.use_resend = True
        else:
            self.use_resend = False
            logger.warning("Resend API 키가 설정되지 않았습니다. Django 기본 이메일 백엔드를 사용합니다.")
    
    def generate_verification_code(self, length=6):
        """
        6자리 숫자 인증 코드 생성
        """
        return ''.join(random.choices(string.digits, k=length))
    
    def generate_reset_token(self, email):
        """
        비밀번호 재설정용 토큰 생성
        """
        # 이메일과 현재 시간을 조합하여 고유 토큰 생성
        timestamp = datetime.now().isoformat()
        token_string = f"{email}{timestamp}{settings.SECRET_KEY}"
        return hashlib.sha256(token_string.encode()).hexdigest()
    
    def store_verification_code(self, email, code, purpose='email_verification'):
        """
        인증 코드를 캐시에 저장
        
        Args:
            email: 이메일 주소
            code: 인증 코드
            purpose: 용도 (email_verification, password_reset 등)
        """
        cache_key = f"{purpose}:{email}"
        cache.set(cache_key, code, timeout=self.CODE_EXPIRY_MINUTES * 60)
        logger.info(f"인증 코드 저장: {email}, 용도: {purpose}")
    
    def verify_code(self, email, code, purpose='email_verification'):
        """
        인증 코드 검증
        
        Returns:
            bool: 인증 성공 여부
        """
        cache_key = f"{purpose}:{email}"
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == code:
            # 인증 성공 시 코드 삭제
            cache.delete(cache_key)
            logger.info(f"인증 코드 검증 성공: {email}")
            return True
        
        logger.warning(f"인증 코드 검증 실패: {email}")
        return False
    
    def send_verification_email(self, email, name=None):
        """
        이메일 인증 코드 발송
        
        Args:
            email: 수신자 이메일
            name: 수신자 이름 (선택)
        
        Returns:
            tuple: (성공여부, 인증코드 or 에러메시지)
        """
        try:
            # 인증 코드 생성
            code = self.generate_verification_code()
            
            # 코드 저장
            self.store_verification_code(email, code, 'email_verification')
            
            # 이메일 내용 생성
            context = {
                'name': name or '고객',
                'verification_code': code,
                'expiry_minutes': self.CODE_EXPIRY_MINUTES,
                'site_name': '둥지마켓',
                'site_url': settings.SITE_URL,
            }
            
            subject = '[둥지마켓] 이메일 인증 코드'
            
            if self.use_resend:
                # Resend 사용
                html_content = render_to_string('emails/verification_code.html', context)
                
                result = resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [email],
                    "subject": subject,
                    "html": html_content
                })
                
                if result.get('id'):
                    logger.info(f"인증 이메일 발송 성공 (Resend): {email}")
                    return True, code
                else:
                    raise Exception(f"Resend 발송 실패: {result}")
            
            else:
                # Django 기본 이메일 백엔드 사용
                html_content = render_to_string('emails/verification_code.html', context)
                text_content = strip_tags(html_content)
                
                if settings.DEBUG:
                    # 개발 환경에서는 로그만 출력
                    logger.info(f"[DEBUG] 인증 코드 이메일: {email}, 코드: {code}")
                    return True, code
                
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                logger.info(f"인증 이메일 발송 성공: {email}")
                return True, code
                
        except Exception as e:
            logger.error(f"인증 이메일 발송 실패: {email}, 오류: {str(e)}")
            return False, str(e)
    
    def send_password_reset_email(self, email, user):
        """
        비밀번호 재설정 이메일 발송
        
        Args:
            email: 수신자 이메일
            user: 사용자 객체
        
        Returns:
            tuple: (성공여부, 토큰 or 에러메시지)
        """
        try:
            # 재설정 토큰 생성
            token = self.generate_reset_token(email)
            
            # 토큰 저장 (24시간 유효)
            cache_key = f"password_reset:{email}"
            cache.set(cache_key, token, timeout=self.TOKEN_EXPIRY_HOURS * 3600)
            
            # 이메일 내용 생성
            reset_url = f"{settings.SITE_URL}/reset-password?token={token}&email={email}"
            
            context = {
                'name': user.name if hasattr(user, 'name') else user.username,
                'reset_url': reset_url,
                'expiry_hours': self.TOKEN_EXPIRY_HOURS,
                'site_name': '둥지마켓',
                'site_url': settings.SITE_URL,
            }
            
            subject = '[둥지마켓] 비밀번호 재설정'
            
            if self.use_resend:
                # Resend 사용
                html_content = render_to_string('emails/password_reset.html', context)
                
                result = resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": [email],
                    "subject": subject,
                    "html": html_content
                })
                
                if result.get('id'):
                    logger.info(f"비밀번호 재설정 이메일 발송 성공 (Resend): {email}")
                    return True, token
                else:
                    raise Exception(f"Resend 발송 실패: {result}")
            
            else:
                # Django 기본 이메일 백엔드 사용
                html_content = render_to_string('emails/password_reset.html', context)
                text_content = strip_tags(html_content)
                
                if settings.DEBUG:
                    # 개발 환경에서는 로그만 출력
                    logger.info(f"[DEBUG] 비밀번호 재설정: {email}, URL: {reset_url}")
                    return True, token
                
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                logger.info(f"비밀번호 재설정 이메일 발송 성공: {email}")
                return True, token
                
        except Exception as e:
            logger.error(f"비밀번호 재설정 이메일 발송 실패: {email}, 오류: {str(e)}")
            return False, str(e)
    
    def verify_reset_token(self, email, token):
        """
        비밀번호 재설정 토큰 검증
        
        Returns:
            bool: 검증 성공 여부
        """
        cache_key = f"password_reset:{email}"
        stored_token = cache.get(cache_key)
        
        if stored_token and stored_token == token:
            logger.info(f"비밀번호 재설정 토큰 검증 성공: {email}")
            return True
        
        logger.warning(f"비밀번호 재설정 토큰 검증 실패: {email}")
        return False
    
    def clear_reset_token(self, email):
        """
        비밀번호 재설정 토큰 삭제
        """
        cache_key = f"password_reset:{email}"
        cache.delete(cache_key)
        logger.info(f"비밀번호 재설정 토큰 삭제: {email}")


# 싱글톤 인스턴스
email_auth_service = EmailAuthService()