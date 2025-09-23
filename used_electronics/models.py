"""
전자제품/가전 중고거래 모델
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from api.models import Region
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class ElectronicsRegion(models.Model):
    """
    전자제품과 지역 간의 다대다 관계를 관리하는 모델
    한 전자제품은 최대 3개까지의 지역을 가질 수 있음
    """
    electronics = models.ForeignKey('UsedElectronics', on_delete=models.CASCADE, related_name='regions')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='electronics_regions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'used_electronics_regions'
        verbose_name = '전자제품 지역'
        verbose_name_plural = '전자제품 지역 관리'
        unique_together = ('electronics', 'region')

    def __str__(self):
        return f"{self.electronics.model_name} - {self.region.name}"


class UsedElectronics(models.Model):
    """전자제품/가전 중고거래"""

    # 카테고리 선택
    SUBCATEGORY_CHOICES = [
        ('laptop', '노트북/컴퓨터'),
        ('tv', 'TV/모니터'),
        ('game', '게임기'),
        ('camera', '카메라'),
        ('audio', '음향기기'),
        ('home', '생활가전'),
        ('etc', '기타'),
    ]

    # 상태 등급 (휴대폰과 동일)
    CONDITION_CHOICES = [
        ('S', 'S급'),
        ('A', 'A급'),
        ('B', 'B급'),
        ('C', 'C급'),
    ]

    # 사용 기간
    PURCHASE_PERIOD_CHOICES = [
        ('1month', '1개월 이내'),
        ('3months', '3개월'),
        ('6months', '6개월'),
        ('1year', '1년'),
        ('over', '1년 이상'),
    ]

    # 거래 상태 (휴대폰과 동일)
    STATUS_CHOICES = [
        ('active', '판매중'),
        ('trading', '거래중'),
        ('sold', '판매완료'),
        ('deleted', '삭제됨'),
    ]

    # ========== 기본 정보 ==========
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_electronics')

    # 카테고리
    subcategory = models.CharField(max_length=50, choices=SUBCATEGORY_CHOICES, verbose_name='카테고리')

    # 제품 정보
    brand = models.CharField(max_length=50, verbose_name='브랜드')
    model_name = models.CharField(max_length=100, verbose_name='모델명')

    # ========== 상태 정보 ==========
    purchase_period = models.CharField(max_length=50, blank=True, verbose_name='구매시기')
    usage_period = models.CharField(max_length=50, blank=True, verbose_name='사용기간')
    is_unused = models.BooleanField(default=False, verbose_name='미개봉')
    condition_grade = models.CharField(max_length=1, choices=CONDITION_CHOICES, verbose_name='상태등급')

    # ========== 구성품 ==========
    has_box = models.BooleanField(default=False, verbose_name='박스포함')
    has_charger = models.BooleanField(default=False, verbose_name='충전기/전원선포함')
    has_manual = models.BooleanField(default=False, verbose_name='매뉴얼포함')
    other_accessories = models.CharField(max_length=200, blank=True, verbose_name='기타구성품')

    # ========== 가격 정보 (휴대폰과 동일) ==========
    price = models.IntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(99000000)],
        verbose_name='판매가격'
    )
    min_offer_price = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(99000000)],
        verbose_name='최소제안가격'
    )
    accept_offers = models.BooleanField(default=False, verbose_name='가격제안허용')

    # ========== 상품 설명 ==========
    description = models.TextField(
        validators=[MinLengthValidator(10)],
        max_length=2000,
        verbose_name='상품설명'
    )

    # ========== 거래 정보 (휴대폰과 동일) ==========
    region_type = models.CharField(max_length=20, default='local', verbose_name='지역 유형')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='거래지역')
    region_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='지역명 백업')
    meeting_place = models.CharField(max_length=200, verbose_name='거래요청사항')  # 필수

    # ========== 추가 정보 (확장성) ==========
    has_warranty_card = models.BooleanField(default=False, verbose_name='보증서보유')
    serial_number = models.CharField(max_length=100, blank=True, verbose_name='시리얼넘버')
    warranty_end_date = models.DateField(null=True, blank=True, verbose_name='보증기한')
    purchase_date = models.DateField(null=True, blank=True, verbose_name='구매일')

    # JSON 필드로 카테고리별 특수 정보 저장
    extra_specs = models.JSONField(default=dict, blank=True, verbose_name='추가사양')

    # ========== 상태 관리 ==========
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='거래상태')

    # ========== 통계 ==========
    view_count = models.IntegerField(default=0, verbose_name='조회수')
    offer_count = models.IntegerField(default=0, verbose_name='제안수')
    favorite_count = models.IntegerField(default=0, verbose_name='찜수')

    # ========== 타임스탬프 ==========
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'used_electronics'
        verbose_name = '전자제품/가전'
        verbose_name_plural = '전자제품/가전 관리'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['subcategory', 'status']),
        ]

    def __str__(self):
        return f"{self.get_subcategory_display()} - {self.brand} {self.model_name}"

    def save(self, *args, **kwargs):
        """저장 시 지역명 백업"""
        if self.region:
            self.region_name = str(self.region)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """활성 상태 여부"""
        return self.status == 'active'

    @property
    def can_edit(self):
        """수정 가능 여부 - 가격제안이 들어오면 일부만 수정 가능"""
        return self.offer_count == 0


class ElectronicsImage(models.Model):
    """전자제품 이미지"""
    electronics = models.ForeignKey(UsedElectronics, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='electronics/%Y/%m/%d/', verbose_name='이미지')
    is_primary = models.BooleanField(default=False, verbose_name='대표이미지')
    order = models.IntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드일')

    class Meta:
        db_table = 'used_electronics_images'
        verbose_name = '전자제품 이미지'
        verbose_name_plural = '전자제품 이미지 관리'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.electronics.model_name} - 이미지 {self.order + 1}"


class ElectronicsOffer(models.Model):
    """전자제품 가격제안"""

    OFFER_STATUS_CHOICES = [
        ('pending', '대기중'),
        ('accepted', '수락됨'),
        ('rejected', '거절됨'),
        ('cancelled', '취소됨'),
    ]

    electronics = models.ForeignKey(UsedElectronics, on_delete=models.CASCADE, related_name='offers')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='electronics_offers')
    offer_price = models.IntegerField(validators=[MinValueValidator(1000)], verbose_name='제안가격')
    message = models.CharField(max_length=200, blank=True, verbose_name='메시지')
    status = models.CharField(max_length=20, choices=OFFER_STATUS_CHOICES, default='pending', verbose_name='상태')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='제안일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'used_electronics_offers'
        verbose_name = '전자제품 가격제안'
        verbose_name_plural = '전자제품 가격제안 관리'
        ordering = ['-created_at']
        # unique_together 제거: 5회까지 제안 가능

    def __str__(self):
        return f"{self.electronics.model_name} - {self.buyer.username} - {self.offer_price:,}원"




class ElectronicsTransaction(models.Model):
    """전자제품 거래"""

    TRANSACTION_STATUS_CHOICES = [
        ('in_progress', '거래중'),
        ('completed', '거래완료'),
        ('cancelled', '거래취소'),
    ]

    electronics = models.OneToOneField(UsedElectronics, on_delete=models.CASCADE, related_name='transaction')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='electronics_sales')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='electronics_purchases')
    final_price = models.IntegerField(verbose_name='거래가격')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='in_progress')

    # 거래 완료 추적
    seller_completed = models.BooleanField(default=False, verbose_name='판매자 완료')
    buyer_completed = models.BooleanField(default=False, verbose_name='구매자 완료')

    # 거래 취소 관련
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='cancelled_electronics_trades', verbose_name='취소자')
    cancellation_reason = models.CharField(max_length=50, blank=True, verbose_name='취소사유')
    cancellation_detail = models.TextField(blank=True, verbose_name='취소상세사유')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='거래시작일')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='거래완료일')

    class Meta:
        db_table = 'used_electronics_transactions'
        verbose_name = '전자제품 거래'
        verbose_name_plural = '전자제품 거래 관리'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.electronics.model_name} - {self.seller.username} → {self.buyer.username}"


class ElectronicsDeletePenalty(models.Model):
    """전자제품 삭제 패널티"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='electronics_delete_penalties')
    electronics_model = models.CharField(max_length=100, verbose_name='삭제된 상품명')
    had_offers = models.BooleanField(default=False, verbose_name='견적 존재 여부')
    penalty_end = models.DateTimeField(verbose_name='패널티 종료 시간')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'electronics_delete_penalties'
        ordering = ['-created_at']
        verbose_name = '전자제품 삭제 패널티'
        verbose_name_plural = '전자제품 삭제 패널티'

    def is_active(self):
        """패널티가 현재 활성 상태인지 확인"""
        from django.utils import timezone
        return timezone.now() < self.penalty_end


# 신고와 패널티는 중고폰과 전자제품이 통합해서 사용
# used_phones.models에 있는 것을 사용하도록 import에서 처리


