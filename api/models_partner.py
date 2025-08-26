from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import secrets
import string

User = get_user_model()

class Partner(models.Model):
    """파트너사 정보를 관리하는 모델"""
    
    # 기본 정보
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='partner_profile',
        verbose_name='사용자'
    )
    partner_name = models.CharField(max_length=100, verbose_name='파트너사명')
    partner_code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='파트너 코드',
        help_text='추천 링크에 사용되는 고유 코드'
    )
    
    # 수수료 및 정산 정보
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('30.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name='수수료율 (%)'
    )
    
    # 계좌 정보
    bank_name = models.CharField(max_length=50, blank=True, verbose_name='은행명')
    account_number = models.CharField(max_length=50, blank=True, verbose_name='계좌번호')
    account_holder = models.CharField(max_length=100, blank=True, verbose_name='예금주')
    
    # 활성화 상태
    is_active = models.BooleanField(default=True, verbose_name='활성화 상태')
    
    # 관리 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    # 추가 설정
    minimum_settlement_amount = models.PositiveIntegerField(
        default=50000,
        verbose_name='최소 정산 금액'
    )
    
    class Meta:
        verbose_name = '파트너사'
        verbose_name_plural = '파트너사 관리'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.partner_name} ({self.partner_code})"
    
    def generate_partner_code(self):
        """고유한 파트너 코드 생성"""
        while True:
            # PARTNER_ 접두사 + 6자리 랜덤 코드
            code = 'PARTNER_' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if not Partner.objects.filter(partner_code=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        # 파트너 코드가 없으면 자동 생성
        if not self.partner_code:
            self.partner_code = self.generate_partner_code()
        super().save(*args, **kwargs)
    
    def get_referral_link(self, base_url='https://dungjimarket.com/join'):
        """추천 링크 생성"""
        return f"{base_url}?ref={self.partner_code}"
    
    def get_total_referrals(self):
        """총 추천 회원 수"""
        return self.referral_records.count()
    
    def get_active_subscribers(self):
        """활성 구독자 수"""
        return self.referral_records.filter(
            subscription_status='active'
        ).count()
    
    def get_monthly_revenue(self, year=None, month=None):
        """특정 월의 수수료 수익"""
        if not year or not month:
            now = timezone.now()
            year, month = now.year, now.month
            
        return self.referral_records.filter(
            created_at__year=year,
            created_at__month=month
        ).aggregate(
            total=models.Sum('commission_amount')
        )['total'] or 0
    
    def get_available_settlement_amount(self):
        """정산 가능 금액 (미정산된 수수료 합계)"""
        return self.referral_records.filter(
            settlement_status='pending'
        ).aggregate(
            total=models.Sum('commission_amount')
        )['total'] or 0


class ReferralRecord(models.Model):
    """추천을 통한 회원 가입 및 결제 기록"""
    
    SUBSCRIPTION_STATUS_CHOICES = (
        ('active', '활성'),
        ('cancelled', '해지'),
        ('paused', '휴면'),
    )
    
    SETTLEMENT_STATUS_CHOICES = (
        ('pending', '미정산'),
        ('requested', '정산요청'),
        ('completed', '정산완료'),
    )
    
    # 기본 정보
    partner = models.ForeignKey(
        Partner, 
        on_delete=models.CASCADE,
        related_name='referral_records',
        verbose_name='파트너사'
    )
    referred_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referral_records',
        verbose_name='추천 회원'
    )
    
    # 가입 정보
    joined_date = models.DateTimeField(auto_now_add=True, verbose_name='가입일자')
    
    # 구독 정보
    subscription_status = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='active',
        verbose_name='구독 상태'
    )
    subscription_amount = models.PositiveIntegerField(default=0, verbose_name='구독 금액')
    subscription_start_date = models.DateTimeField(null=True, blank=True, verbose_name='구독 시작일')
    subscription_end_date = models.DateTimeField(null=True, blank=True, verbose_name='구독 종료일')
    
    # 티켓 정보
    ticket_count = models.PositiveIntegerField(default=0, verbose_name='구매 티켓 수')
    ticket_amount = models.PositiveIntegerField(default=0, verbose_name='티켓 총 금액')
    
    # 결제 정보
    total_amount = models.PositiveIntegerField(default=0, verbose_name='총 결제 금액')
    commission_amount = models.PositiveIntegerField(default=0, verbose_name='수수료 금액')
    
    # 정산 정보
    settlement_status = models.CharField(
        max_length=20,
        choices=SETTLEMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='정산 상태'
    )
    settlement_date = models.DateTimeField(null=True, blank=True, verbose_name='정산일')
    
    # 관리 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '추천 기록'
        verbose_name_plural = '추천 기록 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'created_at']),
            models.Index(fields=['settlement_status']),
        ]
    
    def __str__(self):
        return f"{self.partner.partner_name} - {self.referred_user.username} ({self.total_amount}원)"
    
    def calculate_commission(self):
        """수수료 자동 계산"""
        commission_rate = self.partner.commission_rate / 100
        self.commission_amount = int(self.total_amount * commission_rate)
        return self.commission_amount
    
    def save(self, *args, **kwargs):
        # 총 금액 자동 계산
        self.total_amount = self.subscription_amount + self.ticket_amount
        
        # 수수료 자동 계산
        if self.total_amount > 0 and self.commission_amount == 0:
            self.calculate_commission()
        
        super().save(*args, **kwargs)


