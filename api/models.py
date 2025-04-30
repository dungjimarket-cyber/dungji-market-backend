from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Case, When, F
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', '구매자'),
        ('seller', '판매자'),
        ('admin', '관리자'),
    )
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    SNS_TYPE_CHOICES = (
        ('google', 'Google'),
        ('kakao', 'Kakao'),
        ('email', 'Email'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_image = models.URLField(blank=True)  # 외부 스토리지 사용 가정
    business_reg_number = models.CharField(max_length=20, blank=True, null=True)
    is_business_verified = models.BooleanField(default=False)
    penalty_expiry = models.DateTimeField(null=True, blank=True)  # 새로 추가
    penalty_count = models.PositiveIntegerField(default=0)
    current_penalty_level = models.PositiveSmallIntegerField(default=0)
    sns_type = models.CharField(max_length=10, choices=SNS_TYPE_CHOICES, default='email')
    sns_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    # Fix reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자 관리'
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'phone_number'],
                name='unique_user_identity'
            )
        ]

class Category(models.Model):
    DETAIL_TYPE_CHOICES = (
        ('none', '기본'),
        ('telecom', '통신'),
        ('electronics', '가전'),
        ('rental', '렌탈'),
        ('subscription', '구독'),
    )
    
    name = models.CharField(max_length=255, verbose_name='카테고리명')
    slug = models.SlugField(unique=True, null=True, verbose_name='슬러그')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='상위 카테고리')
    is_service = models.BooleanField(default=False, verbose_name='서비스 여부')  # 서비스 구분 필드 추가
    detail_type = models.CharField(max_length=20, choices=DETAIL_TYPE_CHOICES, default='none', verbose_name='상세 정보 유형')
    required_fields = models.JSONField(default=dict, blank=True, verbose_name='필수 필드')
    
    def __str__(self):
        parent_name = f" ({self.parent.name})" if self.parent else ""
        return f"{self.name}{parent_name}"
    
    class Meta:
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리 관리'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    TYPE_CHOICES = (
        ('device', '기기'),
        ('service', '통신/서비스'),
    )
    
    def __str__(self):
        return f"{self.name} ({self.get_product_type_display()})"
    CARRIER_CHOICES = (
        ('SKT', 'SK텔레콤'),
        ('KT', 'KT'),
        ('LGU', 'LG U+'),
        ('MVNO', '알뜰폰'),
    )
    REGISTRATION_TYPE_CHOICES = (
        ('MNP', '번호이동'),
        ('NEW', '신규가입'),
        ('CHANGE', '기기변경'),
    )
    name = models.CharField(max_length=255, verbose_name='상품명')
    slug = models.SlugField(unique=True, verbose_name='슬러그')
    description = models.TextField(blank=True, verbose_name='상품 설명')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='카테고리')
    category_name = models.CharField(max_length=100, blank=True, verbose_name='카테고리명')
    product_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='상품 유형')
    base_price = models.PositiveIntegerField(verbose_name='기본 가격')
    image_url = models.URLField(verbose_name='이미지 URL')
    is_available = models.BooleanField(default=True, verbose_name='판매 가능 여부')
    release_date = models.DateField(blank=True, null=True, verbose_name='출시일')
    attributes = models.JSONField(default=dict, blank=True, verbose_name='상품 특성')
    
    class Meta:
        verbose_name = '상품'
        verbose_name_plural = '상품 관리'
    
    def get_detail(self):
        """카테고리 유형에 따라 적절한 상세 정보 모델 반환"""
        if not self.category:
            return None
            
        detail_type = self.category.detail_type
        
        if detail_type == 'telecom' and hasattr(self, 'telecom_detail'):
            return self.telecom_detail
        elif detail_type == 'electronics' and hasattr(self, 'electronics_detail'):
            return self.electronics_detail
        elif detail_type == 'rental' and hasattr(self, 'rental_detail'):
            return self.rental_detail
        elif detail_type == 'subscription' and hasattr(self, 'subscription_detail'):
            return self.subscription_detail
        elif detail_type == 'none' and hasattr(self, 'standard_detail'):
            return self.standard_detail
        return None
    
    def save(self, *args, **kwargs):
        # 카테고리 이름 자동 저장
        if self.category and not self.category_name:
            self.category_name = self.category.name
        super().save(*args, **kwargs)

