from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import (
    Category, Product, GroupBuy, Bid, Penalty, User, Badge,
    TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail,
    SubscriptionProductDetail, StandardProductDetail, ProductCustomField,
    ProductCustomValue, ParticipantConsent, PhoneVerification
)
from django.utils.html import mark_safe

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

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    list_display = ['username', 'email', 'role', 'is_business_verified', 'display_business_reg_file']
    list_filter = ['role', 'is_active', 'is_staff', 'is_business_verified']
    search_fields = ['username', 'email', 'business_number']
    ordering = ['username']
    readonly_fields = ('display_business_reg_file_preview',)
    
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
        ('개인정보', {'fields': ('nickname', 'phone_number', 'address_region')}),
        ('사업자정보', {'fields': ('business_number', 'business_license_image', 'display_business_reg_file_preview', 'is_business_verified', 'is_remote_sales')}),
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

    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('username',)
        super().__init__(model, admin_site)

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
        # Django admin은 기본적으로 ImageField를 올바르게 처리하므로
        # 추가적인 처리는 필요 없음
        super().save_model(request, obj, form, change)
        
        # 저장 후 이미지 URL 확인 (디버깅용)
        if obj.image:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"상품 이미지 저장됨: {obj.image.url}")
    
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