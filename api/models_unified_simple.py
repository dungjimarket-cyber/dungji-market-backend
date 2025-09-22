"""
중고거래 통합 모델 (찜, 후기) - 간단한 버전
기존 구조 그대로 유지하면서 타입 구분자만 추가
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class UnifiedFavorite(models.Model):
    """
    통합 찜 모델 - 기존 PhoneFavorite/ElectronicsFavorite 구조 유지
    단순히 item_type 필드만 추가
    """
    ITEM_TYPE_CHOICES = [
        ('phone', '휴대폰'),
        ('electronics', '전자제품'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_favorites')

    # 타입 구분자와 상품 ID
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='상품타입')
    item_id = models.IntegerField(verbose_name='상품ID')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='찜한날짜')

    class Meta:
        db_table = 'unified_favorites'
        verbose_name = '통합 찜'
        verbose_name_plural = '통합 찜 관리'
        unique_together = ('user', 'item_type', 'item_id')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['item_type', 'item_id']),
        ]

    def __str__(self):
        item_type_display = '휴대폰' if self.item_type == 'phone' else '전자제품'
        return f"{self.user.username} - {item_type_display} #{self.item_id}"

    def get_item(self):
        """실제 상품 객체 반환"""
        if self.item_type == 'phone':
            from used_phones.models import UsedPhone
            return UsedPhone.objects.filter(id=self.item_id).first()
        else:
            from used_electronics.models import UsedElectronics
            return UsedElectronics.objects.filter(id=self.item_id).first()


class UnifiedReview(models.Model):
    """
    통합 거래 후기 모델 - 기존 PhoneReview 구조 유지
    단순히 item_type 필드만 추가
    """
    ITEM_TYPE_CHOICES = [
        ('phone', '휴대폰'),
        ('electronics', '전자제품'),
    ]

    RATING_CHOICES = [
        (5, '매우 만족'),
        (4, '만족'),
        (3, '보통'),
        (2, '불만족'),
        (1, '매우 불만족'),
    ]

    # 거래 정보
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='상품타입')
    transaction_id = models.IntegerField(verbose_name='거래ID')

    # 작성자와 대상
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_reviews_written')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_reviews_received')

    # 평점 및 내용
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='평점'
    )
    comment = models.TextField(max_length=500, verbose_name='후기내용')

    # 추가 평가 항목 (기존과 동일)
    is_punctual = models.BooleanField(default=False, verbose_name='시간약속잘지킴')
    is_friendly = models.BooleanField(default=False, verbose_name='친절함')
    is_honest = models.BooleanField(default=False, verbose_name='정직함')
    is_fast_response = models.BooleanField(default=False, verbose_name='응답빠름')

    # 메타 정보
    is_from_buyer = models.BooleanField(default=True, verbose_name='구매자후기')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'unified_reviews'
        verbose_name = '통합 후기'
        verbose_name_plural = '통합 후기 관리'
        unique_together = ('item_type', 'transaction_id', 'reviewer')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reviewee', '-created_at']),
            models.Index(fields=['reviewer', '-created_at']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username} ({self.rating}점)"

    def get_transaction(self):
        """실제 거래 객체 반환"""
        if self.item_type == 'phone':
            from used_phones.models import UsedPhoneTransaction
            return UsedPhoneTransaction.objects.filter(id=self.transaction_id).first()
        else:
            from used_electronics.models import ElectronicsTransaction
            return ElectronicsTransaction.objects.filter(id=self.transaction_id).first()


class UnifiedReport(models.Model):
    """
    통합 신고 시스템 - 모든 중고거래에 사용
    제품 타입 구분 없이 사용자 중심으로 운영
    """
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

    # 신고 대상 - 사용자 또는 상품
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='received_reports', verbose_name='신고대상')

    # 상품 정보 (선택사항) - 타입과 ID로 관리
    item_type = models.CharField(max_length=20, blank=True, verbose_name='상품타입')
    item_id = models.IntegerField(null=True, blank=True, verbose_name='상품ID')

    # 신고 대상 텍스트 정보 (사용자를 찾지 못한 경우)
    reported_nickname = models.CharField(max_length=100, null=True, blank=True, verbose_name='신고대상 닉네임')
    reported_phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name='신고대상 연락처')

    # 신고자 정보
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_reports', verbose_name='신고자')

    # 신고 내용
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, verbose_name='신고유형')
    title = models.CharField(max_length=200, verbose_name='신고제목')
    description = models.TextField(verbose_name='신고내용')
    evidence = models.TextField(blank=True, verbose_name='증거자료', help_text='스크린샷 URL, 대화 내용 등')

    # 상태 및 처리
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='상태')
    admin_notes = models.TextField(blank=True, verbose_name='관리자메모')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='processed_reports', verbose_name='처리자')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일시')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='신고일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'unified_reports'
        verbose_name = '통합 신고'
        verbose_name_plural = '통합 신고 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reported_user', 'status']),
            models.Index(fields=['reporter', '-created_at']),
        ]

    def __str__(self):
        target = self.reported_user.username if self.reported_user else self.reported_nickname or '알 수 없음'
        return f"[{self.get_report_type_display()}] {target} - {self.reporter.username}"

    def get_item(self):
        """신고된 상품 객체 반환"""
        if not self.item_type or not self.item_id:
            return None

        if self.item_type == 'phone':
            from used_phones.models import UsedPhone
            return UsedPhone.objects.filter(id=self.item_id).first()
        elif self.item_type == 'electronics':
            from used_electronics.models import UsedElectronics
            return UsedElectronics.objects.filter(id=self.item_id).first()
        return None


class UnifiedPenalty(models.Model):
    """
    통합 패널티 시스템 - 모든 사용자에게 적용
    """
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penalties', verbose_name='패널티대상')

    # 패널티 정보
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPE_CHOICES, verbose_name='패널티유형')
    reason = models.TextField(verbose_name='패널티사유')
    duration_hours = models.IntegerField(default=24, verbose_name='패널티시간',
                                        help_text='시간 단위로 입력 (예: 24시간 = 1일, 168시간 = 7일)')

    # 관련 신고들 (선택사항)
    related_reports = models.ManyToManyField('UnifiedReport', blank=True, related_name='penalties', verbose_name='관련신고')

    # 패널티 시작일
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='시작일')

    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='상태')

    # 처리자 정보
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='issued_penalties', verbose_name='발령자')
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='revoked_penalties', verbose_name='해제자')
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name='해제일시')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'unified_penalties'
        verbose_name = '통합 패널티'
        verbose_name_plural = '통합 패널티 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

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


class UnifiedDeletePenalty(models.Model):
    """
    통합 삭제 패널티 - 견적 있는 상품 삭제 시
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delete_penalties')
    item_name = models.CharField(max_length=200, verbose_name='삭제된 상품명')
    item_type = models.CharField(max_length=20, verbose_name='상품타입')
    had_offers = models.BooleanField(default=False, verbose_name='견적 존재 여부')
    penalty_end = models.DateTimeField(verbose_name='패널티 종료 시간')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'unified_delete_penalties'
        verbose_name = '통합 삭제 패널티'
        verbose_name_plural = '통합 삭제 패널티 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'penalty_end']),
            models.Index(fields=['-created_at']),
        ]

    def is_active(self):
        """패널티가 현재 활성 상태인지 확인"""
        from django.utils import timezone
        return timezone.now() < self.penalty_end

    def __str__(self):
        return f"{self.user.username} - {self.item_name} ({self.item_type})"