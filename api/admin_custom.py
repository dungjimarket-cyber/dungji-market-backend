from django.contrib import admin
from api.models_custom import (
    CustomGroupBuy,
    CustomGroupBuyImage,
    CustomParticipant,
    CustomFavorite,
    CustomGroupBuyRegion
)


class CustomGroupBuyImageInline(admin.TabularInline):
    model = CustomGroupBuyImage
    extra = 0
    fields = ['image_url', 'order_index', 'is_primary']
    readonly_fields = ['created_at']


class CustomGroupBuyRegionInline(admin.TabularInline):
    model = CustomGroupBuyRegion
    extra = 0
    fields = ['region', 'created_at']
    readonly_fields = ['created_at']


@admin.register(CustomGroupBuy)
class CustomGroupBuyAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'type', 'status', 'seller',
        'current_participants', 'target_participants',
        'final_price', 'created_at'
    ]
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['title', 'seller__username', 'seller__email']
    readonly_fields = [
        'created_at', 'updated_at', 'expired_at', 'completed_at',
        'seller_decision_deadline', 'discount_valid_until',
        'current_participants', 'view_count', 'favorite_count',
        'final_price', 'is_completed', 'seller_type', 'seller_name', 'is_business_verified'
    ]

    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'description', 'type', 'categories', 'usage_guide')
        }),
        ('가격 정보', {
            'fields': ('original_price', 'discount_rate', 'final_price')
        }),
        ('인원 정보', {
            'fields': ('target_participants', 'current_participants', 'is_completed')
        }),
        ('시간 정보', {
            'fields': (
                'max_wait_hours', 'expired_at', 'completed_at',
                'seller_decision_deadline', 'discount_valid_days', 'discount_valid_until',
                'created_at', 'updated_at'
            )
        }),
        ('판매자 정보', {
            'fields': ('seller', 'seller_name', 'seller_type', 'is_business_verified', 'allow_partial_sale')
        }),
        ('할인 정보', {
            'fields': (
                'online_discount_type', 'discount_url', 'discount_codes',
                'location', 'location_detail', 'phone_number'
            )
        }),
        ('메타데이터', {
            'fields': ('meta_title', 'meta_image', 'meta_description', 'meta_price'),
            'classes': ('collapse',)
        }),
        ('상태 및 통계', {
            'fields': ('status', 'view_count', 'favorite_count')
        }),
    )

    inlines = [CustomGroupBuyImageInline, CustomGroupBuyRegionInline]

    def final_price(self, obj):
        return f"{obj.final_price:,}원"
    final_price.short_description = '최종 가격'


@admin.register(CustomGroupBuyImage)
class CustomGroupBuyImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'custom_groupbuy', 'order_index', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['custom_groupbuy__title']
    readonly_fields = ['created_at']


@admin.register(CustomParticipant)
class CustomParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'custom_groupbuy', 'status',
        'discount_code', 'discount_used', 'participated_at'
    ]
    list_filter = ['status', 'discount_used', 'participated_at']
    search_fields = [
        'user__username', 'custom_groupbuy__title',
        'participation_code', 'discount_code'
    ]
    readonly_fields = [
        'participated_at', 'participation_code',
        'discount_used_at', 'verified_by'
    ]

    fieldsets = (
        ('기본 정보', {
            'fields': ('custom_groupbuy', 'user', 'status', 'participated_at')
        }),
        ('참여 코드', {
            'fields': ('participation_code',)
        }),
        ('할인 정보', {
            'fields': ('discount_code', 'discount_url', 'discount_used', 'discount_used_at', 'verified_by')
        }),
    )


@admin.register(CustomFavorite)
class CustomFavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'custom_groupbuy', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'custom_groupbuy__title']
    readonly_fields = ['created_at']


@admin.register(CustomGroupBuyRegion)
class CustomGroupBuyRegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'custom_groupbuy', 'region', 'created_at']
    list_filter = ['created_at']
    search_fields = ['custom_groupbuy__title', 'region__name']
    readonly_fields = ['created_at']