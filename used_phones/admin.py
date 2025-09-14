from django.contrib import admin
from .models import (UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer,
                     UsedPhoneRegion, TradeCancellation, UsedPhoneReview,
                     UsedPhoneReport, UsedPhonePenalty, UsedPhoneTransaction)


class UsedPhoneImageInline(admin.TabularInline):
    model = UsedPhoneImage
    extra = 0


class UsedPhoneRegionInline(admin.TabularInline):
    """중고폰 지역 인라인 관리"""
    model = UsedPhoneRegion
    extra = 1
    max_num = 3  # 최대 3개 지역까지만
    autocomplete_fields = ['region']  # 자동완성 필드
    verbose_name = '거래 가능 지역'
    verbose_name_plural = '거래 가능 지역 (최대 3개)'


@admin.register(UsedPhone)
class UsedPhoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'model', 'brand', 'price', 'seller', 'status', 'get_buyer_info', 'get_regions', 'created_at']
    list_filter = ['status', 'brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'seller__username', 'description']
    inlines = [UsedPhoneRegionInline, UsedPhoneImageInline]
    readonly_fields = ['view_count', 'favorite_count', 'offer_count', 'get_regions_display', 'get_buyer_display', 'created_at', 'updated_at']
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
    
    def get_buyer_info(self, obj):
        """목록에서 구매자 정보 표시 (거래중/판매완료인 경우)"""
        if obj.status in ['trading', 'sold']:
            # 수락된 제안 찾기
            accepted_offer = obj.offers.filter(status='accepted').first()
            if accepted_offer:
                return f"{accepted_offer.buyer.username} ({accepted_offer.offered_price:,}원)"
        return '-'
    get_buyer_info.short_description = '구매자 정보'
    
    def get_buyer_display(self, obj):
        """상세페이지에서 구매자 정보 표시"""
        if obj.status in ['trading', 'sold']:
            # 수락된 제안 찾기
            accepted_offer = obj.offers.filter(status='accepted').select_related('buyer').first()
            if accepted_offer:
                buyer = accepted_offer.buyer
                info = f"구매자: {buyer.username}\n"
                info += f"제안 금액: {accepted_offer.offered_price:,}원\n"
                if hasattr(buyer, 'phone') and buyer.phone:
                    info += f"연락처: {buyer.phone}\n"
                if hasattr(buyer, 'email') and buyer.email:
                    info += f"이메일: {buyer.email}\n"
                if accepted_offer.message:
                    info += f"메시지: {accepted_offer.message}"
                return info
        return '거래 정보 없음'
    get_buyer_display.short_description = '구매자 상세 정보'


@admin.register(UsedPhoneOffer)
class UsedPhoneOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_phone_info', 'buyer', 'offered_price', 'status', 'created_at']
    list_filter = ['status', 'phone__status']
    search_fields = ['phone__model', 'buyer__username']
    readonly_fields = ['phone', 'buyer', 'offered_price', 'message', 'status', 'seller_message', 'created_at']
    
    def get_phone_info(self, obj):
        """상품 정보 표시"""
        return f"{obj.phone.brand} {obj.phone.model} ({obj.phone.status})"
    get_phone_info.short_description = '상품 정보'


@admin.register(UsedPhoneFavorite)
class UsedPhoneFavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'phone', 'created_at']
    search_fields = ['user__username', 'phone__model']


@admin.register(TradeCancellation)
class TradeCancellationAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_phone_info', 'cancelled_by', 'canceller', 'reason', 'created_at']
    list_filter = ['cancelled_by', 'reason', 'created_at']
    search_fields = ['phone__model', 'canceller__username', 'custom_reason']
    readonly_fields = ['phone', 'offer', 'cancelled_by', 'canceller', 'reason', 'custom_reason', 'created_at']
    date_hierarchy = 'created_at'
    
    def get_phone_info(self, obj):
        """상품 정보 표시"""
        return f"{obj.phone.brand} {obj.phone.model}"
    get_phone_info.short_description = '상품'


@admin.register(UsedPhoneTransaction)
class UsedPhoneTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_phone_info', 'seller', 'buyer', 'final_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['phone__model', 'seller__username', 'buyer__username']
    readonly_fields = ['phone', 'offer', 'seller', 'buyer', 'final_price', 'created_at', 'updated_at', 'completed_at']

    def get_phone_info(self, obj):
        """상품 정보 표시"""
        return f"{obj.phone.brand} {obj.phone.model}"
    get_phone_info.short_description = '상품'


@admin.register(UsedPhoneReview)
class UsedPhoneReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_transaction_info', 'reviewer', 'reviewee', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['reviewer__username', 'reviewee__username', 'transaction__phone__model']
    readonly_fields = ['transaction', 'reviewer', 'reviewee', 'created_at', 'updated_at']

    def get_transaction_info(self, obj):
        """거래 정보 표시"""
        return f"{obj.transaction.phone.brand} {obj.transaction.phone.model}"
    get_transaction_info.short_description = '거래 상품'


@admin.register(UsedPhoneReport)
class UsedPhoneReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reported_user', 'reporter', 'report_type', 'status', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['reported_user__username', 'reporter__username', 'description']
    readonly_fields = ['reporter', 'created_at', 'updated_at']
    actions = ['mark_as_resolved', 'mark_as_processing']

    def mark_as_resolved(self, request, queryset):
        """신고를 해결됨으로 처리"""
        from django.utils import timezone
        updated_count = queryset.update(
            status='resolved',
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated_count}개의 신고가 해결됨으로 처리되었습니다.')
    mark_as_resolved.short_description = '선택된 신고를 해결됨으로 처리'

    def mark_as_processing(self, request, queryset):
        """신고를 처리중으로 변경"""
        from django.utils import timezone
        updated_count = queryset.update(
            status='processing',
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated_count}개의 신고가 처리중으로 변경되었습니다.')
    mark_as_processing.short_description = '선택된 신고를 처리중으로 변경'


@admin.register(UsedPhonePenalty)
class UsedPhonePenaltyAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'penalty_type', 'duration_days', 'status', 'is_active_display', 'start_date', 'end_date']
    list_filter = ['penalty_type', 'status', 'start_date']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['user', 'start_date', 'created_at', 'updated_at']
    actions = ['revoke_penalty']

    def is_active_display(self, obj):
        """현재 패널티 활성 상태 표시"""
        return obj.is_active()
    is_active_display.short_description = '현재 활성'
    is_active_display.boolean = True

    def revoke_penalty(self, request, queryset):
        """패널티 해제"""
        from django.utils import timezone
        updated_count = 0
        for penalty in queryset.filter(status='active'):
            penalty.status = 'revoked'
            penalty.revoked_by = request.user
            penalty.revoked_at = timezone.now()
            penalty.save()
            updated_count += 1

        self.message_user(request, f'{updated_count}개의 패널티가 해제되었습니다.')
    revoke_penalty.short_description = '선택된 패널티 해제'