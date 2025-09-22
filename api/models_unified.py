"""
중고거래 통합 모델 (찜, 후기)
api 앱에 위치시켜 공통으로 사용
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class UnifiedFavorite(models.Model):
    """
    통합 찜 모델
    휴대폰과 전자제품 찜을 하나의 테이블에서 관리
    """
    ITEM_TYPE_CHOICES = [
        ('phone', '휴대폰'),
        ('electronics', '전자제품'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unified_favorites')

    # 상품 타입과 ID
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='상품타입')
    item_id = models.IntegerField(verbose_name='상품ID')

    # 메타 정보 (조회 성능 향상을 위한 캐시)
    item_title = models.CharField(max_length=200, verbose_name='상품명')
    item_price = models.IntegerField(verbose_name='상품가격')
    item_status = models.CharField(max_length=20, verbose_name='상품상태')
    item_image_url = models.URLField(blank=True, verbose_name='대표이미지URL')

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
        return f"{self.user.username} - {self.item_title}"

    def get_item(self):
        """실제 상품 객체 반환"""
        if self.item_type == 'phone':
            from used_phones.models import UsedPhone
            return UsedPhone.objects.filter(id=self.item_id).first()
        else:
            from used_electronics.models import UsedElectronics
            return UsedElectronics.objects.filter(id=self.item_id).first()

    def update_cache(self):
        """캐시된 정보 업데이트"""
        item = self.get_item()
        if item:
            if self.item_type == 'phone':
                self.item_title = f"{item.brand} {item.model}"
            else:
                self.item_title = f"{item.brand} {item.model_name}"

            self.item_price = item.price
            self.item_status = item.status

            # 대표 이미지 URL
            if item.images.exists():
                first_image = item.images.first()
                if hasattr(first_image, 'image'):
                    self.item_image_url = first_image.image.url if first_image.image else ''

            self.save()


class UnifiedReview(models.Model):
    """
    통합 거래 후기 모델
    휴대폰과 전자제품 거래 후기를 하나의 테이블에서 관리
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

    # 상품 정보 (캐시)
    item_id = models.IntegerField(verbose_name='상품ID')
    item_title = models.CharField(max_length=200, verbose_name='상품명')
    final_price = models.IntegerField(verbose_name='거래가격')

    # 작성자와 대상
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')

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

    def save(self, *args, **kwargs):
        """저장 시 자동으로 캐시 정보 설정"""
        if not self.pk:  # 신규 생성 시
            transaction = self.get_transaction()
            if transaction:
                # reviewee 자동 설정
                if not self.reviewee_id:
                    if self.reviewer == transaction.buyer:
                        self.reviewee = transaction.seller
                        self.is_from_buyer = True
                    else:
                        self.reviewee = transaction.buyer
                        self.is_from_buyer = False

                # 상품 정보 캐시
                if self.item_type == 'phone':
                    item = transaction.phone
                    self.item_id = item.id
                    self.item_title = f"{item.brand} {item.model}"
                else:
                    item = transaction.electronics
                    self.item_id = item.id
                    self.item_title = f"{item.brand} {item.model_name}"

                self.final_price = transaction.final_price

        super().save(*args, **kwargs)


class UserStats(models.Model):
    """
    사용자 통계 (찜, 후기, 거래 통계)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='used_stats')

    # 찜 통계
    total_favorites = models.IntegerField(default=0, verbose_name='총찜수')
    phone_favorites = models.IntegerField(default=0, verbose_name='휴대폰찜수')
    electronics_favorites = models.IntegerField(default=0, verbose_name='전자제품찜수')

    # 후기 통계
    total_reviews_received = models.IntegerField(default=0, verbose_name='받은후기수')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='평균평점')

    # 평점별 개수
    rating_5_count = models.IntegerField(default=0)
    rating_4_count = models.IntegerField(default=0)
    rating_3_count = models.IntegerField(default=0)
    rating_2_count = models.IntegerField(default=0)
    rating_1_count = models.IntegerField(default=0)

    # 거래 통계
    total_sales = models.IntegerField(default=0, verbose_name='총판매수')
    total_purchases = models.IntegerField(default=0, verbose_name='총구매수')
    phone_sales = models.IntegerField(default=0, verbose_name='휴대폰판매수')
    phone_purchases = models.IntegerField(default=0, verbose_name='휴대폰구매수')
    electronics_sales = models.IntegerField(default=0, verbose_name='전자제품판매수')
    electronics_purchases = models.IntegerField(default=0, verbose_name='전자제품구매수')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='업데이트일')

    class Meta:
        db_table = 'user_used_stats'
        verbose_name = '사용자 중고거래 통계'
        verbose_name_plural = '사용자 중고거래 통계 관리'

    def __str__(self):
        return f"{self.user.username} - 평점 {self.average_rating}"

    def update_stats(self):
        """통계 재계산"""
        from django.db.models import Avg, Count

        # 찜 통계
        favorites = UnifiedFavorite.objects.filter(user=self.user)
        self.total_favorites = favorites.count()
        self.phone_favorites = favorites.filter(item_type='phone').count()
        self.electronics_favorites = favorites.filter(item_type='electronics').count()

        # 후기 통계
        reviews = UnifiedReview.objects.filter(reviewee=self.user)
        self.total_reviews_received = reviews.count()

        if self.total_reviews_received > 0:
            self.average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

            # 평점별 개수
            rating_counts = reviews.values('rating').annotate(count=Count('rating'))
            for item in rating_counts:
                setattr(self, f"rating_{item['rating']}_count", item['count'])

        self.save()