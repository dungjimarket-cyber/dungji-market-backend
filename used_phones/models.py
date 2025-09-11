"""
Used Phones Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
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
        ('excellent', '90% 이상'),
        ('good', '80~89%'),
        ('fair', '70~79%'),
        ('poor', '70% 미만'),
        ('unknown', '확인불가'),
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
    price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name='판매가격')
    min_offer_price = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name='최소제안가격')
    accept_offers = models.BooleanField(default=False, verbose_name='가격제안허용')
    
    # 상태 정보
    condition_grade = models.CharField(max_length=1, choices=CONDITION_CHOICES, verbose_name='상태등급')
    condition_description = models.TextField(null=True, blank=True, verbose_name='상태설명')
    battery_status = models.CharField(max_length=20, choices=BATTERY_CHOICES, default='unknown', verbose_name='배터리상태')
    
    # 구성품
    body_only = models.BooleanField(default=False, verbose_name='본체만')
    has_box = models.BooleanField(default=False, verbose_name='박스포함')
    has_charger = models.BooleanField(default=False, verbose_name='충전기포함')
    has_earphones = models.BooleanField(default=False, verbose_name='이어폰포함')
    
    # 상품 설명
    description = models.TextField(null=True, blank=True, verbose_name='상품설명')
    
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
    amount = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9900000)], verbose_name='제안금액')  # 최대 990만원
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


class UsedPhoneDeletePenalty(models.Model):
    """중고폰 삭제 패널티"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='used_phone_penalties')
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