class PartnerSettlement(models.Model):
    """파트너 정산 요청 및 처리 기록"""
    
    STATUS_CHOICES = (
        ('pending', '요청됨'),
        ('processing', '처리중'),
        ('completed', '완료'),
        ('failed', '실패'),
        ('cancelled', '취소'),
    )
    
    # 기본 정보
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name='파트너사'
    )
    
    # 정산 정보
    settlement_amount = models.PositiveIntegerField(verbose_name='정산 금액')
    tax_invoice_requested = models.BooleanField(default=False, verbose_name='세금계산서 발행 요청')
    
    # 처리 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='처리 상태'
    )
    
    # 계좌 정보 (정산 요청 시점 기준)
    bank_name = models.CharField(max_length=50, verbose_name='은행명')
    account_number = models.CharField(max_length=50, verbose_name='계좌번호')
    account_holder = models.CharField(max_length=100, verbose_name='예금주')
    
    # 처리 정보
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name='요청일')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일')
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_settlements',
        verbose_name='처리자'
    )
    
    # 추가 정보
    memo = models.TextField(blank=True, verbose_name='메모')
    receipt_url = models.URLField(blank=True, verbose_name='영수증 URL')
    
    # 관리 정보
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '파트너 정산'
        verbose_name_plural = '파트너 정산 관리'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['requested_at']),
        ]
    
    def __str__(self):
        return f"{self.partner.partner_name} - {self.settlement_amount}원 ({self.get_status_display()})"
    
    def can_process(self):
        """정산 처리 가능 여부 확인"""
        return self.status in ['pending', 'processing']
    
    def complete_settlement(self, processed_by=None):
        """정산 완료 처리"""
        if not self.can_process():
            return False
        
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.processed_by = processed_by
        
        # 관련 추천 기록들의 정산 상태 업데이트
        ReferralRecord.objects.filter(
            partner=self.partner,
            settlement_status='requested'
        ).update(
            settlement_status='completed',
            settlement_date=self.processed_at
        )
        
        self.save()
        return True


