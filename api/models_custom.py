"""
커스텀 특가 모델
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from datetime import timedelta
import uuid
import logging
from api.models_region import Region

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomGroupBuy(models.Model):
    """커스텀 특가"""

    TYPE_CHOICES = [
        ('online', '온라인'),
        ('offline', '오프라인'),
    ]

    STATUS_CHOICES = [
        ('recruiting', '모집중'),
        ('pending_seller', '판매자 확정 대기'),
        ('completed', '선착순 마감'),
        ('cancelled', '취소'),
        ('expired', '기간만료'),
    ]

    ONLINE_DISCOUNT_TYPE_CHOICES = [
        ('link_only', '할인링크만 제공'),
        ('code_only', '할인코드만 제공'),
        ('both', '할인링크 + 할인코드'),
    ]

    DISCOUNT_VALID_DAYS_CHOICES = [
        (3, '3일'),
        (7, '7일'),
        (14, '14일'),
        (30, '30일'),
        (60, '60일'),
        (90, '90일'),
    ]

    # 커스텀 특가 전용 카테고리
    CATEGORY_CHOICES = [
        ('food', '음식/외식'),
        ('cafe', '카페/디저트'),
        ('beauty', '뷰티/미용'),
        ('fashion', '패션/의류'),
        ('sports', '스포츠/레저'),
        ('education', '교육/학원'),
        ('culture', '문화/공연'),
        ('travel', '여행/숙박'),
        ('electronics', '전자제품'),
        ('living', '생활용품'),
        ('book', '도서/문구'),
        ('health', '건강/의료'),
        ('pet', '반려동물'),
        ('car', '자동차/정비'),
        ('service', '서비스/기타'),
    ]

    # 기본 정보
    title = models.CharField(max_length=200, verbose_name='제목')
    description = models.TextField(verbose_name='설명')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='유형')
    categories = models.JSONField(default=list, verbose_name='카테고리')
    usage_guide = models.TextField(null=True, blank=True, verbose_name='이용안내', help_text='사용기간, 시간 조건 등 이용 안내사항')

    # 가격 정보
    pricing_type = models.CharField(
        max_length=20,
        choices=[('single_product', '단일상품'), ('all_products', '전품목 할인')],
        default='single_product',
        verbose_name='가격 유형'
    )
    products = models.JSONField(
        default=list,
        blank=True,
        verbose_name='상품 목록',
        help_text='단일상품 최대 10개 [{"name": "상품명", "original_price": 100000, "discount_rate": 10}]'
    )
    # 하위 호환성을 위한 기존 필드 (deprecated)
    product_name = models.CharField(
        max_length=200,
        null=True, blank=True,
        verbose_name='상품명 (구버전)',
        help_text='(구버전 - products 필드 사용 권장)'
    )
    original_price = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MaxValueValidator(100000000)],
        verbose_name='정가 (구버전)',
        help_text='(구버전 - products 필드 사용 권장, 최대 1억원)'
    )
    discount_rate = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        verbose_name='할인율 (전품목용)',
        help_text='전품목 할인 시 사용, 0~99%'
    )

    # 인원 정보
    target_participants = models.PositiveIntegerField(
        validators=[MinValueValidator(2), MaxValueValidator(10)],
        verbose_name='목표 인원'
    )
    current_participants = models.PositiveIntegerField(default=0, verbose_name='현재 인원')

    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    max_wait_hours = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        verbose_name='최대 대기 시간(시간)',
        help_text='1~168시간 (1시간~7일), deprecated - expired_at 사용 권장'
    )
    expired_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='만료 시간',
        help_text='모집 마감 시간 (최소 1시간 이후 ~ 최대 7일 이내)'
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료일')
    seller_decision_deadline = models.DateTimeField(
        null=True, blank=True,
        verbose_name='판매자 결정 기한',
        help_text='기간 만료 시 인원 미달인 경우 24시간'
    )

    # 할인 유효기간
    discount_valid_days = models.PositiveIntegerField(
        null=True, blank=True,
        choices=DISCOUNT_VALID_DAYS_CHOICES,
        verbose_name='할인 유효기간',
        help_text='할인코드/링크 사용 가능 기간'
    )
    discount_valid_until = models.DateTimeField(null=True, blank=True, verbose_name='할인 만료일')

    # 판매자 옵션
    allow_partial_sale = models.BooleanField(
        default=False,
        verbose_name='부분 판매 허용',
        help_text='기간 종료 시 인원 미달이어도 판매자가 최종 결정 가능'
    )

    # 판매자 정보
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_groupbuys',
        verbose_name='판매자'
    )

    # 온라인 할인 제공 방식
    online_discount_type = models.CharField(
        max_length=20,
        choices=ONLINE_DISCOUNT_TYPE_CHOICES,
        null=True, blank=True,
        verbose_name='온라인 할인 제공 방식',
        help_text='온라인 공구인 경우만 설정'
    )

    # 온라인
    discount_url = models.TextField(null=True, blank=True, verbose_name='할인링크')
    discount_codes = models.JSONField(default=list, blank=True, verbose_name='할인코드 목록')

    # 오프라인
    location = models.CharField(max_length=300, null=True, blank=True, verbose_name='매장 위치')
    location_detail = models.TextField(null=True, blank=True, verbose_name='위치 상세')
    phone_number = models.CharField(
        max_length=20,
        null=True, blank=True,
        verbose_name='연락처',
        validators=[
            RegexValidator(
                r'^[\d\-\(\)\s]+$',
                '숫자, 하이픈, 괄호, 공백만 입력 가능합니다.'
            )
        ]
    )

    # 링크 메타데이터
    meta_title = models.CharField(max_length=300, null=True, blank=True)
    meta_image = models.TextField(null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    meta_price = models.PositiveIntegerField(null=True, blank=True)

    # 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='recruiting',
        verbose_name='상태'
    )

    # 통계
    view_count = models.PositiveIntegerField(default=0, verbose_name='조회수')
    favorite_count = models.PositiveIntegerField(default=0, verbose_name='찜 수')

    class Meta:
        db_table = 'custom_groupbuy'
        verbose_name = '커스텀 특가'
        verbose_name_plural = '커스텀 특가 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['type']),
            models.Index(fields=['seller']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['expired_at'], name='idx_custom_expired'),
            models.Index(fields=['seller_decision_deadline'], name='idx_custom_seller_decision'),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"

    @property
    def final_price(self):
        """최종 가격 계산 (단일상품 여러 개 지원)"""
        if self.pricing_type != 'single_product':
            return None  # 전품목 할인은 가격 없음

        # products 필드 사용 (최신 방식)
        if self.products and len(self.products) > 0:
            # 여러 상품의 최종 가격 리스트 반환
            prices = []
            for product in self.products:
                if 'original_price' in product and 'discount_rate' in product:
                    final = int(product['original_price'] * (100 - product['discount_rate']) / 100)
                    prices.append(final)
            return prices if prices else None

        # 하위 호환성: 기존 필드 사용 (구버전)
        if self.original_price and self.discount_rate:
            return int(self.original_price * (100 - self.discount_rate) / 100)

        return None

    @property
    def is_completed(self):
        """목표 달성 여부"""
        if self.current_participants is None or self.target_participants is None:
            return False
        return self.current_participants >= self.target_participants

    @property
    def seller_type(self):
        """판매자 유형"""
        if self.seller is None:
            return 'individual'
        return 'business' if hasattr(self.seller, 'is_business_verified') and self.seller.is_business_verified else 'individual'

    @property
    def seller_name(self):
        """판매자 이름"""
        if self.seller is None:
            return ""
        return self.seller.username

    @property
    def is_business_verified(self):
        """사업자 인증 여부"""
        if self.seller is None:
            return False
        return self.seller.is_business_verified if hasattr(self.seller, 'is_business_verified') else False

    def save(self, *args, **kwargs):
        """저장 시 만료 시간 자동 계산 (deprecated - 프론트에서 expired_at 직접 전송)"""
        if not self.pk and not self.expired_at and self.max_wait_hours:
            self.expired_at = timezone.now() + timedelta(hours=self.max_wait_hours)

        super().save(*args, **kwargs)

    def complete_groupbuy(self):
        """공구 완료 처리"""
        from django.db import transaction

        with transaction.atomic():
            self.status = 'completed'
            self.completed_at = timezone.now()

            # 할인 유효기간 설정
            if self.discount_valid_days:
                self.discount_valid_until = timezone.now() + timedelta(days=self.discount_valid_days)

            self.save()

            # 할인 발급
            self.issue_discounts()

            logger.info(f"공구 완료: {self.title} ({self.current_participants}명)")

    def issue_discounts(self):
        """할인코드/링크 발급"""
        from django.core.exceptions import ValidationError

        participants = self.participants.filter(status='confirmed')
        participant_count = participants.count()

        if self.type == 'online':
            if self.online_discount_type in ['code_only', 'both']:
                if len(self.discount_codes) < participant_count:
                    logger.error(f"할인코드 부족: {self.title} - 코드:{len(self.discount_codes)} 참여자:{participant_count}")
                    raise ValidationError(
                        f'할인코드가 부족합니다. (필요: {participant_count}, 보유: {len(self.discount_codes)})'
                    )

            for i, participant in enumerate(participants):
                if self.online_discount_type in ['link_only', 'both']:
                    participant.discount_url = self.discount_url

                if self.online_discount_type in ['code_only', 'both']:
                    participant.discount_code = self.discount_codes[i]

                participant.discount_valid_until = self.discount_valid_until
                participant.save()

        elif self.type == 'offline':
            if len(self.discount_codes) < participant_count:
                logger.error(f"할인코드 부족: {self.title} - 코드:{len(self.discount_codes)} 참여자:{participant_count}")
                raise ValidationError(
                    f'할인코드가 부족합니다. (필요: {participant_count}, 보유: {len(self.discount_codes)})'
                )

            for i, participant in enumerate(participants):
                participant.discount_code = self.discount_codes[i]
                participant.discount_valid_until = self.discount_valid_until
                participant.save()

        logger.info(f"할인 발급 완료: {self.title} ({participant_count}명)")

    def check_expiration(self):
        """기간 만료 체크"""
        if self.status != 'recruiting':
            return

        now = timezone.now()

        if now >= self.expired_at:
            # 목표 달성 시 완료
            if self.current_participants >= self.target_participants:
                self.complete_groupbuy()
                return

            # 0명 참여: 즉시 취소
            if self.current_participants == 0:
                self.status = 'expired'
                self.save()
                logger.info(f"공구 만료 (0명): {self.title}")
                return

            # 1명 이상 + 부분 판매 허용: 판매자 결정 대기
            if self.current_participants >= 1 and self.allow_partial_sale:
                self.status = 'pending_seller'
                self.seller_decision_deadline = timezone.now() + timedelta(hours=24)
                self.save()
                logger.info(f"판매자 결정 대기: {self.title} ({self.current_participants}명)")
                return

            # 그 외: 즉시 취소
            self.status = 'expired'
            self.save()
            logger.info(f"공구 만료 (인원 미달): {self.title}")

    def early_close(self, seller_user):
        """조기 종료 (즉시 완료)"""
        from django.db import transaction
        from django.core.exceptions import PermissionDenied, ValidationError

        # 권한 체크
        if self.seller != seller_user:
            raise PermissionDenied('판매자만 조기 종료할 수 있습니다.')

        # 상태 체크
        if self.status != 'recruiting':
            raise ValidationError('모집 중인 공구만 조기 종료할 수 있습니다.')

        # 최소 인원 체크
        if self.current_participants < 1:
            raise ValidationError('최소 1명 이상 참여해야 조기 종료할 수 있습니다.')

        # 즉시 완료 처리
        self.complete_groupbuy()
        logger.info(f"조기 종료 완료: {self.title} ({self.current_participants}명)")


class CustomGroupBuyImage(models.Model):
    """공구 이미지"""

    custom_groupbuy = models.ForeignKey(
        CustomGroupBuy,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='공구'
    )
    image_url = models.TextField(verbose_name='이미지 URL')
    order_index = models.PositiveIntegerField(default=0, verbose_name='순서')
    is_primary = models.BooleanField(default=False, verbose_name='대표 이미지')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')

    class Meta:
        db_table = 'custom_groupbuy_image'
        verbose_name = '공구 이미지'
        verbose_name_plural = '공구 이미지 관리'
        ordering = ['order_index']
        unique_together = [('custom_groupbuy', 'order_index')]

    def __str__(self):
        return f"{self.custom_groupbuy.title} - 이미지 {self.order_index + 1}"


class CustomParticipant(models.Model):
    """참여자"""

    STATUS_CHOICES = [
        ('confirmed', '확정'),
        ('cancelled', '취소'),
    ]

    custom_groupbuy = models.ForeignKey(
        CustomGroupBuy,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='공구'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_participations',
        verbose_name='사용자'
    )
    participated_at = models.DateTimeField(auto_now_add=True, verbose_name='참여일')

    # 할인 정보
    participation_code = models.CharField(max_length=50, unique=True, verbose_name='참여 코드')
    discount_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='할인코드')
    discount_url = models.TextField(null=True, blank=True, verbose_name='할인링크')

    # 사용 정보
    discount_used = models.BooleanField(default=False, verbose_name='사용 여부')
    discount_used_at = models.DateTimeField(null=True, blank=True, verbose_name='사용일')
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_custom_discounts',
        verbose_name='검증자'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed',
        verbose_name='상태'
    )

    class Meta:
        db_table = 'custom_participant'
        verbose_name = '참여자'
        verbose_name_plural = '참여자 관리'
        unique_together = [('custom_groupbuy', 'user')]
        ordering = ['participated_at']

    def __str__(self):
        return f"{self.user.username} - {self.custom_groupbuy.title}"

    def save(self, *args, **kwargs):
        # 참여 코드 자동 생성
        if not self.participation_code:
            self.participation_code = f"DJM-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class CustomFavorite(models.Model):
    """찜"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_favorites',
        verbose_name='사용자'
    )
    custom_groupbuy = models.ForeignKey(
        CustomGroupBuy,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='공구'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='찜한 날짜')

    class Meta:
        db_table = 'custom_favorite'
        verbose_name = '찜'
        verbose_name_plural = '찜 관리'
        unique_together = [('user', 'custom_groupbuy')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.custom_groupbuy.title}"