# 통신 상품 특화 정보 (휴대폰, 인터넷 등)
class TelecomProductDetail(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='telecom_detail', verbose_name='상품')
    carrier = models.CharField(max_length=10, choices=Product.CARRIER_CHOICES, verbose_name='통신사')
    registration_type = models.CharField(max_length=10, choices=Product.REGISTRATION_TYPE_CHOICES, verbose_name='가입 유형')
    plan_info = models.CharField(max_length=255, verbose_name='요금제 정보')
    contract_info = models.CharField(max_length=255, verbose_name='계약 정보')
    total_support_amount = models.PositiveIntegerField(verbose_name='총 지원금')
    
    class Meta:
        verbose_name = '통신 상품 상세'
        verbose_name_plural = '통신 상품 상세 관리'

# 가전 제품 특화 정보
class ElectronicsProductDetail(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='electronics_detail', verbose_name='상품')
    manufacturer = models.CharField(max_length=100, verbose_name='제조사')
    warranty_period = models.PositiveSmallIntegerField(verbose_name='보증 기간(개월)')
    power_consumption = models.CharField(max_length=50, blank=True, verbose_name='소비 전력')
    dimensions = models.CharField(max_length=100, blank=True, verbose_name='제품 크기')
    
    class Meta:
        verbose_name = '가전 제품 상세'
        verbose_name_plural = '가전 제품 상세 관리'

# 렌탈 상품 특화 정보
class RentalProductDetail(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='rental_detail', verbose_name='상품')
    rental_period_options = models.JSONField(verbose_name='렌탈 기간 옵션')
    maintenance_info = models.TextField(blank=True, verbose_name='유지보수 정보')
    deposit_amount = models.PositiveIntegerField(default=0, verbose_name='보증금')
    monthly_fee = models.PositiveIntegerField(verbose_name='월 이용료')
    
    class Meta:
        verbose_name = '렌탈 상품 상세'
        verbose_name_plural = '렌탈 상품 상세 관리'

# 구독 상품 특화 정보
class SubscriptionProductDetail(models.Model):
    BILLING_CYCLE_CHOICES = (
        ('monthly', '월간'),
        ('quarterly', '분기'),
        ('yearly', '연간'),
    )
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='subscription_detail', verbose_name='상품')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, verbose_name='결제 주기')
    auto_renewal = models.BooleanField(default=True, verbose_name='자동 갱신')
    free_trial_days = models.PositiveSmallIntegerField(default=0, verbose_name='무료 체험 기간(일)')
    
    class Meta:
        verbose_name = '구독 상품 상세'
        verbose_name_plural = '구독 상품 상세 관리'

# 일반 상품 특화 정보 (일반 판매 상품)
class StandardProductDetail(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='standard_detail', verbose_name='상품')
    brand = models.CharField(max_length=100, blank=True, verbose_name='브랜드')
    origin = models.CharField(max_length=100, blank=True, verbose_name='원산지')
    shipping_fee = models.PositiveIntegerField(default=0, verbose_name='배송비')
    shipping_info = models.CharField(max_length=255, blank=True, verbose_name='배송 정보')
    
    class Meta:
        verbose_name = '일반 상품 상세'
        verbose_name_plural = '일반 상품 상세 관리'

# 동적 필드 처리를 위한 추가 모델
class ProductCustomField(models.Model):
    """카테고리별 커스텀 필드 정의"""
    FIELD_TYPE_CHOICES = (
        ('text', '텍스트'),
        ('number', '숫자'),
        ('boolean', '예/아니오'),
        ('select', '선택'),
        ('date', '날짜'),
    )
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='custom_fields', verbose_name='카테고리')
    field_name = models.CharField(max_length=100, verbose_name='필드명')
    field_label = models.CharField(max_length=100, verbose_name='표시명')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, verbose_name='필드 타입')
    is_required = models.BooleanField(default=False, verbose_name='필수 여부')
    options = models.JSONField(default=list, blank=True, verbose_name='선택 옵션')
    
    class Meta:
        verbose_name = '상품 커스텀 필드'
        verbose_name_plural = '상품 커스텀 필드 관리'
        unique_together = ('category', 'field_name')

