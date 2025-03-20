from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Case, When, F
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', '구매자'),
        ('seller', '판매자'),
        ('admin', '관리자'),
    )
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
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'phone_number'],
                name='unique_user_identity'
            )
        ]

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_service = models.BooleanField(default=False)  # 서비스 구분 필드 추가

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    TYPE_CHOICES = (
        ('device', '기기'),
        ('service', '통신/서비스'),
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)  # Add description field
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    product_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    base_price = models.PositiveIntegerField()  # 시장가격
    image_url = models.URLField()
    is_available = models.BooleanField(default=True)

class GroupBuy(models.Model):
    STATUS_CHOICES = (
        ('recruiting', '모집중'),
        ('bidding', '입찰진행중'),
        ('voting', '최종선택중'),
        ('seller_confirmation', '판매자확정대기'),
        ('completed', '완료'),
        ('cancelled', '취소됨'),
    )
    
    title = models.CharField(max_length=255)  # Required field
    description = models.TextField(blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True)  # Temporarily allow null
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='created_groupbuys')  # Temporarily allow null
    participants = models.ManyToManyField(User, through='Participation', related_name='joined_groupbuys')
    min_participants = models.PositiveSmallIntegerField(default=2)
    max_participants = models.PositiveSmallIntegerField(default=5)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField()  # 종료 시간 명시적 관리
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recruiting')
    current_participants = models.PositiveIntegerField(default=0)
    voting_end = models.DateTimeField(null=True, blank=True)
    target_price = models.PositiveIntegerField(null=True, blank=True)  # 목표 가격

    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import timedelta

        if self.end_time - self.start_time < timedelta(hours=24):
            raise ValidationError('공구 기간은 최소 24시간 이상이어야 합니다')
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_leader = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

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
    
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, null=True)  # Temporarily allow null
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True)  # Temporarily allow null
    bid_type = models.CharField(max_length=10, choices=BID_TYPE, default='price')
    amount = models.PositiveIntegerField(default=0)
    contract_period = models.PositiveSmallIntegerField(null=True, blank=True)  # 약정기간(월)
    created_at = models.DateTimeField(auto_now_add=True)
    is_selected = models.BooleanField(default=False)  # 최종선택여부
    
    @property
    def masked_amount(self):
        if self.bid_type == 'price':
            return f"{str(self.amount)[0]}*****"
        return str(self.amount)

    class Meta:
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
    
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE)
    choice = models.CharField(max_length=10, choices=VOTE_CHOICE)
    voted_at = models.DateTimeField(auto_now_add=True)

class Penalty(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    penalty_type = models.CharField(max_length=20)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    count = models.PositiveSmallIntegerField(default=1)

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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'penalty_type'],
                name='unique_penalty'
            )
        ]
    
class Badge(models.Model):
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
        return f"{self.user.username} - {self.message[:50]}"

@receiver(post_save, sender=GroupBuy)
def handle_status_change(sender, instance, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields is None or 'status' in update_fields:
        instance.notify_status_change()