class CustomGroupBuyRegion(models.Model):
    """커스텀 공구와 지역 간의 다대다 관계"""

    custom_groupbuy = models.ForeignKey(
        CustomGroupBuy,
        on_delete=models.CASCADE,
        related_name='region_links',
        verbose_name='공구'
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='custom_groupbuy_regions',
        verbose_name='지역'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')

    class Meta:
        db_table = 'custom_groupbuy_region'
        verbose_name = '커스텀 공구 지역'
        verbose_name_plural = '커스텀 공구 지역 관리'
        unique_together = [('custom_groupbuy', 'region')]
        ordering = ['region__code']

    def __str__(self):
        return f"{self.custom_groupbuy.title} - {self.region.full_name}"


class CustomNoShowReport(models.Model):
    """커스텀 공구 노쇼 신고 (기존 NoShowReport 복사)"""
    REPORT_STATUS_CHOICES = [
        ('pending', '처리중'),
        ('completed', '처리완료'),
        ('on_hold', '보류중'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_noshow_reports_made', verbose_name='신고자')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_noshow_reports_received', verbose_name='피신고자')
    custom_groupbuy = models.ForeignKey(CustomGroupBuy, on_delete=models.CASCADE, related_name='noshow_reports', verbose_name='커스텀 공구')
    participant = models.ForeignKey(CustomParticipant, on_delete=models.CASCADE, related_name='noshow_reports', verbose_name='참여 정보', null=True, blank=True)

    report_type = models.CharField(max_length=20, choices=[
        ('buyer_noshow', '구매자 노쇼'),
        ('seller_noshow', '판매자 노쇼'),
    ], verbose_name='신고 유형')

    content = models.TextField(verbose_name='신고 내용')
    evidence_image = models.ImageField(upload_to='custom_noshow_reports/', null=True, blank=True, verbose_name='증빙 이미지')
    evidence_image_2 = models.ImageField(upload_to='custom_noshow_reports/', null=True, blank=True, verbose_name='증빙 이미지 2')
    evidence_image_3 = models.ImageField(upload_to='custom_noshow_reports/', null=True, blank=True, verbose_name='증빙 이미지 3')

    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='pending', verbose_name='처리 상태')
    admin_comment = models.TextField(blank=True, verbose_name='관리자 코멘트')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='신고일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_custom_noshow_reports', verbose_name='처리자')

    edit_count = models.IntegerField(default=0, verbose_name='수정 횟수')
    last_edited_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 수정 시간')

    noshow_buyers = models.JSONField(default=list, blank=True, verbose_name='노쇼 구매자 목록')

    is_cancelled = models.BooleanField(default=False, verbose_name='취소 여부')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='취소 시간')
    cancellation_reason = models.TextField(blank=True, verbose_name='취소 사유')

    def can_edit(self):
        return self.status == 'pending' and self.edit_count < 1

    def can_cancel(self):
        return self.status == 'pending'

    class Meta:
        db_table = 'custom_noshow_report'
        verbose_name = '커스텀 노쇼 신고'
        verbose_name_plural = '커스텀 노쇼 신고 관리'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'reported_user', 'custom_groupbuy'],
                name='unique_custom_noshow_report_per_user_groupbuy'
            )
        ]

    def __str__(self):
        return f'{self.reporter.username}이 {self.reported_user.username}을 신고 ({self.custom_groupbuy.title})'


