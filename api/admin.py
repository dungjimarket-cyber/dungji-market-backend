from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import (
    Category, Product, GroupBuy, Bid, Penalty, User, Badge,
    TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail,
    SubscriptionProductDetail, StandardProductDetail, ProductCustomField,
    ProductCustomValue, ParticipantConsent, PhoneVerification, Banner, Event,
    Review, NoShowReport, BidToken, BidTokenPurchase, BidTokenAdjustmentLog
)
from django.utils.html import mark_safe
from django.conf import settings
import logging
from .views_auth import kakao_unlink

# 추가 어드민 클래스들 import (RemoteSalesCertification 포함)
from .admin_extra import *

logger = logging.getLogger(__name__)

# 설정 확인 로깅
logger.info(f"Admin 로드 시 USE_S3: {settings.USE_S3}")
logger.info(f"Admin 로드 시 DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")

# Admin 사이트 타이틀 한글화
AdminSite.site_header = '둥지마켓 관리자'
AdminSite.site_title = '둥지마켓 관리자 포털'
AdminSite.index_title = '둥지마켓 관리자 대시보드'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'detail_type']
    list_filter = ['detail_type', 'is_service']
    search_fields = ['name']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('name',)
        super().__init__(model, admin_site)
    
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        for action in perms:
            perms[action] = perms[action]
        return perms

@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'reason', 'start_date']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)

from .forms import UserCreationForm, UserChangeForm
from django.utils import timezone
from django.db.models import Count, Q
from django import forms

# BidToken 관련 인라인 Admin
class BidTokenInline(admin.TabularInline):
    model = BidToken
    extra = 0
    fields = ['token_type', 'status', 'expires_at', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    max_num = 10  # 최대 10개만 표시
    
    def get_queryset(self, request):
        # 최근 10개만 표시
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:10]

