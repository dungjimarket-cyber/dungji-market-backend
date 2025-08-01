from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Case, When, F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.conf import settings
import logging

# 지역 정보 모델 import
from .models_region import Region

logger = logging.getLogger(__name__)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('buyer', '구매자'),
        ('seller', '판매자'),
        ('admin', '관리자'),
    )
    
    def __str__(self):
        return f"{self.nickname} ({self.get_role_display()})"
    SNS_TYPE_CHOICES = (
        ('google', 'Google'),
        ('kakao', 'Kakao'),
        ('email', 'Email'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    nickname = models.CharField(max_length=100, default='', verbose_name='닉네임', help_text='사용자가 표시될 이름')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_image = models.URLField(blank=True)  # 외부 스토리지 사용 가정
    business_reg_number = models.CharField(max_length=20, blank=True, null=True)
    is_business_verified = models.BooleanField(default=False)
    penalty_expiry = models.DateTimeField(null=True, blank=True)  # 새로 추가
    penalty_count = models.PositiveIntegerField(default=0)
    current_penalty_level = models.PositiveSmallIntegerField(default=0)
    sns_type = models.CharField(max_length=10, choices=SNS_TYPE_CHOICES, default='email')
    sns_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # 활동 지역 정보 (시/군/구 단위) - 구매자/판매자 공통
    address_region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name='활동 지역')
    address_detail = models.CharField(max_length=255, blank=True, null=True, verbose_name='상세 주소')
    
    # 판매자 추가 정보
    business_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='사업자등록번호')
    is_remote_sales = models.BooleanField(default=False, verbose_name='비대면 판매 가능')
    
    # 비대면 판매 관련 필드
    is_remote_sales_enabled = models.BooleanField(default=False, verbose_name='비대면 판매 가능 여부')
    remote_sales_verified = models.BooleanField(default=False, verbose_name='비대면 판매 인증 완료')
    remote_sales_verification_date = models.DateTimeField(null=True, blank=True, verbose_name='비대면 인증일')
    remote_sales_expiry_date = models.DateTimeField(null=True, blank=True, verbose_name='비대면 인증 만료일')
    business_license_image = models.URLField(blank=True, null=True, verbose_name='사업자등록증 이미지')
    delivery_history_image = models.URLField(blank=True, null=True, verbose_name='택배 송장 이미지')
    
    # 휴대폰 인증 시 수집한 개인정보
    birth_date = models.DateField(null=True, blank=True, verbose_name='생년월일')
    gender = models.CharField(max_length=1, choices=[('M', '남성'), ('F', '여성')], null=True, blank=True, verbose_name='성별')
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
    # 이미지 URL 필드를 ImageField로 변경하고 기존 URL도 지원
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='상품 이미지')
    image_url = models.URLField(blank=True, verbose_name='이미지 URL')
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
        
        # 디버깅을 위한 로그
        # 이미지가 업로드되었는지 확인
        if self.image:
            logger.info(f"Product save: 이미지 필드 있음 - {self.image}")
            logger.info(f"Product save: 이미지 필드 타입 - {type(self.image)}")
            logger.info(f"Product save: 이미지 name - {getattr(self.image, 'name', 'No name')}")
            
            # Django의 ImageField는 자동으로 S3에 업로드됨
            logger.info(f"Product save: USE_S3 = {getattr(settings, 'USE_S3', False)}")
            logger.info(f"Product save: DEFAULT_FILE_STORAGE = {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
            logger.info(f"Product save: AWS_STORAGE_BUCKET_NAME = {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')}")
        
        super().save(*args, **kwargs)
        
        # 저장 후 이미지 URL 확인
        if self.image:
            logger.info(f"Product save 후: 이미지 URL - {self.image.url if self.image else 'None'}")

# 통신 상품 특화 정보 (휴대폰, 인터넷 등)
class TelecomProductDetail(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='telecom_detail', verbose_name='상품')
    carrier = models.CharField(max_length=10, choices=Product.CARRIER_CHOICES, verbose_name='통신사')
    registration_type = models.CharField(max_length=10, choices=Product.REGISTRATION_TYPE_CHOICES, verbose_name='가입 유형')
    plan_info = models.CharField(max_length=255, verbose_name='요금제 정보')
    contract_info = models.CharField(max_length=255, verbose_name='계약 정보')
    # total_support_amount 필드 제거 - 지원금은 상품에 고정된 값이 아니라 입찰 시 사용자가 제안하는 금액
    
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

class GroupBuyRegion(models.Model):
    """
    공구와 지역 간의 다대다 관계를 관리하는 모델
    한 공구는 최대 3개까지의 지역을 가질 수 있음
    """
    groupbuy = models.ForeignKey('GroupBuy', on_delete=models.CASCADE, related_name='regions', verbose_name='공구')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='groupbuy_regions', verbose_name='지역')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    
    class Meta:
        verbose_name = '공구 지역'
        verbose_name_plural = '공구 지역 관리'
        unique_together = ('groupbuy', 'region')
        
    def __str__(self):
        return f"{self.groupbuy.title} - {self.region.name}"