class CustomPenalty(models.Model):
    """커스텀 공구 패널티 (기존 Penalty 복사)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_penalties', verbose_name='사용자')
    reason = models.TextField(verbose_name='사유')
    penalty_type = models.CharField(max_length=20, verbose_name='페널티 유형',
                                   help_text='예: 노쇼, 판매포기, 기타')
    duration_hours = models.PositiveIntegerField(default=24, verbose_name='패널티 기간(시간)',
                                                 help_text='시간 단위로 입력 (예: 24, 48, 72)')
    start_date = models.DateTimeField(default=timezone.now, verbose_name='시작일')
    end_date = models.DateTimeField(verbose_name='종료일', blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    count = models.PositiveSmallIntegerField(default=1, verbose_name='누적 횟수')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='custom_penalties_created', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')

    custom_groupbuy = models.ForeignKey(CustomGroupBuy, on_delete=models.SET_NULL, null=True, blank=True, related_name='penalties', verbose_name='관련 커스텀 공구')
    participant = models.ForeignKey(CustomParticipant, on_delete=models.SET_NULL, null=True, blank=True, related_name='penalties', verbose_name='관련 참여 정보')

    def __str__(self):
        active = "[활성]" if self.is_active else "[비활성]"
        return f"{self.user.username} - {self.penalty_type} ({self.count}회) - {self.duration_hours}시간 {active}"

    def get_penalty_duration(self):
        return timezone.timedelta(hours=self.duration_hours)

    def save(self, *args, **kwargs):
        if not self.start_date:
            self.start_date = timezone.now()

        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(hours=self.duration_hours)

        if self.end_date and timezone.now() > self.end_date:
            self.is_active = False

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'custom_penalty'
        verbose_name = '커스텀 노쇼 패널티'
        verbose_name_plural = '커스텀 노쇼 패널티 관리'
        ordering = ['-created_at', '-start_date']