class BidTokenAdjustmentLogInline(admin.TabularInline):
    model = BidTokenAdjustmentLog
    fk_name = 'seller'  # seller 필드를 기준으로 인라인 표시
    extra = 0
    fields = ['adjustment_type', 'quantity', 'reason', 'admin', 'created_at']
    readonly_fields = ['adjustment_type', 'quantity', 'reason', 'admin', 'created_at']
    can_delete = False
    max_num = 10  # 최대 10개만 표시
    
    def get_queryset(self, request):
        # 최근 10개만 표시
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:10]

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    list_display = ['username', 'email', 'role', 'get_sns_type', 'is_business_verified', 'get_bid_tokens_count', 'get_subscription_status', 'display_business_reg_file']
    list_filter = ['role', 'sns_type', 'is_active', 'is_staff', 'is_business_verified']
    search_fields = ['username', 'email', 'business_number', 'nickname']
    ordering = ['username']
    readonly_fields = ('display_business_reg_file_preview', 'sns_type', 'sns_id', 'get_bid_tokens_summary', 'get_adjustment_history')
    
    def get_sns_type(self, obj):
        """가입 유형 표시"""
        if obj.sns_type == 'kakao':
            return mark_safe('<span style="color: #FEE500; background: #3C1E1E; padding: 2px 8px; border-radius: 4px;">카카오</span>')
        elif obj.sns_type == 'google':
            return mark_safe('<span style="color: #4285F4; background: #F1F3F4; padding: 2px 8px; border-radius: 4px;">구글</span>')
        elif obj.sns_type == 'email':
            return mark_safe('<span style="color: #666; background: #F5F5F5; padding: 2px 8px; border-radius: 4px;">이메일</span>')
        return obj.sns_type or '직접가입'
    get_sns_type.short_description = '가입유형'
    get_sns_type.admin_order_field = 'sns_type'
    
    def get_bid_tokens_count(self, obj):
        """활성 입찰권 수 표시"""
        if obj.role != 'seller':
            return '-'
        count = BidToken.objects.filter(
            seller=obj,
            status='active',
            token_type='single'
        ).count()
        if count > 0:
            return mark_safe(f'<span style="color: green; font-weight: bold;">{count}개</span>')
        return mark_safe('<span style="color: gray;">0개</span>')
    get_bid_tokens_count.short_description = '입찰권'
    
    def get_subscription_status(self, obj):
        """구독권 상태 표시"""
        if obj.role != 'seller':
            return '-'
        active_subscription = BidToken.objects.filter(
            seller=obj,
            token_type='unlimited',
            status='active',
            expires_at__gt=timezone.now()
        ).first()
        if active_subscription:
            days_left = (active_subscription.expires_at - timezone.now()).days
            return mark_safe(f'<span style="color: blue; font-weight: bold;">활성 ({days_left}일 남음)</span>')
        return mark_safe('<span style="color: gray;">없음</span>')
    get_subscription_status.short_description = '구독권'
    
    def get_bid_tokens_summary(self, obj):
        """입찰권 상세 요약"""
        if obj.role != 'seller':
            return '판매회원이 아닙니다'
        
        active_single = BidToken.objects.filter(
            seller=obj, status='active', token_type='single'
        ).count()
        
        used_tokens = BidToken.objects.filter(
            seller=obj, status='used'
        ).count()
        
        active_subscription = BidToken.objects.filter(
            seller=obj,
            token_type='unlimited',
            status='active',
            expires_at__gt=timezone.now()
        ).first()
        
        summary = f"""
        <div style="line-height: 1.8;">
            <strong>입찰권 현황:</strong><br>
            • 활성 입찰권: {active_single}개<br>
            • 사용된 입찰권: {used_tokens}개<br>
            • 구독권: {'활성' if active_subscription else '없음'}
        """
        
        if active_subscription:
            summary += f"<br>• 구독권 만료일: {active_subscription.expires_at.strftime('%Y-%m-%d %H:%M')}"
        
        summary += "</div>"
        return mark_safe(summary)
    get_bid_tokens_summary.short_description = '입찰권 요약'
    
    def get_adjustment_history(self, obj):
        """최근 조정 이력"""
        if obj.role != 'seller':
            return '판매회원이 아닙니다'
        
        recent_logs = BidTokenAdjustmentLog.objects.filter(
            seller=obj
        ).order_by('-created_at')[:5]
        
        if not recent_logs:
            return '조정 이력 없음'
        
        history = '<div style="line-height: 1.6;">'
        history += '<strong>최근 조정 이력:</strong><br>'
        for log in recent_logs:
            adjustment_type = {'add': '추가', 'subtract': '차감', 'grant_subscription': '구독권'}.get(log.adjustment_type, log.adjustment_type)
            history += f"• {log.created_at.strftime('%Y-%m-%d')} - {adjustment_type} {log.quantity}{'일' if log.adjustment_type == 'grant_subscription' else '개'} (사유: {log.reason[:20]}...)<br>"
        history += '</div>'
        
        return mark_safe(history)
    get_adjustment_history.short_description = '최근 조정 이력'
    
    def display_business_reg_file(self, obj):
        """어드민 목록에서 사업자등록증 표시"""
        if obj.business_license_image:
            return mark_safe(f'<a href="{obj.business_license_image}" target="_blank">보기</a>')
        return "없음"
    display_business_reg_file.short_description = '사업자등록증'
    
    def display_business_reg_file_preview(self, obj):
        """어드민 상세 페이지에서 사업자등록증 미리보기"""
        if obj.business_license_image:
            # URL 형태이므로 이미지로 처리
            return mark_safe(f'<img src="{obj.business_license_image}" width="400" />')
        return "사업자등록증 없음"
    display_business_reg_file_preview.short_description = '사업자등록증 미리보기'
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'role', 'password')}),
        ('가입정보', {'fields': ('sns_type', 'sns_id')}),
        ('개인정보', {'fields': ('nickname', 'phone_number', 'address_region')}),
        ('사업자정보', {'fields': ('business_number', 'business_license_image', 'display_business_reg_file_preview', 'is_business_verified', 'is_remote_sales')}),
        ('입찰권 관리', {'fields': ('get_bid_tokens_summary', 'get_adjustment_history'), 'classes': ('collapse',)}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('중요 날짜', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')
    inlines = [BidTokenInline, BidTokenAdjustmentLogInline]
    actions = ['add_5_bid_tokens', 'add_10_bid_tokens', 'grant_7day_subscription', 'grant_30day_subscription', 'approve_business_verification']

    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('username',)
        super().__init__(model, admin_site)
    
    def get_inlines(self, request, obj):
        """판매회원인 경우에만 BidToken 관련 인라인 표시"""
        if obj and obj.role == 'seller':
            return self.inlines
        return []
    
    # 대량 액션들
    def add_5_bid_tokens(self, request, queryset):
        """선택한 판매회원들에게 입찰권 5개 추가"""
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 입찰권 5개 생성
            for _ in range(5):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='add',
                quantity=5,
                reason='관리자 대량 추가 (5개)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 입찰권 5개씩 추가했습니다.')
    add_5_bid_tokens.short_description = '선택한 판매회원에게 입찰권 5개 추가'
    
    def add_10_bid_tokens(self, request, queryset):
        """선택한 판매회원들에게 입찰권 10개 추가"""
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 입찰권 10개 생성
            for _ in range(10):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='add',
                quantity=10,
                reason='관리자 대량 추가 (10개)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 입찰권 10개씩 추가했습니다.')
    add_10_bid_tokens.short_description = '선택한 판매회원에게 입찰권 10개 추가'
    
    def grant_7day_subscription(self, request, queryset):
        """선택한 판매회원들에게 7일 구독권 부여"""
        from datetime import timedelta
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 기존 구독권 만료
            BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active'
            ).update(status='expired')
            
            # 새 구독권 생성
            expires_at = timezone.now() + timedelta(days=7)
            BidToken.objects.create(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at=expires_at
            )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='grant_subscription',
                quantity=7,
                reason='관리자 대량 부여 (7일)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 7일 구독권을 부여했습니다.')
    grant_7day_subscription.short_description = '선택한 판매회원에게 7일 구독권 부여'
    
    def grant_30day_subscription(self, request, queryset):
        """선택한 판매회원들에게 30일 구독권 부여"""
        from datetime import timedelta
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 기존 구독권 만료
            BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active'
            ).update(status='expired')
            
            # 새 구독권 생성
            expires_at = timezone.now() + timedelta(days=30)
            BidToken.objects.create(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at=expires_at
            )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='grant_subscription',
                quantity=30,
                reason='관리자 대량 부여 (30일)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 30일 구독권을 부여했습니다.')
    grant_30day_subscription.short_description = '선택한 판매회원에게 30일 구독권 부여'
    
    def approve_business_verification(self, request, queryset):
        """선택한 판매회원들의 사업자 인증 승인"""
        sellers = queryset.filter(role='seller', is_business_verified=False)
        count = sellers.update(is_business_verified=True)
        self.message_user(request, f'{count}명의 판매회원 사업자 인증을 승인했습니다.')
    approve_business_verification.short_description = '선택한 판매회원 사업자 인증 승인'
    
    def delete_model(self, request, obj):
        """개별 사용자 삭제 시 카카오 연결 해제"""
        if obj.sns_type == 'kakao' and obj.sns_id:
            kakao_unlink_success = kakao_unlink(obj.sns_id)
            if not kakao_unlink_success:
                logger.warning(f"관리자 삭제: 카카오 연결 끊기 실패했지만 삭제는 진행합니다. User ID: {obj.id}")
            else:
                logger.info(f"관리자 삭제: 카카오 연결 끊기 성공. User ID: {obj.id}")
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """다중 사용자 삭제 시 카카오 연결 해제"""
        for user in queryset:
            if user.sns_type == 'kakao' and user.sns_id:
                kakao_unlink_success = kakao_unlink(user.sns_id)
                if not kakao_unlink_success:
                    logger.warning(f"관리자 대량 삭제: 카카오 연결 끊기 실패했지만 삭제는 진행합니다. User ID: {user.id}")
                else:
                    logger.info(f"관리자 대량 삭제: 카카오 연결 끊기 성공. User ID: {user.id}")
        super().delete_queryset(request, queryset)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'icon']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)


