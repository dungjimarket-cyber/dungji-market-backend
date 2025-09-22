"""
Used Phones Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from api.models import Region
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class UsedPhoneRegion(models.Model):
    """
    중고폰과 지역 간의 다대다 관계를 관리하는 모델
    한 중고폰은 최대 3개까지의 지역을 가질 수 있음
    """
    used_phone = models.ForeignKey('UsedPhone', on_delete=models.CASCADE, related_name='regions', verbose_name='중고폰')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='used_phone_regions', verbose_name='지역')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    
    class Meta:
        db_table = 'used_phone_regions'
        verbose_name = '중고폰 지역'
        verbose_name_plural = '중고폰 지역 관리'
        unique_together = ('used_phone', 'region')
        
    def __str__(self):
        return f"{self.used_phone.model} - {self.region.name}"


class UsedPhone(models.Model):
    """중고폰 상품"""
    
    BRAND_CHOICES = [
        ('apple', '애플'),
        ('samsung', '삼성'),
        ('lg', 'LG'),
        ('xiaomi', '샤오미'),
        ('other', '기타'),
    ]
    
    CONDITION_CHOICES = [
        ('S', 'S급'),
        ('A', 'A급'),
        ('B', 'B급'),
        ('C', 'C급'),
    ]
    
    BATTERY_CHOICES = [
        ('excellent', '최상'),
        ('good', '좋음'),
        ('fair', '보통'),
        ('poor', '나쁨'),
        ('defective', '불량'),
    ]
    
    STATUS_CHOICES = [
        ('active', '판매중'),
        ('trading', '거래중'),
        ('sold', '판매완료'),
        ('deleted', '삭제됨'),
    ]
    
    # 판매자 정보
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phones')
    
    # 기본 정보
    brand = models.CharField(max_length=20, choices=BRAND_CHOICES)
    model = models.CharField(max_length=100, verbose_name='모델명')
    storage = models.IntegerField(null=True, blank=True, verbose_name='용량(GB)')
    color = models.CharField(max_length=50, null=True, blank=True, verbose_name='색상')
    
    # 가격 정보
    price = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9900000)], verbose_name='판매가격')  # 최대 990만원
    min_offer_price = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(9900000)], verbose_name='최소제안가격')  # 최대 990만원
    accept_offers = models.BooleanField(default=False, verbose_name='가격제안허용')
    
    # 상태 정보
    condition_grade = models.CharField(max_length=1, choices=CONDITION_CHOICES, verbose_name='상태등급')
    condition_description = models.TextField(null=True, blank=True, max_length=500, verbose_name='상태설명')
    battery_status = models.CharField(max_length=20, choices=BATTERY_CHOICES, default='good', verbose_name='배터리상태')
    
    # 구성품
    body_only = models.BooleanField(default=False, verbose_name='본체만')
    has_box = models.BooleanField(default=False, verbose_name='박스포함')
    has_charger = models.BooleanField(default=False, verbose_name='충전기포함')
    has_earphones = models.BooleanField(default=False, verbose_name='이어폰포함')
    
    # 상품 설명
    description = models.TextField(
        validators=[MinLengthValidator(10)],
        max_length=2000,
        verbose_name='상품설명'
    )
    
    # 거래 위치 (공구와 동일한 구조)
    region_type = models.CharField(max_length=20, default='local', verbose_name='지역 유형')  # local only for used phones
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='거래지역')
    region_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='지역명 백업')  # 지역명 백업
    meeting_place = models.CharField(max_length=200, null=True, blank=True, verbose_name='거래장소')
    
    # 상태 및 통계
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    view_count = models.IntegerField(default=0, verbose_name='조회수')
    favorite_count = models.IntegerField(default=0, verbose_name='찜개수')
    offer_count = models.IntegerField(default=0, verbose_name='제안수')
    is_modified = models.BooleanField(default=False, verbose_name='수정됨 표시')  # 견적 후 수정 시 True
    
    # 거래 완료 관련 필드
    seller_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='판매자 완료 시간')
    buyer_completed_at = models.DateTimeField(null=True, blank=True, verbose_name='구매자 완료 시간')
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sold_at = models.DateTimeField(null=True, blank=True, verbose_name='판매완료일')
    
    class Meta:
        db_table = 'used_phones'
        ordering = ['-created_at']
        verbose_name = '중고폰'
        verbose_name_plural = '중고폰'
    
    def __str__(self):
        return f"{self.model} - {self.seller.username}"


class UsedPhoneImage(models.Model):
    """중고폰 이미지"""
    phone = models.ForeignKey(UsedPhone, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='used_phones/%Y/%m/%d/', verbose_name='이미지')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='이미지 URL')
    thumbnail = models.ImageField(upload_to='used_phones/thumbs/%Y/%m/%d/', null=True, blank=True, verbose_name='썸네일')
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='썸네일 URL')
    is_main = models.BooleanField(default=False, verbose_name='대표이미지')
    order = models.IntegerField(default=0, verbose_name='순서')
    width = models.IntegerField(null=True, blank=True, verbose_name='가로크기')
    height = models.IntegerField(null=True, blank=True, verbose_name='세로크기')
    file_size = models.IntegerField(null=True, blank=True, verbose_name='파일크기')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'used_phone_images'
        ordering = ['order', 'id']
        verbose_name = '중고폰 이미지'
        verbose_name_plural = '중고폰 이미지'
    
    def save(self, *args, **kwargs):
        """S3 업로드 및 썸네일 생성"""
        try:
            # Django의 ImageField는 settings에 따라 자동으로 S3에 업로드됨
            logger.info(f"UsedPhoneImage save: 이미지 처리 시작")
            logger.info(f"USE_S3: {getattr(settings, 'USE_S3', False)}")
            
            if self.image:
                # 이미지 메타데이터 저장
                try:
                    from PIL import Image
                    img = Image.open(self.image)
                    self.width, self.height = img.size
                    logger.info(f"이미지 크기: {self.width}x{self.height}")
                except Exception as e:
                    logger.warning(f"이미지 메타데이터 추출 실패: {e}")
                
                # 파일 크기 저장
                if hasattr(self.image, 'size'):
                    self.file_size = self.image.size
                    logger.info(f"파일 크기: {self.file_size} bytes")
            
            super().save(*args, **kwargs)
            
            # S3 사용 시 URL 업데이트
            if settings.USE_S3 and self.image:
                if hasattr(self.image, 'url'):
                    self.image_url = self.image.url
                    logger.info(f"이미지 URL: {self.image_url}")
                    
                    # URL만 업데이트 (무한 루프 방지)
                    super().save(update_fields=['image_url'])
                    
        except Exception as e:
            logger.error(f"UsedPhoneImage save 오류: {e}")
            # 오류가 있어도 저장은 완료
            super().save(*args, **kwargs)




class UsedPhoneOffer(models.Model):
    """중고폰 가격 제안"""
    
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('accepted', '수락'),
        ('cancelled', '취소'),
    ]
    
    phone = models.ForeignKey(UsedPhone, on_delete=models.CASCADE, related_name='offers')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_offers')
    offered_price = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9900000)], verbose_name='제안금액')  # 최대 990만원
    message = models.TextField(null=True, blank=True, verbose_name='메시지')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    seller_message = models.TextField(null=True, blank=True, verbose_name='판매자메시지')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'used_phone_offers'
        ordering = ['-created_at']
        verbose_name = '가격 제안'
        verbose_name_plural = '가격 제안'


class TradeCancellation(models.Model):
    """거래 취소 기록"""
    
    CANCELLATION_REASONS = [
        # 구매자 취소 사유
        ('change_mind', '단순 변심'),
        ('found_better', '다른 상품 구매 결정'),
        ('seller_no_response', '판매자 연락 두절'),
        ('condition_mismatch', '상품 상태가 설명과 다름'),
        ('price_disagreement', '추가 비용 요구'),
        ('seller_cancel_request', '판매자 취소 요청'),
        # 판매자 취소 사유
        ('product_sold', '다른 경로로 판매됨'),
        ('buyer_no_response', '구매자 연락 두절'),
        ('buyer_no_show', '구매자 약속 불이행'),
        ('payment_issue', '결제 문제 발생'),
        ('buyer_unreasonable', '구매자 무리한 요구'),
        ('buyer_cancel_request', '구매자 취소 요청'),
        ('personal_reason', '개인 사정으로 판매 불가'),
        # 공통
        ('schedule_conflict', '거래 일정 조율 실패'),
        ('location_issue', '거래 장소 문제'),
        ('other', '기타'),
    ]
    
    CANCELLED_BY_CHOICES = [
        ('seller', '판매자'),
        ('buyer', '구매자'),
    ]
    
    phone = models.ForeignKey('UsedPhone', on_delete=models.CASCADE, related_name='cancellations')
    offer = models.ForeignKey('UsedPhoneOffer', on_delete=models.CASCADE, related_name='cancellations')
    cancelled_by = models.CharField(max_length=10, choices=CANCELLED_BY_CHOICES)
    canceller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trade_cancellations')
    reason = models.CharField(max_length=50, choices=CANCELLATION_REASONS)
    custom_reason = models.TextField(null=True, blank=True, verbose_name='기타 사유')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trade_cancellations'
        ordering = ['-created_at']
        verbose_name = '거래 취소 기록'
        verbose_name_plural = '거래 취소 기록'


class UsedPhoneDeletePenalty(models.Model):
    """중고폰 삭제 패널티"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_delete_penalties')
    phone_model = models.CharField(max_length=100, verbose_name='삭제된 상품명')
    had_offers = models.BooleanField(default=False, verbose_name='견적 존재 여부')
    penalty_end = models.DateTimeField(verbose_name='패널티 종료 시간')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'used_phone_delete_penalties'
        ordering = ['-created_at']
        verbose_name = '삭제 패널티'
        verbose_name_plural = '삭제 패널티'

    def is_active(self):
        """패널티가 현재 활성 상태인지 확인"""
        from django.utils import timezone
        return timezone.now() < self.penalty_end