class GroupBuy(models.Model):
    STATUS_CHOICES = (
        ('recruiting', '모집중'),
        ('bidding', '입찰진행중'),
        ('voting', '투표중'),
        ('final_selection', '최종선택중'),
        ('seller_confirmation', '판매자확정대기'),
        ('completed', '완료'),
        ('cancelled', '취소됨'),
    )
    
    REGION_TYPE_CHOICES = (
        ('local', '지역'),
        ('nationwide', '전국(비대면)'),
    )
    
    # 기본 공구 정보
    title = models.CharField(max_length=255, verbose_name='공구 제목')  # Required field
    description = models.TextField(blank=True, verbose_name='공구 설명')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, verbose_name='상품')  # Temporarily allow null
    product_name = models.CharField(max_length=255, blank=True, verbose_name='상품명 백업')  # 상품 이름 백업
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='created_groupbuys', verbose_name='생성자')  # Temporarily allow null
    creator_nickname = models.CharField(max_length=150, blank=True, null=True, verbose_name='생성자 닉네임')  # 생성자 닉네임 저장
    participants = models.ManyToManyField(User, through='Participation', related_name='joined_groupbuys', verbose_name='참여자')
    min_participants = models.PositiveSmallIntegerField(default=1, verbose_name='최소 참여자 수')
    max_participants = models.PositiveSmallIntegerField(default=100, verbose_name='최대 참여자 수')
    start_time = models.DateTimeField(default=now, verbose_name='시작 시간')  # 시작일을 현재 시간으로 기본값 설정
    end_time = models.DateTimeField(verbose_name='종료 시간')  # 종료 시간 명시적 관리
    voting_end = models.DateTimeField(null=True, blank=True, verbose_name='투표 종료 시간')  # 공구 마감 후 12시간
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recruiting', verbose_name='상태')
    current_participants = models.PositiveIntegerField(default=0, verbose_name='현재 참여자 수')
    target_price = models.PositiveIntegerField(null=True, blank=True, verbose_name='목표 가격')  # 목표 가격
    region_type = models.CharField(max_length=20, choices=REGION_TYPE_CHOICES, default='local', verbose_name='지역 유형')
    # 기존 단일 지역 필드는 유지 (하위 호환성)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='groupbuys', verbose_name='지역')
    region_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='지역명 백업')  # 지역명 백업
    
    # 통신 관련 정보는 GroupBuyTelecomDetail 모델로 분리
    
    # 기타 카테고리별 세부 정보는 여전히 JSON으로 저장
    product_details = models.JSONField(null=True, blank=True, verbose_name='기타 세부 정보')
    
    def save(self, *args, **kwargs):
        # 상품 이름 백업
        if self.product and not self.product_name:
            self.product_name = self.product.name
            
        # 생성자 닉네임 자동 저장
        if self.creator:
            # nickname 필드가 있으면 사용, 없으면 username 사용
            if hasattr(self.creator, 'nickname') and self.creator.nickname:
                self.creator_nickname = self.creator.nickname
            else:
                self.creator_nickname = self.creator.username
            
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
            self.save()
        elif self.status == 'voting':
            # 투표 완료 후 final_selection 상태로 전환
            selected_bid = self.bid_set.filter(is_selected=True).first()
            if selected_bid:
                self.status = 'final_selection'
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

    def handle_final_selection_timeout(self):
        """최종선택 시간 초과 처리"""
        if self.status == 'final_selection' and self.voting_end and timezone.now() > self.voting_end:
            # 최종선택을 완료한 참여자들만 completed 상태로 진행
            confirmed_participations = self.participation_set.filter(final_decision='confirmed')
            selected_bid = self.bid_set.filter(is_selected=True, final_decision='confirmed').first()
            
            if confirmed_participations.exists() and selected_bid:
                self.status = 'completed'
            else:
                self.status = 'cancelled'
            self.save()

    def check_auto_transitions(self):
        now = timezone.now()
        if self.status == 'voting' and now > self.voting_end:
            self.handle_voting_timeout()
        elif self.status == 'final_selection' and self.voting_end and now > self.voting_end:
            self.handle_final_selection_timeout()
        elif self.status == 'seller_confirmation' and now > self.voting_end + timezone.timedelta(hours=24):
            self.status = 'completed'
            self.save()

    def notify_status_change(self):
        # STATUS_CHOICES에서 현재 상태의 한글 표시 가져오기
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        
        for participant in self.participants.all():
            Notification.objects.create(
                user=participant,
                groupbuy=self,
                message=f"공구 {self.product.name}의 상태가 {status_display}로 변경되었습니다."
            )
    
    def start_consent_process(self, selected_bid, consent_hours=24):
        """선택된 입찰에 대한 참여자 동의 프로세스 시작"""
        from datetime import timedelta
        
        consent_deadline = timezone.now() + timedelta(hours=consent_hours)
        participations = Participation.objects.filter(groupbuy=self)
        
        for participation in participations:
            ParticipantConsent.objects.create(
                participation=participation,
                bid=selected_bid,
                consent_deadline=consent_deadline
            )
            
            # 동의 요청 알림 발송
            Notification.objects.create(
                user=participation.user,
                groupbuy=self,
                message=f"공구 '{self.title}'의 최종 가격이 확정되었습니다. {consent_hours}시간 내에 동의 여부를 선택해주세요."
            )
    
    def check_all_consents(self):
        """모든 참여자의 동의 상태 확인"""
        participations = Participation.objects.filter(groupbuy=self)
        consents = ParticipantConsent.objects.filter(
            participation__in=participations,
            bid__groupbuy=self
        )
        
        total = consents.count()
        agreed = consents.filter(status='agreed').count()
        disagreed = consents.filter(status='disagreed').count()
        pending = consents.filter(status='pending').count()
        expired = consents.filter(status='expired').count()
        
        return {
            'total': total,
            'agreed': agreed,
            'disagreed': disagreed,
            'pending': pending,
            'expired': expired,
            'all_agreed': total > 0 and agreed == total,
            'can_proceed': total > 0 and agreed >= (total * 0.8)  # 80% 이상 동의 시 진행 가능
        }

    class Meta:
        verbose_name = '공동구매'
        verbose_name_plural = '공동구매 관리'
        indexes = [
            models.Index(fields=['status', 'end_time']),
        ]