# 카테고리별 상세 정보 모델 인라인
class TelecomProductDetailInline(admin.StackedInline):
    model = TelecomProductDetail
    can_delete = True
    verbose_name_plural = '통신 상품 상세 정보'

class ElectronicsProductDetailInline(admin.StackedInline):
    model = ElectronicsProductDetail
    can_delete = True
    verbose_name_plural = '가전 제품 상세 정보'

class RentalProductDetailInline(admin.StackedInline):
    model = RentalProductDetail
    can_delete = True
    verbose_name_plural = '렌탈 상품 상세 정보'

class SubscriptionProductDetailInline(admin.StackedInline):
    model = SubscriptionProductDetail
    can_delete = True
    verbose_name_plural = '구독 상품 상세 정보'

class StandardProductDetailInline(admin.StackedInline):
    model = StandardProductDetail
    can_delete = True
    verbose_name_plural = '일반 상품 상세 정보'

class ProductCustomValueInline(admin.TabularInline):
    model = ProductCustomValue
    extra = 1
    verbose_name_plural = '커스텀 필드 값'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'is_available', 'display_image']
    list_filter = ['is_available', 'category__detail_type']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('category_name', 'display_image_preview')
    
    def display_image(self, obj):
        """어드민 목록에서 이미지 썸네일 표시"""
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        elif obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="50" height="50" />')
        return "이미지 없음"
    display_image.short_description = '이미지'
    
    def display_image_preview(self, obj):
        """어드민 상세 페이지에서 이미지 미리보기"""
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="300" />')
        elif obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="300" />')
        return "이미지 없음"
    display_image_preview.short_description = '이미지 미리보기'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'slug', 'description', 'category', 'product_type', 'base_price', 'is_available', 'release_date')
        }),
        ('이미지', {
            'fields': ('image', 'image_url', 'display_image_preview'),
            'description': '이미지 파일을 업로드하거나 외부 URL을 입력하세요. 둘 다 입력된 경우 업로드된 이미지가 우선 사용됩니다.'
        }),
        ('추가 정보', {
            'fields': ('attributes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 이미지 처리"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 이미지 필드가 변경되었는지 확인
        if 'image' in form.changed_data:
            logger.info(f"ProductAdmin: 이미지 필드 변경 감지 - {form.cleaned_data.get('image')}")
        
        # 기본 저장 처리
        super().save_model(request, obj, form, change)
        
        # 저장 후 이미지 정보 로깅
        if obj.image:
            logger.info(f"ProductAdmin: 상품 '{obj.name}' 이미지 저장 완료")
            logger.info(f"ProductAdmin: 이미지 경로 - {obj.image.name}")
            logger.info(f"ProductAdmin: 이미지 URL - {obj.image.url}")
        else:
            logger.info(f"ProductAdmin: 상품 '{obj.name}' 이미지 없음")
    
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        if obj is None:
            return inline_instances
            
        inlines = self.get_inlines(request, obj)
        
        # 카테고리 유형에 따라 적절한 인라인 선택
        if obj.category and obj.category.detail_type == 'telecom':
            inlines = [TelecomProductDetailInline] + [i for i in inlines if i != TelecomProductDetailInline]
        elif obj.category and obj.category.detail_type == 'electronics':
            inlines = [ElectronicsProductDetailInline] + [i for i in inlines if i != ElectronicsProductDetailInline]
        elif obj.category and obj.category.detail_type == 'rental':
            inlines = [RentalProductDetailInline] + [i for i in inlines if i != RentalProductDetailInline]
        elif obj.category and obj.category.detail_type == 'subscription':
            inlines = [SubscriptionProductDetailInline] + [i for i in inlines if i != SubscriptionProductDetailInline]
        else:
            inlines = [StandardProductDetailInline] + [i for i in inlines if i != StandardProductDetailInline]
        
        # 커스텀 필드 값 인라인 추가
        inlines.append(ProductCustomValueInline)
            
        for inline_class in inlines:
            inline = inline_class(self.model, self.admin_site)
            inline_instances.append(inline)
            
        return inline_instances

@admin.register(ProductCustomField)
class ProductCustomFieldAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'field_label', 'category', 'field_type', 'is_required']
    list_filter = ['category', 'field_type', 'is_required']
    search_fields = ['field_name', 'field_label']

@admin.register(TelecomProductDetail)
class TelecomProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'carrier', 'registration_type', 'plan_info']
    list_filter = ['carrier', 'registration_type']
    search_fields = ['product__name']

@admin.register(ElectronicsProductDetail)
class ElectronicsProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'manufacturer', 'warranty_period']
    list_filter = ['manufacturer']
    search_fields = ['product__name']