class UsedPhoneTransaction(models.Model):
    """중고폰 거래 기록"""

    STATUS_CHOICES = [
        ('trading', '거래중'),
        ('completed', '거래완료'),
        ('cancelled', '거래취소'),
    ]

    phone = models.ForeignKey('UsedPhone', on_delete=models.CASCADE, related_name='transactions')
    offer = models.ForeignKey('UsedPhoneOffer', on_delete=models.CASCADE, related_name='transaction')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sold_transactions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bought_transactions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trading')

    # 거래 완료 확인
    seller_confirmed = models.BooleanField(default=False, verbose_name='판매자 확인')
    buyer_confirmed = models.BooleanField(default=False, verbose_name='구매자 확인')
    seller_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='판매자 확인 시간')
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='구매자 확인 시간')

    # 거래 정보
    final_price = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9900000)], verbose_name='최종거래가격')
    meeting_date = models.DateTimeField(null=True, blank=True, verbose_name='거래일시')
    meeting_location = models.CharField(max_length=200, null=True, blank=True, verbose_name='거래장소')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='거래완료일')

    class Meta:
        db_table = 'used_phone_transactions'
        ordering = ['-created_at']
        verbose_name = '중고폰 거래'
        verbose_name_plural = '중고폰 거래'

    def complete_trade(self):
        """양방향 확인 시 거래 완료 처리"""
        if self.seller_confirmed and self.buyer_confirmed:
            from django.utils import timezone
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

            # 상품 상태 업데이트
            self.phone.status = 'sold'
            self.phone.sold_at = timezone.now()
            self.phone.save()

            # 제안 상태 업데이트
            self.offer.status = 'accepted'
            self.offer.save()

            return True
        return False


