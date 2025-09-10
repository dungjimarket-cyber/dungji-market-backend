from django.contrib import admin
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer, UsedPhoneRegion


class UsedPhoneImageInline(admin.TabularInline):
    model = UsedPhoneImage
    extra = 0


class UsedPhoneRegionInline(admin.TabularInline):
    """중고폰 지역 인라인 관리"""
    model = UsedPhoneRegion
    extra = 1
    max_num = 3  # 최대 3개 지역까지만
    autocomplete_fields = ['region']
    verbose_name = '거래 가능 지역'
    verbose_name_plural = '거래 가능 지역 (최대 3개)'


@admin.register(UsedPhone)
class UsedPhoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'model', 'brand', 'price', 'seller', 'status', 'get_regions', 'created_at']
    list_filter = ['status', 'brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'seller__username', 'description']
    inlines = [UsedPhoneRegionInline, UsedPhoneImageInline]
    readonly_fields = ['view_count', 'favorite_count', 'offer_count', 'get_regions_display', 'created_at', 'updated_at']
    exclude = ['region']  # 기존 단일 region 필드는 제외
    
    def get_regions(self, obj):
        """목록에서 지역 표시"""
        regions = obj.regions.select_related('region').all()
        return ', '.join([r.region.full_name for r in regions]) if regions else '-'
    get_regions.short_description = '거래 지역'
    
    def get_regions_display(self, obj):
        """상세페이지에서 지역 표시"""
        regions = obj.regions.select_related('region').all()
        if regions:
            return ' / '.join([r.region.full_name for r in regions])
        return '지역 정보 없음'
    get_regions_display.short_description = '거래 가능 지역'


@admin.register(UsedPhoneOffer)
class UsedPhoneOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone', 'buyer', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['phone__model', 'buyer__username']


@admin.register(UsedPhoneFavorite)
class UsedPhoneFavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'phone', 'created_at']
    search_fields = ['user__username', 'phone__model']