@admin.register(RentalProductDetail)
class RentalProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'monthly_fee', 'deposit_amount']
    search_fields = ['product__name']

@admin.register(SubscriptionProductDetail)
class SubscriptionProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'billing_cycle', 'auto_renewal', 'free_trial_days']
    list_filter = ['billing_cycle', 'auto_renewal']
    search_fields = ['product__name']

@admin.register(StandardProductDetail)
class StandardProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'brand', 'shipping_fee']
    list_filter = ['brand']
    search_fields = ['product__name']

@admin.register(GroupBuy)
class GroupBuyAdmin(admin.ModelAdmin):
    list_display = ('product', 'creator', 'status', 'current_participants', 'end_time')
    raw_id_fields = ('participants',)
    readonly_fields = ('current_participants',)
    actions = ['force_complete_groupbuy']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('product',)
        super().__init__(model, admin_site)
        
    def force_complete_groupbuy(self, request, queryset):
        for groupbuy in queryset:
            groupbuy.status = 'completed'
            groupbuy.save()
    force_complete_groupbuy.short_description = '선택한 공구를 강제 완료 처리'

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('seller', 'groupbuy', 'bid_type', 'display_amount', 'is_selected')
    list_editable = ('is_selected',)
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('seller',)
        super().__init__(model, admin_site)

    def display_amount(self, obj):
        return f"{obj.amount // 10000}****"  # 부분 마스킹 처리
    display_amount.short_description = '입찰 금액'