class GroupBuyTelecomDetail(models.Model):
    """
    공구의 통신 관련 세부 정보를 저장하는 모델
    GroupBuy와 1:1 관계를 가짐
    """
    # 통신사 선택 옵션
    TELECOM_CARRIER_CHOICES = (
        ('SKT', 'SKT'),
        ('KT', 'KT'),
        ('LGU', 'LG U+'),
        ('MVNO', '알뜰폰'),
    )
    
    # 가입유형 선택 옵션
    SUBSCRIPTION_TYPE_CHOICES = (
        ('new', '신규가입'),
        ('transfer', '번호이동'),
        ('change', '기기변경'),
    )
    
    # 요금제 선택 옵션 - 만원대 표시로 변경
    PLAN_INFO_CHOICES = (
        ('3만원대', '3만원대'),
        ('5만원대', '5만원대'),
        ('7만원대', '7만원대'),
        ('9만원대', '9만원대'),
        ('10만원대', '10만원대'),
    )
    
    groupbuy = models.OneToOneField(GroupBuy, on_delete=models.CASCADE, related_name='telecom_detail', verbose_name='공구')
    telecom_carrier = models.CharField(max_length=20, choices=TELECOM_CARRIER_CHOICES, verbose_name='통신사')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPE_CHOICES, verbose_name='가입유형')
    plan_info = models.CharField(max_length=20, choices=PLAN_INFO_CHOICES, verbose_name='요금제')
    contract_period = models.CharField(max_length=20, default='24개월', verbose_name='약정기간')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    def __str__(self):
        return f"{self.groupbuy.title} - {self.telecom_carrier} {self.subscription_type} {self.plan_info}"
    
    class Meta:
        verbose_name = '공구 통신 세부정보'
        verbose_name_plural = '공구 통신 세부정보 관리'


