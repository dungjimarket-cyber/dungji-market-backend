"""
통합 찜하기 및 후기 모델
휴대폰과 전자제품 공통으로 사용
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class UnifiedFavorite(models.Model):
    """
    통합 찜하기 모델
    휴대폰, 전자제품 등 모든 중고거래 상품의 찜을 통합 관리
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_favorites')

    # Generic Relation으로 다양한 상품 타입 지원
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('usedphone', 'usedelectronics')}
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='찜한날짜')

    class Meta:
        db_table = 'used_unified_favorites'
        verbose_name = '통합 찜'
        verbose_name_plural = '통합 찜 관리'
        unique_together = ('user', 'content_type', 'object_id')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.content_object}"

    @property
    def item_type(self):
        """아이템 타입 반환 (phone/electronics)"""
        return 'phone' if self.content_type.model == 'usedphone' else 'electronics'

    @property
    def item(self):
        """실제 아이템 객체 반환"""
        return self.content_object


class UnifiedReview(models.Model):
    """
    통합 거래 후기 모델
    휴대폰, 전자제품 등 모든 중고거래의 후기를 통합 관리
    """

    RATING_CHOICES = [
        (5, '매우 만족'),
        (4, '만족'),
        (3, '보통'),
        (2, '불만족'),
        (1, '매우 불만족'),
    ]

    # 거래 정보 (Generic Relation)
    transaction_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('usedphonetransaction', 'electronicstransaction')}
    )
    transaction_id = models.PositiveIntegerField()
    transaction_object = GenericForeignKey('transaction_type', 'transaction_id')

    # 작성자 (구매자 또는 판매자)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_reviews_written')

    # 평가 대상 (판매자 또는 구매자)
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_reviews_received')

    # 평점 및 내용
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='평점'
    )
    comment = models.TextField(max_length=500, verbose_name='후기내용')

    # 추가 평가 항목
    is_punctual = models.BooleanField(default=False, verbose_name='시간약속잘지킴')
    is_friendly = models.BooleanField(default=False, verbose_name='친절함')
    is_honest = models.BooleanField(default=False, verbose_name='정직함')
    is_fast_response = models.BooleanField(default=False, verbose_name='응답빠름')

    # 메타 정보
    is_from_buyer = models.BooleanField(default=True, verbose_name='구매자후기여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'used_unified_reviews'
        verbose_name = '통합 후기'
        verbose_name_plural = '통합 후기 관리'
        unique_together = ('transaction_type', 'transaction_id', 'reviewer')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reviewee', '-created_at']),
            models.Index(fields=['reviewer', '-created_at']),
            models.Index(fields=['rating', '-created_at']),
        ]

    def __str__(self):
        return f"{self.reviewer.username} → {self.reviewee.username} ({self.rating}점)"

    @property
    def item_type(self):
        """거래 타입 반환 (phone/electronics)"""
        return 'phone' if self.transaction_type.model == 'usedphonetransaction' else 'electronics'

    @property
    def transaction(self):
        """실제 거래 객체 반환"""
        return self.transaction_object

    def save(self, *args, **kwargs):
        """저장 시 자동으로 reviewee 설정"""
        if not self.reviewee_id and self.transaction_object:
            # 거래에서 상대방 찾기
            if self.reviewer == self.transaction_object.buyer:
                self.reviewee = self.transaction_object.seller
                self.is_from_buyer = True
            else:
                self.reviewee = self.transaction_object.buyer
                self.is_from_buyer = False
        super().save(*args, **kwargs)


class UserReviewStats(models.Model):
    """
    사용자별 후기 통계 (캐시 용도)
    실시간 계산 부담을 줄이기 위한 통계 테이블
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='review_stats')

    # 받은 후기 통계
    total_reviews_received = models.IntegerField(default=0, verbose_name='받은후기수')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='평균평점')

    # 평점별 개수
    rating_5_count = models.IntegerField(default=0)
    rating_4_count = models.IntegerField(default=0)
    rating_3_count = models.IntegerField(default=0)
    rating_2_count = models.IntegerField(default=0)
    rating_1_count = models.IntegerField(default=0)

    # 추가 평가 항목 통계
    punctual_count = models.IntegerField(default=0, verbose_name='시간약속잘지킴수')
    friendly_count = models.IntegerField(default=0, verbose_name='친절함수')
    honest_count = models.IntegerField(default=0, verbose_name='정직함수')
    fast_response_count = models.IntegerField(default=0, verbose_name='응답빠름수')

    # 거래 통계
    total_sales = models.IntegerField(default=0, verbose_name='총판매수')
    total_purchases = models.IntegerField(default=0, verbose_name='총구매수')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='업데이트일')

    class Meta:
        db_table = 'used_user_review_stats'
        verbose_name = '사용자 후기 통계'
        verbose_name_plural = '사용자 후기 통계 관리'

    def __str__(self):
        return f"{self.user.username} - 평점 {self.average_rating}"

    def update_stats(self):
        """통계 재계산"""
        reviews = UnifiedReview.objects.filter(reviewee=self.user)

        self.total_reviews_received = reviews.count()

        if self.total_reviews_received > 0:
            # 평균 평점
            from django.db.models import Avg, Count
            self.average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

            # 평점별 개수
            rating_counts = reviews.values('rating').annotate(count=Count('rating'))
            for item in rating_counts:
                setattr(self, f"rating_{item['rating']}_count", item['count'])

            # 추가 평가 항목
            self.punctual_count = reviews.filter(is_punctual=True).count()
            self.friendly_count = reviews.filter(is_friendly=True).count()
            self.honest_count = reviews.filter(is_honest=True).count()
            self.fast_response_count = reviews.filter(is_fast_response=True).count()

        self.save()