class UsedPhoneReview(models.Model):
    """중고폰 거래 후기"""

    RATING_CHOICES = [
        (5, '매우 만족'),
        (4, '만족'),
        (3, '보통'),
        (2, '불만족'),
        (1, '매우 불만족'),
    ]

    transaction = models.ForeignKey('UsedPhoneTransaction', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_used_phone_reviews')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_used_phone_reviews')

    # 평가 내용
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='평점')
    comment = models.TextField(null=True, blank=True, verbose_name='후기내용')

    # 평가 항목 (선택적)
    is_punctual = models.BooleanField(null=True, blank=True, verbose_name='시간약속준수')
    is_friendly = models.BooleanField(null=True, blank=True, verbose_name='친절함')
    is_honest = models.BooleanField(null=True, blank=True, verbose_name='정직한거래')
    is_fast_response = models.BooleanField(null=True, blank=True, verbose_name='빠른응답')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'used_phone_reviews'
        ordering = ['-created_at']
        verbose_name = '중고폰 거래 후기'
        verbose_name_plural = '중고폰 거래 후기'
        unique_together = ('transaction', 'reviewer')  # 한 거래당 한 번만 평가 가능

    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username} ({self.rating}★)"


class UsedPhoneReport(models.Model):
    """중고폰 신고 시스템"""

    REPORT_TYPE_CHOICES = [
        ('fake_listing', '허위매물'),
        ('fraud', '사기'),
        ('abusive_language', '욕설'),
        ('inappropriate_behavior', '부적절한 행동'),
        ('spam', '스팸/광고'),
        ('other', '기타'),
    ]

    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('processing', '처리중'),
        ('resolved', '해결됨'),
        ('rejected', '거부됨'),
    ]

    # 신고 대상 (선택사항 - 사용자를 찾지 못해도 신고 가능)
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='received_used_phone_reports', verbose_name='신고대상')
    reported_phone = models.ForeignKey('UsedPhone', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports', verbose_name='신고상품')

    # 신고 대상 텍스트 정보 (사용자를 찾지 못한 경우)
    reported_nickname = models.CharField(max_length=100, null=True, blank=True, verbose_name='신고대상 닉네임')
    reported_phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name='신고대상 연락처')

    # 신고자 정보
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_used_phone_reports', verbose_name='신고자')

    # 신고 내용
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, verbose_name='신고유형')
    description = models.TextField(verbose_name='신고내용')

    # 처리 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='처리상태')
    admin_note = models.TextField(null=True, blank=True, verbose_name='관리자메모')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_used_phone_reports', verbose_name='처리자')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일시')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'used_phone_reports'
        ordering = ['-created_at']
        verbose_name = '중고폰 신고'
        verbose_name_plural = '중고폰 신고'

    def __str__(self):
        return f"{self.reporter.username} → {self.reported_user.username if self.reported_user else (self.reported_nickname or self.reported_phone_number or '정보없음')} ({self.get_report_type_display()})"