class BidToken(models.Model):
    """판매자의 입찰권 관리를 위한 모델"""
    TOKEN_TYPE_CHOICES = (
        ('single', '입찰권 단품'),
        ('unlimited', '무제한 구독권'),
    )
    
    STATUS_CHOICES = (
        ('active', '활성'),
        ('used', '사용됨'),
        ('expired', '만료됨'),
    )
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bid_tokens', verbose_name='판매자')
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES, default='standard', verbose_name='입찰권 유형')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='만료일')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='상태')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='사용일')
    used_for = models.ForeignKey('Bid', on_delete=models.SET_NULL, null=True, blank=True, related_name='token_used', verbose_name='사용된 입찰')
    
    class Meta:
        verbose_name = '입찰권'
        verbose_name_plural = '입찰권 관리'
    
    def __str__(self):
        return f"{self.seller.username}의 {self.get_token_type_display()} ({self.get_status_display()})"
    
    def is_valid(self):
        """입찰권이 유효한지 확인"""
        # 상태가 활성이면서, 만료일이 없거나(None) 또는 만료일이 현재보다 더 나중인 경우
        return self.status == 'active' and (self.expires_at is None or self.expires_at > timezone.now())
    
    def use(self, bid):
        """입찰권 사용 처리"""
        if not self.is_valid():
            return False
        
        self.status = 'used'
        self.used_at = timezone.now()
        self.used_for = bid
        self.save()
        return True


class BidTokenPurchase(models.Model):
    """입찰권 구매 내역"""
    PAYMENT_STATUS_CHOICES = (
        ('pending', '결제 대기'),
        ('completed', '결제 완료'),
        ('cancelled', '취소됨'),
        ('refunded', '환불됨'),
    )
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='token_purchases', verbose_name='구매자')
    token_type = models.CharField(max_length=20, choices=BidToken.TOKEN_TYPE_CHOICES, verbose_name='입찰권 유형')
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name='수량')
    total_price = models.PositiveIntegerField(verbose_name='결제 금액')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='결제 상태')
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name='구매일')
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name='결제일')
    
    class Meta:
        verbose_name = '입찰권 구매 내역'
        verbose_name_plural = '입찰권 구매 내역 관리'
    
    def __str__(self):
        return f"{self.seller.username}의 {self.get_token_type_display()} {self.quantity}개 구매"