class ProductCustomValue(models.Model):
    """상품별 커스텀 필드 값"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='custom_values', verbose_name='상품')
    field = models.ForeignKey(ProductCustomField, on_delete=models.CASCADE, verbose_name='필드')
    text_value = models.TextField(blank=True, null=True, verbose_name='텍스트 값')
    number_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='숫자 값')
    boolean_value = models.BooleanField(blank=True, null=True, verbose_name='불리언 값')
    date_value = models.DateField(blank=True, null=True, verbose_name='날짜 값')
    
    class Meta:
        verbose_name = '상품 커스텀 값'
        verbose_name_plural = '상품 커스텀 값 관리'
        unique_together = ('product', 'field')

class GroupBuy(models.Model):
    STATUS_CHOICES = (
        ('recruiting', '모집중'),
        ('bidding', '입찰진행중'),
        ('voting', '최종선택중'),
        ('seller_confirmation', '판매자확정대기'),
        ('completed', '완료'),
        ('cancelled', '취소됨'),
    )
    
    REGION_TYPE_CHOICES = (
        ('local', '지역'),
        ('nationwide', '전국(비대면)'),
    )
    
    title = models.CharField(max_length=255, verbose_name='공구 제목')  # Required field
    description = models.TextField(blank=True, verbose_name='공구 설명')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, verbose_name='상품')  # Temporarily allow null
    product_name = models.CharField(max_length=255, blank=True, verbose_name='상품명 백업')  # 상품 이름 백업
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='created_groupbuys', verbose_name='생성자')  # Temporarily allow null
    participants = models.ManyToManyField(User, through='Participation', related_name='joined_groupbuys', verbose_name='참여자')
    min_participants = models.PositiveSmallIntegerField(default=1, verbose_name='최소 참여자 수')
    max_participants = models.PositiveSmallIntegerField(default=100, verbose_name='최대 참여자 수')
    start_time = models.DateTimeField(default=now, verbose_name='시작 시간')  # 시작일을 현재 시간으로 기본값 설정
    end_time = models.DateTimeField(verbose_name='종료 시간')  # 종료 시간 명시적 관리
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recruiting', verbose_name='상태')
    current_participants = models.PositiveIntegerField(default=0, verbose_name='현재 참여자 수')
    voting_end = models.DateTimeField(null=True, blank=True, verbose_name='투표 종료 시간')
    target_price = models.PositiveIntegerField(null=True, blank=True, verbose_name='목표 가격')  # 목표 가격
    region_type = models.CharField(max_length=20, choices=REGION_TYPE_CHOICES, default='local', verbose_name='지역 유형')
    product_details = models.JSONField(null=True, blank=True, verbose_name='상품 세부 정보')
    
    def save(self, *args, **kwargs):
        # 상품 이름 백업
        if self.product and not self.product_name:
            self.product_name = self.product.name
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.title} - {self.product_name if self.product_name else (self.product.name if self.product else '상품 없음')}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import timedelta

        if self.end_time - self.start_time > timedelta(hours=48):
            raise ValidationError('공구 기간은 최대 48시간까지 설정 가능합니다')

    def advance_status(self):
        now = timezone.now()
        if self.status == 'recruiting' and now >= self.start_time:
            self.status = 'bidding'
            self.save()
        elif self.status == 'bidding' and now >= self.end_time:
            self.status = 'voting'
            from datetime import timedelta
            self.voting_end = now + timedelta(hours=12)
            self.save()

    def handle_voting_timeout(self):
        if timezone.now() > self.voting_end:
            confirmed = self.vote_set.filter(choice='confirm').count()
            if confirmed >= 1:
                self.status = 'seller_confirmation'
            else:
                self.status = 'cancelled'
            self.save()

    def check_auto_transitions(self):
        now = timezone.now()
        if self.status == 'voting' and now > self.voting_end:
            self.handle_voting_timeout()
        elif self.status == 'seller_confirmation' and now > self.voting_end + timezone.timedelta(hours=24):
            self.status = 'completed'
            self.save()

    def notify_status_change(self):
        for participant in self.participants.all():
            Notification.objects.create(
                user=participant,
                groupbuy=self,
                message=f"공구 {self.product.name}의 상태가 {self.status}로 변경되었습니다."
            )

    class Meta:
        verbose_name = '공동구매'
        verbose_name_plural = '공동구매 관리'
        indexes = [
            models.Index(fields=['status', 'end_time']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'creator'],
                name='unique_groupbuy_per_product'
            )
        ]

class Participation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, verbose_name='공동구매')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='참여 시간')
    is_leader = models.BooleanField(default=False, verbose_name='리더 여부')
    is_locked = models.BooleanField(default=False, verbose_name='잠금 여부')
    
    def __str__(self):
        leader_mark = "[리더]" if self.is_leader else ""
        return f"{self.user.username} - {self.groupbuy.title} {leader_mark}"

    def save(self, *args, **kwargs):
        if Participation.objects.filter(
            user=self.user,
            groupbuy__product=self.groupbuy.product,
            groupbuy__status__in=['recruiting', 'bidding']
        ).exists():
            raise ValidationError("이미 동일한 상품의 공구에 참여중입니다.")
        super().save(*args, **kwargs)

    def can_leave(self):
        return not self.is_locked and self.groupbuy.status == 'recruiting'

    class Meta:
        verbose_name = '참여 정보'
        verbose_name_plural = '참여 정보 관리'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'groupbuy'],
                name='unique_participation'
            )
        ]

class Bid(models.Model):
    BID_TYPE = (
        ('price', '가격입찰'),
        ('support', '지원금입찰'),
    )
    
    def __str__(self):
        selected = "[선택됨]" if self.is_selected else ""
        return f"{self.seller.username} - {self.groupbuy.title} ({self.get_bid_type_display()}: {self.amount}원) {selected}"
    
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, null=True, verbose_name='공동구매')  # Temporarily allow null
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, verbose_name='판매자')  # Temporarily allow null
    bid_type = models.CharField(max_length=10, choices=BID_TYPE, default='price', verbose_name='입찰 유형')
    amount = models.PositiveIntegerField(default=0, verbose_name='입찰 금액')
    contract_period = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='약정 기간(월)')  # 약정기간(월)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    is_selected = models.BooleanField(default=False, verbose_name='선택 여부')  # 최종선택여부
    
    @property
    def masked_amount(self):
        if self.bid_type == 'price':
            return f"{str(self.amount)[0]}*****"
        return str(self.amount)

    class Meta:
        verbose_name = '입찰'
        verbose_name_plural = '입찰 관리'
        ordering = [
            Case(
                When(bid_type='price', then='amount'),
                When(bid_type='support', then=-F('amount')),
                output_field=models.IntegerField()
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['groupbuy', 'seller'],
                name='unique_bid_per_seller'
            )
        ]

class Vote(models.Model):
    VOTE_CHOICE = (
        ('confirm', '확정'),
        ('cancel', '포기'),
    )
    
    def __str__(self):
        return f"{self.participation.user.username} - {self.get_choice_display()} ({self.participation.groupbuy.title})"
    
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE, verbose_name='참여 정보')
    choice = models.CharField(max_length=10, choices=VOTE_CHOICE, verbose_name='선택')
    voted_at = models.DateTimeField(auto_now_add=True, verbose_name='투표 시간')
    
    class Meta:
        verbose_name = '투표'
        verbose_name_plural = '투표 관리'

class Penalty(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    reason = models.TextField(verbose_name='사유')
    penalty_type = models.CharField(max_length=20, verbose_name='페널티 유형')
    start_date = models.DateTimeField(default=timezone.now, verbose_name='시작일')
    end_date = models.DateTimeField(verbose_name='종료일')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    count = models.PositiveSmallIntegerField(default=1, verbose_name='누적 횟수')
    
    def __str__(self):
        active = "[활성]" if self.is_active else "[비활성]"
        return f"{self.user.username} - {self.penalty_type} ({self.count}회) {active}"

    def get_penalty_duration(self):
        duration_map = {
            1: 48,    # 48 hours
            2: 72,    # 72 hours
            3: 168,   # 1 week
            4: 720    # 1 month
        }
        return timezone.timedelta(hours=duration_map.get(self.count, 48))

    def save(self, *args, **kwargs):
        if not self.pk:
            self.end_date = timezone.now() + self.get_penalty_duration()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = '페널티'
        verbose_name_plural = '페널티 관리'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'penalty_type'],
                name='unique_penalty'
            )
        ]
    
class Badge(models.Model):
    def __str__(self):
        return f"{self.user.username} - Level {self.level}"
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    level = models.CharField(max_length=50)  # 예: 초보참새, 우수한참새
    icon = models.ImageField(upload_to='badges/')

    def __str__(self):
        return f"{self.user.username} - {self.level}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.message[:50]}..."

class Wishlist(models.Model):
    """찜하기 기능을 위한 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists', verbose_name='사용자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, related_name='wishlists', verbose_name='공동구매')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    
    class Meta:
        verbose_name = '찜하기'
        verbose_name_plural = '찜하기 관리'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'groupbuy'],
                name='unique_wishlist'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username}의 찜: {self.groupbuy.title}"


class Review(models.Model):
    """리뷰 및 별점 기능을 위한 모델"""
    RATING_CHOICES = (
        (1, '1점'),
        (2, '2점'),
        (3, '3점'),
        (4, '4점'),
        (5, '5점'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name='작성자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, related_name='reviews', verbose_name='공동구매')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name='별점')
    content = models.TextField(verbose_name='리뷰 내용')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    is_purchased = models.BooleanField(default=False, verbose_name='구매 확인')
    
    class Meta:
        verbose_name = '리뷰'
        verbose_name_plural = '리뷰 관리'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'groupbuy'],
                name='unique_review_per_user_groupbuy'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username}의 리뷰: {self.groupbuy.title} ({self.rating}점)"

@receiver(post_save, sender=GroupBuy)
def handle_status_change(sender, instance, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields is None or 'status' in update_fields:
        instance.notify_status_change()