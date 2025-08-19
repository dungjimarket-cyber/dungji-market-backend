from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import string

User = get_user_model()

class PhoneVerification(models.Model):
    """휴대폰 인증 모델"""
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', '대기중'),
        ('verified', '인증완료'),
        ('expired', '만료됨'),
        ('failed', '실패'),
    )
    
    phone_number = models.CharField(max_length=20, verbose_name='휴대폰 번호')
    verification_code = models.CharField(max_length=6, verbose_name='인증 코드')
    status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        verbose_name='상태'
    )
    
    # 인증 관련 필드
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    expires_at = models.DateTimeField(verbose_name='만료일시')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='인증일시')
    
    # 시도 횟수 제한
    attempt_count = models.IntegerField(default=0, verbose_name='시도 횟수')
    max_attempts = models.IntegerField(default=5, verbose_name='최대 시도 횟수')
    
    # 사용자 연결 (선택적)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='phone_verifications',
        verbose_name='사용자'
    )
    
    # 인증 용도
    purpose = models.CharField(
        max_length=50,
        default='signup',
        verbose_name='용도',
        help_text='signup: 회원가입, reset_password: 비밀번호 재설정, change_phone: 전화번호 변경'
    )
    
    # IP 주소 (보안용)
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 주소')
    
    # 추가 정보 (이름, 생년월일, 성별 등)
    additional_info = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='추가 정보',
        help_text='인증 시 제공된 추가 정보 (이름, 생년월일, 성별 등)'
    )
    
    class Meta:
        verbose_name = '휴대폰 인증'
        verbose_name_plural = '휴대폰 인증'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.phone_number} - {self.get_status_display()} ({self.created_at.strftime("%Y-%m-%d %H:%M")})'
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # 새로 생성되는 경우
            if not self.verification_code:
                self.verification_code = self.generate_verification_code()
            if not self.expires_at:
                self.expires_at = timezone.now() + timedelta(minutes=3)  # 3분 후 만료
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_verification_code():
        """6자리 인증 코드 생성"""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """유효한 인증인지 확인"""
        return (
            self.status == 'pending' and 
            not self.is_expired() and 
            self.attempt_count < self.max_attempts
        )
    
    def verify(self, code):
        """인증 코드 확인"""
        if not self.is_valid():
            return False, '인증 시간이 만료되었거나 시도 횟수를 초과했습니다.'
        
        self.attempt_count += 1
        
        if self.verification_code == code:
            self.status = 'verified'
            self.verified_at = timezone.now()
            self.save()
            return True, '인증이 완료되었습니다.'
        else:
            self.save()  # 시도 횟수 증가 저장
            remaining_attempts = self.max_attempts - self.attempt_count
            if remaining_attempts > 0:
                return False, f'인증 코드가 일치하지 않습니다. (남은 시도: {remaining_attempts}회)'
            else:
                self.status = 'failed'
                self.save()
                return False, '시도 횟수를 초과했습니다. 다시 인증을 요청해주세요.'
    
    @classmethod
    def cleanup_expired(cls):
        """만료된 인증 정리"""
        expired_time = timezone.now() - timedelta(hours=24)  # 24시간 이상 된 것들
        cls.objects.filter(created_at__lt=expired_time).delete()
    
    @classmethod
    def get_recent_verification(cls, phone_number, purpose='signup'):
        """최근 유효한 인증 가져오기"""
        return cls.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            status='pending',
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
    
    @classmethod
    def check_rate_limit(cls, phone_number, ip_address=None):
        """발송 제한 확인 (스팸 방지)"""
        # 최근 1시간 내 발송 횟수 확인
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        # 전화번호별 제한
        phone_count = cls.objects.filter(
            phone_number=phone_number,
            created_at__gt=one_hour_ago
        ).count()
        
        if phone_count >= 5:  # 시간당 5회 제한
            return False, '1시간 내 발송 한도를 초과했습니다.'
        
        # IP별 제한 (선택적)
        if ip_address:
            ip_count = cls.objects.filter(
                ip_address=ip_address,
                created_at__gt=one_hour_ago
            ).count()
            
            if ip_count >= 10:  # IP당 시간당 10회 제한
                return False, 'IP 발송 한도를 초과했습니다.'
        
        # 최근 발송 시간 확인 (1분 내 재발송 방지)
        one_minute_ago = timezone.now() - timedelta(minutes=1)
        recent_verification = cls.objects.filter(
            phone_number=phone_number,
            created_at__gt=one_minute_ago
        ).exists()
        
        if recent_verification:
            return False, '1분 후에 다시 시도해주세요.'
        
        return True, None


class BusinessNumberVerification(models.Model):
    """사업자번호 검증 모델"""
    
    STATUS_CHOICES = (
        ('pending', '검증 대기'),
        ('valid', '유효'),
        ('invalid', '무효'),
        ('error', '검증 오류'),
    )
    
    business_number = models.CharField(max_length=12, verbose_name='사업자등록번호')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='검증 상태'
    )
    
    # 검증 결과 정보
    business_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='상호명')
    representative_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='대표자명')
    business_status = models.CharField(max_length=50, blank=True, null=True, verbose_name='사업상태')
    business_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='업종')
    establishment_date = models.DateField(null=True, blank=True, verbose_name='개업일')
    address = models.TextField(blank=True, null=True, verbose_name='사업장 주소')
    
    # 검증 관련 필드
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='검증 요청일')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='검증 완료일')
    error_message = models.TextField(blank=True, null=True, verbose_name='오류 메시지')
    
    # 사용자 연결
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='business_verifications',
        verbose_name='사용자'
    )
    
    # API 응답 저장 (디버깅용)
    api_response = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='API 응답',
        help_text='국세청 API 응답 데이터'
    )
    
    class Meta:
        verbose_name = '사업자번호 검증'
        verbose_name_plural = '사업자번호 검증'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business_number']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f'{self.business_number} - {self.get_status_display()} ({self.user.username})'
    
    @staticmethod
    def validate_business_number_format(business_number):
        """사업자번호 형식 검증"""
        # 하이픈 제거
        clean_number = business_number.replace('-', '')
        
        # 길이 체크
        if len(clean_number) != 10:
            return False, '사업자번호는 10자리여야 합니다.'
        
        # 숫자 체크
        if not clean_number.isdigit():
            return False, '사업자번호는 숫자만 입력 가능합니다.'
        
        # 체크섬 검증
        check_array = [1, 3, 7, 1, 3, 7, 1, 3, 5]
        sum_val = 0
        
        for i in range(9):
            sum_val += int(clean_number[i]) * check_array[i]
        
        sum_val += (int(clean_number[8]) * 5) // 10
        check_digit = (10 - (sum_val % 10)) % 10
        
        if check_digit != int(clean_number[9]):
            return False, '올바르지 않은 사업자번호입니다.'
        
        return True, clean_number
    
    def format_business_number(self):
        """사업자번호 형식화 (123-45-67890)"""
        if len(self.business_number) == 10:
            return f'{self.business_number[:3]}-{self.business_number[3:5]}-{self.business_number[5:]}'
        return self.business_number