class Participation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, verbose_name='공동구매')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='참여 시간')
    is_leader = models.BooleanField(default=False, verbose_name='리더 여부')
    is_locked = models.BooleanField(default=False, verbose_name='잠금 여부')
    # 참여 당시의 닉네임 저장 (사용자가 닉네임을 변경해도 참여 당시 닉네임 보존)
    nickname = models.CharField(max_length=150, blank=True, null=True, verbose_name='참여 닉네임')
    
    # 최종선택 관련 필드
    final_decision = models.CharField(
        max_length=20,
        choices=(
            ('pending', '대기중'),
            ('confirmed', '구매확정'),
            ('cancelled', '구매포기'),
        ),
        default='pending',
        verbose_name='최종선택'
    )
    final_decision_at = models.DateTimeField(null=True, blank=True, verbose_name='최종선택 일시')
    
    def __str__(self):
        leader_mark = "[리더]" if self.is_leader else ""
        return f"{self.user.username} - {self.groupbuy.title} {leader_mark}"

    def save(self, *args, **kwargs):
        # 동일한 상품의 공구 중복 참여 방지
        if Participation.objects.filter(
            user=self.user,
            groupbuy__product=self.groupbuy.product,
            groupbuy__status__in=['recruiting', 'bidding']
        ).exists():
            raise ValidationError("이미 동일한 상품의 공구에 참여중입니다.")
            
        # 참여 닉네임 자동 저장 (새로 생성되는 것인 경우에만)
        if not self.pk and not self.nickname and self.user:
            self.nickname = self.user.username
            
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
    
    STATUS_CHOICES = (
        ('pending', '대기중'),
        ('selected', '확정'),
        ('rejected', '포기'),
        ('ineligible', '자격미달'),
    )
    
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, null=True, verbose_name='공동구매')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, verbose_name='판매자')
    bid_type = models.CharField(max_length=10, choices=BID_TYPE, default='price', verbose_name='입찰 유형')
    amount = models.PositiveIntegerField(default=0, verbose_name='입찰 금액')
    message = models.TextField(blank=True, verbose_name='입찰 메시지')
    contract_period = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='약정 기간(월)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시간')
    is_selected = models.BooleanField(default=False, verbose_name='선택 여부')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='상태')
    # 입찰권 관련 필드 추가
    bid_token = models.ForeignKey(BidToken, on_delete=models.SET_NULL, null=True, blank=True, related_name='bids', verbose_name='사용된 입찰권')
    
    # 최종선택 관련 필드
    final_decision = models.CharField(
        max_length=20,
        choices=(
            ('pending', '대기중'),
            ('confirmed', '판매확정'),
            ('cancelled', '판매포기'),
        ),
        default='pending',
        verbose_name='최종선택'
    )
    final_decision_at = models.DateTimeField(null=True, blank=True, verbose_name='최종선택 일시')
    
    @property
    def masked_amount(self):
        if self.bid_type == 'price':
            return f"{str(self.amount)[0]}*****"
        return str(self.amount)
    
    def check_seller_eligibility(self):
        """
        판매자가 해당 공구에 입찰 가능한지 확인
        """
        from django.core.exceptions import ValidationError
        
        # 판매자 역할 확인
        if self.seller.role != 'seller':
            raise ValidationError('판매자만 입찰이 가능합니다.')
        
        # 전국 공구인 경우 비대면 인증 확인
        if self.groupbuy.region_type == 'nationwide':
            if not self.seller.is_remote_sales_enabled or not self.seller.remote_sales_verified:
                raise ValidationError('전국 공구는 비대면 판매 인증을 완료한 판매회원만 입찰 가능합니다.')
            
            # 비대면 인증 만료일 확인
            if self.seller.remote_sales_expiry_date and self.seller.remote_sales_expiry_date < timezone.now():
                raise ValidationError('비대면 판매 인증이 만료되었습니다. 재인증이 필요합니다.')
        
        # 지역 공구인 경우 지역 일치 확인
        else:
            # 판매자 주소지 확인
            if not self.seller.address_region:
                raise ValidationError('판매자 주소지 정보가 없습니다.')
            
            # 공구 지역들과 판매자 주소지 비교
            seller_region_code = self.seller.address_region.code
            
            # 기존 단일 지역 필드 확인 (하위 호환성)
            if self.groupbuy.region and self.groupbuy.region.code[:5] == seller_region_code[:5]:
                return True
                
            # 새로운 다중 지역 필드 확인
            groupbuy_regions = self.groupbuy.regions.all()
            for gb_region in groupbuy_regions:
                # 시/군/구 레벨에서 비교 (코드 앞 5자리 비교)
                if gb_region.region.code[:5] == seller_region_code[:5]:
                    return True
                    
            raise ValidationError('해당 공구의 지역에 해당하는 판매회원만 입찰이 가능합니다.')
        
        return True

    def save(self, *args, **kwargs):
        # 입찰 자격 확인 (새로 생성되는 경우에만)
        # TODO: 결제 시스템 구현 후 아래 주석 해제
        # if not self.pk:
        #     try:
        #         self.check_seller_eligibility()
        #     except Exception as e:
        #         self.status = 'ineligible'
        #         # 예외 발생 시 일단 저장하고 상태만 변경
        #         super().save(*args, **kwargs)
        #         return
        
        # status 필드와 is_selected 필드 동기화
        if self.status == 'selected':
            self.is_selected = True
        else:
            self.is_selected = False
        super().save(*args, **kwargs)

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
    NOTIFICATION_TYPES = [
        ('reminder', '리마인더'),
        ('success', '성공/낙찰'),
        ('failure', '실패/취소'),
        ('info', '정보/상태변경'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES, 
        default='info'
    )
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


class Settlement(models.Model):
    """
    판매자의 정산 내역을 관리하는 모델
    """
    PAYMENT_STATUS_CHOICES = (
        ('pending', '처리중'),
        ('completed', '정산완료'),
        ('failed', '정산실패'),
    )
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='settlements', verbose_name='판매자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, related_name='settlements', verbose_name='공동구매')
    bid = models.OneToOneField(Bid, on_delete=models.SET_NULL, null=True, blank=True, related_name='settlement', verbose_name='입찰')
    total_amount = models.PositiveIntegerField(verbose_name='총 금액')
    fee_amount = models.PositiveIntegerField(verbose_name='수수료')
    net_amount = models.PositiveIntegerField(verbose_name='실 정산액')
    settlement_date = models.DateTimeField(verbose_name='정산일')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='정산 상태')
    receipt_url = models.URLField(null=True, blank=True, verbose_name='영수증 URL')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시간')
    
    def __str__(self):
        return f"{self.seller.username} - {self.groupbuy.title} ({self.net_amount}원)"
    
    class Meta:
        verbose_name = '정산 내역'
        verbose_name_plural = '정산 내역 관리'
        ordering = ['-settlement_date']


