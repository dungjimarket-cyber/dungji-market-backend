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
    original_price = models.PositiveIntegerField(verbose_name='정가')
    discount_rate = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='할인율'
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
        validators=[MinValueValidator(24), MaxValueValidator(720)],
        verbose_name='최대 대기 시간(시간)',
        help_text='24~720시간 (1~30일)'
    )
    expired_at = models.DateTimeField(verbose_name='만료 시간')
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
        """최종 가격 계산"""
        return int(self.original_price * (100 - self.discount_rate) / 100)

    @property
    def is_completed(self):
        """목표 달성 여부"""
        return self.current_participants >= self.target_participants

    @property
    def seller_type(self):
        """판매자 유형"""
        return 'business' if hasattr(self.seller, 'is_business_verified') and self.seller.is_business_verified else 'individual'

    @property
    def seller_name(self):
        """판매자 이름"""
        return self.seller.username

    @property
    def is_business_verified(self):
        """사업자 인증 여부"""
        return self.seller.is_business_verified if hasattr(self.seller, 'is_business_verified') else False

    def save(self, *args, **kwargs):
        """저장 시 만료 시간 자동 계산"""
        if not self.pk and not self.expired_at:
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