class UsedPhonePenalty(models.Model):
    """중고폰 사용자 패널티 시스템"""

    PENALTY_TYPE_CHOICES = [
        ('auto_report', '신고 누적'),
        ('manual_admin', '관리자 수동'),
        ('trade_violation', '거래 위반'),
        ('fake_listing', '허위매물'),
        ('abusive_behavior', '악성 행위'),
    ]

    STATUS_CHOICES = [
        ('active', '활성'),
        ('expired', '만료'),
        ('revoked', '해제'),
    ]

    # 패널티 대상자
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_report_penalties', verbose_name='패널티대상')

    # 패널티 정보
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPE_CHOICES, verbose_name='패널티유형')
    reason = models.TextField(verbose_name='패널티사유')
    duration_hours = models.IntegerField(default=24, verbose_name='패널티시간', help_text='시간 단위로 입력 (예: 24시간 = 1일, 168시간 = 7일)')

    # 관련 신고들 (선택사항)
    related_reports = models.ManyToManyField('UsedPhoneReport', blank=True, related_name='penalties', verbose_name='관련신고')

    # 패널티 시작일
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='시작일')

    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='상태')

    # 처리자 정보
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_used_phone_penalties', verbose_name='발령자')
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_used_phone_penalties', verbose_name='해제자')
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name='해제일시')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'used_phone_penalties'
        ordering = ['-created_at']
        verbose_name = '중고폰 패널티'
        verbose_name_plural = '중고폰 패널티'

    def get_end_date(self):
        """패널티 종료 예정 시간 계산"""
        from datetime import timedelta
        if not self.duration_hours or not self.start_date:
            return None
        return self.start_date + timedelta(hours=self.duration_hours)

    def is_active(self):
        """현재 패널티가 활성 상태인지 확인"""
        from django.utils import timezone
        if self.status != 'active':
            return False

        # 해제된 경우
        if self.revoked_at:
            return False

        # duration_hours가 없으면 비활성
        if not self.duration_hours:
            return False

        # 시간이 만료된 경우
        end_date = self.get_end_date()
        if end_date and timezone.now() > end_date:
            # 자동으로 상태를 만료로 변경
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False

        return True

    def get_remaining_hours(self):
        """남은 패널티 시간 계산"""
        from django.utils import timezone
        if not self.is_active():
            return 0

        end_date = self.get_end_date()
        if not end_date:
            return 0

        remaining = end_date - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0

        return int(remaining.total_seconds() / 3600)

    def __str__(self):
        hours_display = f"{self.duration_hours}시간"
        if self.duration_hours >= 24:
            days = self.duration_hours // 24
            remaining_hours = self.duration_hours % 24
            if remaining_hours > 0:
                hours_display = f"{days}일 {remaining_hours}시간"
            else:
                hours_display = f"{days}일"
        return f"{self.user.username} - {self.get_penalty_type_display()} ({hours_display})"