class PartnerLink(models.Model):
    """파트너 추천 링크 관리"""
    
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='파트너사'
    )
    
    # 링크 정보
    original_url = models.URLField(verbose_name='원본 URL')
    short_code = models.CharField(max_length=10, unique=True, verbose_name='단축 코드')
    short_url = models.URLField(verbose_name='단축 URL')
    
    # 통계 정보
    click_count = models.PositiveIntegerField(default=0, verbose_name='클릭 수')
    conversion_count = models.PositiveIntegerField(default=0, verbose_name='전환 수')
    
    # 관리 정보
    is_active = models.BooleanField(default=True, verbose_name='활성화 상태')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '파트너 링크'
        verbose_name_plural = '파트너 링크 관리'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.partner.partner_name} - {self.short_url}"
    
    def generate_short_code(self):
        """단축 코드 생성"""
        while True:
            code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            if not PartnerLink.objects.filter(short_code=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_short_code()
        if not self.short_url:
            self.short_url = f"https://dng.kr/{self.short_code}"
        super().save(*args, **kwargs)
    
    def increment_click(self):
        """클릭 수 증가"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def increment_conversion(self):
        """전환 수 증가"""
        self.conversion_count += 1
        self.save(update_fields=['conversion_count'])


class PartnerNotification(models.Model):
    """파트너용 알림"""
    
    TYPE_CHOICES = (
        ('signup', '신규 가입'),
        ('payment', '결제 완료'),
        ('cancellation', '구독 해지'),
        ('settlement', '정산 관련'),
        ('system', '시스템 알림'),
    )
    
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='파트너사'
    )
    
    # 알림 내용
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='알림 유형'
    )
    title = models.CharField(max_length=200, verbose_name='제목')
    message = models.TextField(verbose_name='메시지')
    
    # 관련 데이터
    referral_record = models.ForeignKey(
        ReferralRecord,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
        verbose_name='관련 추천 기록'
    )
    
    # 읽음 상태
    is_read = models.BooleanField(default=False, verbose_name='읽음 상태')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='읽은 시간')
    
    # 관리 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    
    class Meta:
        verbose_name = '파트너 알림'
        verbose_name_plural = '파트너 알림 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.partner.partner_name} - {self.title}"
    
    def mark_as_read(self):
        """읽음 처리"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PartnerBankAccount(models.Model):
    """파트너 은행계좌 정보"""
    BANK_CODE_CHOICES = [
        ('002', '산업은행'),
        ('003', '기업은행'),
        ('004', 'KB국민은행'),
        ('005', '수협은행'),
        ('007', '수협중앙회'),
        ('008', '수출입은행'),
        ('011', 'NH농협은행'),
        ('012', '농협중앙회'),
        ('020', '우리은행'),
        ('023', 'SC제일은행'),
        ('027', '한국씨티은행'),
        ('031', '대구은행'),
        ('032', '부산은행'),
        ('034', '광주은행'),
        ('035', '제주은행'),
        ('037', '전북은행'),
        ('039', '경남은행'),
        ('045', '새마을금고'),
        ('048', '신협'),
        ('050', '저축은행'),
        ('064', '산림조합'),
        ('071', '우체국'),
        ('081', '하나은행'),
        ('088', '신한은행'),
        ('089', '케이뱅크'),
        ('090', '카카오뱅크'),
        ('092', '토스뱅크'),
    ]
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', '인증대기'),
        ('verified', '인증완료'),
        ('failed', '인증실패'),
    ]
    
    partner = models.OneToOneField(
        Partner,
        on_delete=models.CASCADE,
        related_name='bank_account',
        verbose_name='파트너'
    )
    bank_code = models.CharField(
        max_length=3,
        choices=BANK_CODE_CHOICES,
        verbose_name='은행코드'
    )
    bank_name = models.CharField(
        max_length=20,
        verbose_name='은행명'
    )
    account_number = models.CharField(
        max_length=50,
        verbose_name='계좌번호'
    )
    account_holder_name = models.CharField(
        max_length=50,
        verbose_name='예금주명'
    )
    account_holder_info = models.CharField(
        max_length=20,
        verbose_name='예금주 정보',
        help_text='생년월일(YYMMDD) 또는 사업자등록번호',
        blank=True
    )
    is_business = models.BooleanField(
        default=False,
        verbose_name='사업자 계좌 여부'
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending',
        verbose_name='인증 상태'
    )
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='인증 일시'
    )
    verification_result = models.TextField(
        blank=True,
        verbose_name='인증 결과'
    )
    is_primary = models.BooleanField(
        default=True,
        verbose_name='주 계좌 여부'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '파트너 은행계좌'
        verbose_name_plural = '파트너 은행계좌'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.partner.company_name} - {self.bank_name} {self.account_number}"