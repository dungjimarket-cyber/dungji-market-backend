"""
중고폰 직거래 모델
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from api.models import Region

User = get_user_model()

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
        ('A', 'A급 (미사용/리퍼)'),
        ('B', 'B급 (사용감 적음)'),
        ('C', 'C급 (사용감 있음)'),
    ]
    
    BATTERY_CHOICES = [
        ('excellent', '90% 이상'),
        ('good', '80~89%'),
        ('fair', '70~79%'),
        ('poor', '70% 미만'),
        ('unknown', '확인불가'),
    ]
    
    STATUS_CHOICES = [
        ('active', '판매중'),
        ('reserved', '예약중'),
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
    price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name='판매가격')
    min_offer_price = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name='최소제안가격')
    accept_offers = models.BooleanField(default=False, verbose_name='가격제안허용')
    
    # 상태 정보
    condition_grade = models.CharField(max_length=1, choices=CONDITION_CHOICES, verbose_name='상태등급')
    condition_description = models.TextField(null=True, blank=True, verbose_name='상태설명')
    battery_status = models.CharField(max_length=20, choices=BATTERY_CHOICES, default='unknown', verbose_name='배터리상태')
    
    # 구성품
    has_box = models.BooleanField(default=False, verbose_name='박스포함')
    has_charger = models.BooleanField(default=False, verbose_name='충전기포함')
    has_earphones = models.BooleanField(default=False, verbose_name='이어폰포함')
    
    # 상품 설명
    description = models.TextField(null=True, blank=True, verbose_name='상품설명')
    
    # 거래 위치
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='거래지역')
    meeting_place = models.CharField(max_length=200, null=True, blank=True, verbose_name='거래장소')
    
    # 상태 및 통계
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    view_count = models.IntegerField(default=0, verbose_name='조회수')
    favorite_count = models.IntegerField(default=0, verbose_name='찜개수')
    offer_count = models.IntegerField(default=0, verbose_name='제안수')
    
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
    thumbnail = models.ImageField(upload_to='used_phones/thumbs/%Y/%m/%d/', null=True, blank=True, verbose_name='썸네일')
    is_main = models.BooleanField(default=False, verbose_name='대표이미지')
    order = models.IntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'used_phone_images'
        ordering = ['order', 'id']
        verbose_name = '중고폰 이미지'
        verbose_name_plural = '중고폰 이미지'


class UsedPhoneFavorite(models.Model):
    """중고폰 찜"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_favorites')
    phone = models.ForeignKey(UsedPhone, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'used_phone_favorites'
        unique_together = ['user', 'phone']
        verbose_name = '중고폰 찜'
        verbose_name_plural = '중고폰 찜'


class UsedPhoneOffer(models.Model):
    """중고폰 가격 제안"""
    
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('accepted', '수락'),
        ('rejected', '거절'),
        ('cancelled', '취소'),
    ]
    
    phone = models.ForeignKey(UsedPhone, on_delete=models.CASCADE, related_name='offers')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_offers')
    amount = models.IntegerField(validators=[MinValueValidator(0)], verbose_name='제안금액')
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