class ParticipantConsent(models.Model):
    """참여자 동의 상태를 추적하는 모델"""
    CONSENT_STATUS_CHOICES = (
        ('pending', '대기중'),
        ('agreed', '동의'),
        ('disagreed', '거부'),
        ('expired', '만료'),
    )
    
    participation = models.OneToOneField('Participation', on_delete=models.CASCADE, related_name='consent', verbose_name='참여')
    bid = models.ForeignKey('Bid', on_delete=models.CASCADE, related_name='consents', verbose_name='선택된 입찰')
    status = models.CharField(max_length=20, choices=CONSENT_STATUS_CHOICES, default='pending', verbose_name='동의 상태')
    agreed_at = models.DateTimeField(null=True, blank=True, verbose_name='동의 시간')
    disagreed_at = models.DateTimeField(null=True, blank=True, verbose_name='거부 시간')
    consent_deadline = models.DateTimeField(verbose_name='동의 마감 시간')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시간')
    
    class Meta:
        verbose_name = '참여자 동의'
        verbose_name_plural = '참여자 동의 관리'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.participation.user.username} - {self.participation.groupbuy.title} 동의: {self.get_status_display()}"
    
    def agree(self):
        """참여자가 동의함"""
        self.status = 'agreed'
        self.agreed_at = timezone.now()
        self.save()
    
    def disagree(self):
        """참여자가 거부함"""
        self.status = 'disagreed'
        self.disagreed_at = timezone.now()
        self.save()
    
    def check_expiry(self):
        """동의 기한 만료 확인"""
        if self.status == 'pending' and timezone.now() > self.consent_deadline:
            self.status = 'expired'
            self.save()
            return True
        return False


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

class NoShowReport(models.Model):
    """노쇼 신고 모델"""
    REPORT_STATUS_CHOICES = [
        ('pending', '검토중'),
        ('confirmed', '확인됨'),
        ('rejected', '반려됨'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='noshow_reports_made', verbose_name='신고자')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='noshow_reports_received', verbose_name='피신고자')
    groupbuy = models.ForeignKey(GroupBuy, on_delete=models.CASCADE, related_name='noshow_reports', verbose_name='공동구매')
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE, related_name='noshow_reports', verbose_name='참여 정보', null=True, blank=True)
    bid = models.ForeignKey('Bid', on_delete=models.CASCADE, related_name='noshow_reports', verbose_name='입찰 정보', null=True, blank=True)
    
    report_type = models.CharField(max_length=20, choices=[
        ('buyer_noshow', '구매자 노쇼'),
        ('seller_noshow', '판매자 노쇼'),
    ], verbose_name='신고 유형')
    
    content = models.TextField(verbose_name='신고 내용')
    evidence_image = models.ImageField(upload_to='noshow_reports/', null=True, blank=True, verbose_name='증빙 이미지')
    
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='pending', verbose_name='처리 상태')
    admin_comment = models.TextField(blank=True, verbose_name='관리자 코멘트')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='신고일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_noshow_reports', verbose_name='처리자')
    
    class Meta:
        verbose_name = '노쇼 신고'
        verbose_name_plural = '노쇼 신고 관리'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'reported_user', 'groupbuy'],
                name='unique_noshow_report_per_user_groupbuy'
            )
        ]
    
    def __str__(self):
        return f'{self.reporter.username}이 {self.reported_user.username}을 신고 ({self.groupbuy.title})'

@receiver(post_save, sender=GroupBuy)
def handle_status_change(sender, instance, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields is None or 'status' in update_fields:
        instance.notify_status_change()

# Import PhoneVerification model
from .models_verification import PhoneVerification
# Import BidVote model
from .models_voting import BidVote
# Import Banner and Event models
from .models_banner import Banner, Event