@admin.register(ParticipantConsent)
class ParticipantConsentAdmin(admin.ModelAdmin):
    list_display = ['get_participant_name', 'get_groupbuy_title', 'status', 'agreed_at', 'disagreed_at', 'consent_deadline']
    list_filter = ['status', 'created_at']
    search_fields = ['participation__user__username', 'participation__groupbuy__title']
    readonly_fields = ['agreed_at', 'disagreed_at', 'created_at', 'updated_at']
    
    def get_participant_name(self, obj):
        return obj.participation.user.username
    get_participant_name.short_description = '참여자'
    
    def get_groupbuy_title(self, obj):
        return obj.participation.groupbuy.title
    get_groupbuy_title.short_description = '공구명'


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    """휴대폰 인증 관리"""
    list_display = ['phone_number', 'status', 'purpose', 'user', 'created_at', 'expires_at', 'attempt_count']
    list_filter = ['status', 'purpose', 'created_at']
    search_fields = ['phone_number', 'user__username', 'user__email']
    readonly_fields = ['verification_code', 'created_at', 'expires_at', 'verified_at', 'ip_address']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('phone_number', 'verification_code', 'status', 'purpose')
        }),
        ('인증 정보', {
            'fields': ('created_at', 'expires_at', 'verified_at', 'attempt_count', 'max_attempts')
        }),
        ('사용자 정보', {
            'fields': ('user', 'ip_address')
        }),
    )
    
    def has_add_permission(self, request):
        """관리자 페이지에서 직접 생성 불가"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가"""
        return False
    
    actions = ['cleanup_expired']
    
    def cleanup_expired(self, request, queryset):
        """만료된 인증 정리"""
        PhoneVerification.cleanup_expired()
        self.message_user(request, "만료된 인증이 정리되었습니다.")
    cleanup_expired.short_description = "만료된 인증 정리"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'banner_type', 'order', 'is_active', 'start_date', 'end_date', 'event', 'created_at']
    list_filter = ['banner_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['title', 'link_url']
    ordering = ['order', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'banner_type', 'order', 'is_active')
        }),
        ('이미지', {
            'fields': ('image', 'image_url', 'image_preview'),
            'description': '이미지를 업로드하거나 URL을 직접 입력하세요. 이미지 업로드 시 자동으로 S3에 업로드됩니다.'
        }),
        ('링크', {
            'fields': ('event', 'link_url'),
            'description': '이벤트를 선택하거나 외부 링크 URL을 입력하세요. 이벤트가 우선됩니다.'
        }),
        ('표시 기간', {
            'fields': ('start_date', 'end_date'),
            'description': '배너가 표시될 기간을 설정하세요. 비워두면 항상 표시됩니다.'
        }),
        ('메타 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'image_url', 'image_preview']
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="300" style="border-radius: 8px;" />')
        elif obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="300" style="border-radius: 8px;" />')
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # 유효한 배너인지 표시하기 위해 어노테이션 추가 가능
        return qs
    
    actions = ['activate_banners', 'deactivate_banners']
    
    def activate_banners(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 배너가 활성화되었습니다.')
    activate_banners.short_description = '선택한 배너 활성화'
    
    def deactivate_banners(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 배너가 비활성화되었습니다.')
    deactivate_banners.short_description = '선택한 배너 비활성화'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'status', 'start_date', 'end_date', 'is_active', 'view_count', 'created_at']
    list_filter = ['event_type', 'status', 'is_active', 'start_date', 'end_date']
    search_fields = ['title', 'content', 'short_description']
    ordering = ['-start_date', '-created_at']
    prepopulated_fields = {}  # 동적으로 설정
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'slug', 'event_type', 'status', 'is_active')
        }),
        ('이벤트 내용', {
            'fields': ('short_description', 'content'),
            'description': 'HTML 태그를 사용할 수 있습니다.'
        }),
        ('이미지', {
            'fields': ('thumbnail', 'thumbnail_url', 'thumbnail_preview', 'content_image', 'content_image_url', 'content_image_preview'),
            'description': '썸네일은 목록에서 표시되고, 본문 이미지는 상세 페이지에서 표시됩니다.'
        }),
        ('기간 설정', {
            'fields': ('start_date', 'end_date')
        }),
        ('통계', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'thumbnail_url', 'content_image_url', 'view_count', 'status', 'thumbnail_preview', 'content_image_preview']
    
    def thumbnail_preview(self, obj):
        """썸네일 미리보기"""
        if obj.thumbnail_url:
            return mark_safe(f'<img src="{obj.thumbnail_url}" width="200" style="border-radius: 8px;" />')
        elif obj.thumbnail:
            return mark_safe(f'<img src="{obj.thumbnail.url}" width="200" style="border-radius: 8px;" />')
        return "썸네일 없음"
    thumbnail_preview.short_description = '썸네일 미리보기'
    
    def content_image_preview(self, obj):
        """본문 이미지 미리보기"""
        if obj.content_image_url:
            return mark_safe(f'<img src="{obj.content_image_url}" width="300" style="border-radius: 8px;" />')
        elif obj.content_image:
            return mark_safe(f'<img src="{obj.content_image.url}" width="300" style="border-radius: 8px;" />')
        return "본문 이미지 없음"
    content_image_preview.short_description = '본문 이미지 미리보기'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # 수정하는 경우
            readonly.append('slug')  # 슬러그는 수정 불가
        return readonly
    
    def get_prepopulated_fields(self, request, obj=None):
        if obj is None:  # 새로 생성하는 경우에만
            return {'slug': ('title',)}
        return {}
    
    actions = ['activate_events', 'deactivate_events', 'reset_view_count']
    
    def activate_events(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 이벤트가 활성화되었습니다.')
    activate_events.short_description = '선택한 이벤트 활성화'
    
    def deactivate_events(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 이벤트가 비활성화되었습니다.')
    deactivate_events.short_description = '선택한 이벤트 비활성화'
    
    def reset_view_count(self, request, queryset):
        updated = queryset.update(view_count=0)
        self.message_user(request, f'{updated}개의 이벤트 조회수가 초기화되었습니다.')
    reset_view_count.short_description = '조회수 초기화'


# BidTokenAdjustmentLog만 추가 등록 (BidToken, BidTokenPurchase는 admin_extra.py에서 관리)
@admin.register(BidTokenAdjustmentLog)
class BidTokenAdjustmentLogAdmin(admin.ModelAdmin):
    list_display = ['seller', 'admin', 'adjustment_type', 'quantity', 'reason_summary', 'created_at']
    list_filter = ['adjustment_type', 'created_at']
    search_fields = ['seller__username', 'seller__email', 'admin__username', 'reason']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def reason_summary(self, obj):
        """사유 요약"""
        if len(obj.reason) > 30:
            return f"{obj.reason[:30]}..."
        return obj.reason
    reason_summary.short_description = '사유'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('seller', 'admin')
    
    def has_add_permission(self, request):
        """직접 생성 불가"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가"""
        return False