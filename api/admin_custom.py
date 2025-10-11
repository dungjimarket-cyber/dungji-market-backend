from django.contrib import admin
from django.utils.html import mark_safe, format_html
from django.utils import timezone
from api.models_custom import (
    CustomGroupBuy,
    CustomGroupBuyImage,
    CustomParticipant,
    CustomFavorite,
    CustomGroupBuyRegion,
    CustomNoShowReport,
    CustomPenalty,
    SMSLog
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
        'created_at', 'updated_at', 'completed_at',
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
        price = obj.final_price
        if price is None:
            return "-"
        if isinstance(price, list):
            if len(price) == 0:
                return "-"
            if len(price) == 1:
                return f"{price[0]:,}원"
            return f"{min(price):,}원 ~ {max(price):,}원"
        return f"{price:,}원"
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


@admin.register(CustomNoShowReport)
class CustomNoShowReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter', 'reported_user', 'custom_groupbuy', 'report_type', 'status', 'cancelled_status', 'edit_status', 'created_at']
    list_filter = ['status', 'report_type', 'is_cancelled', 'edit_count', 'created_at', 'processed_at']
    search_fields = ['reporter__username', 'reported_user__username', 'custom_groupbuy__title', 'content']
    readonly_fields = ['created_at', 'updated_at', 'processed_at', 'processed_by', 'edit_count',
                      'evidence_image_display', 'evidence_image_2_display', 'evidence_image_3_display']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('신고 정보', {
            'fields': ('reporter', 'reported_user', 'custom_groupbuy', 'report_type', 'content', 'created_at', 'updated_at')
        }),
        ('증빙 자료', {
            'fields': ('evidence_image', 'evidence_image_2', 'evidence_image_3',
                      'evidence_image_display', 'evidence_image_2_display', 'evidence_image_3_display')
        }),
        ('수정/취소 정보', {
            'fields': ('edit_count', 'is_cancelled', 'cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('처리 정보', {
            'fields': ('status', 'admin_comment', 'processed_by', 'processed_at')
        }),
    )

    def cancelled_status(self, obj):
        if obj.is_cancelled:
            return mark_safe('<span style="background-color: #DC3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">취소됨</span>')
        return '-'
    cancelled_status.short_description = '취소'

    def edit_status(self, obj):
        if obj.edit_count > 0:
            return mark_safe(f'<span style="color: blue;">수정 {obj.edit_count}회</span>')
        return '-'
    edit_status.short_description = '수정'

    actions = ['confirm_reports', 'reject_reports', 'cancel_reports']

    def confirm_reports(self, request, queryset):
        from .models_custom import CustomParticipant
        import logging

        logger = logging.getLogger(__name__)
        processed_count = 0
        cancelled_count = 0
        completed_count = 0

        for report in queryset.filter(status='pending'):
            report.status = 'completed'
            report.processed_at = timezone.now()
            report.processed_by = request.user
            report.save()

            custom_groupbuy = report.custom_groupbuy

            if report.report_type == 'seller_noshow':
                custom_groupbuy.status = 'cancelled'
                custom_groupbuy.cancellation_reason = '판매자 노쇼로 인한 커스텀 공구 취소'
                custom_groupbuy.save()
                cancelled_count += 1
                logger.info(f"판매자 노쇼로 커스텀 공구 {custom_groupbuy.id} 취소 처리")

            else:
                confirmed_participants = CustomParticipant.objects.filter(
                    custom_groupbuy=custom_groupbuy,
                    status='confirmed'
                )
                confirmed_count = confirmed_participants.count()

                noshow_reports = CustomNoShowReport.objects.filter(
                    custom_groupbuy=custom_groupbuy,
                    report_type='buyer_noshow',
                    status__in=['pending', 'completed']
                )
                noshow_users = set(noshow_reports.values_list('reported_user_id', flat=True))
                noshow_count = len(noshow_users)

                if confirmed_count > 0 and noshow_count >= confirmed_count:
                    custom_groupbuy.status = 'cancelled'
                    custom_groupbuy.cancellation_reason = '구매자 전원 노쇼로 인한 커스텀 공구 취소'
                    custom_groupbuy.save()
                    cancelled_count += 1
                    logger.info(f"커스텀 공구 {custom_groupbuy.id} 전원 노쇼로 취소 처리")

                elif noshow_count > 0 and noshow_count < confirmed_count:
                    custom_groupbuy.status = 'completed'
                    custom_groupbuy.completed_at = timezone.now()
                    custom_groupbuy.save()
                    completed_count += 1
                    logger.info(f"커스텀 공구 {custom_groupbuy.id} 부분 노쇼로 판매완료 처리")

            processed_count += 1

        msg = f'{processed_count}개의 신고가 처리되었습니다.'
        if cancelled_count > 0:
            msg += f' ({cancelled_count}개 공구 취소)'
        if completed_count > 0:
            msg += f' ({completed_count}개 공구 완료)'

        self.message_user(request, msg)
    confirm_reports.short_description = '선택한 신고 처리완료'

    def reject_reports(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'{updated}개의 신고가 반려되었습니다.')
    reject_reports.short_description = '선택한 신고 반려'

    def cancel_reports(self, request, queryset):
        count = 0
        for report in queryset.filter(is_cancelled=False):
            report.is_cancelled = True
            report.cancelled_at = timezone.now()
            report.cancellation_reason = '관리자에 의한 수동 취소'
            report.save()
            count += 1
        self.message_user(request, f'{count}개의 신고가 취소 처리되었습니다.')
    cancel_reports.short_description = '선택한 신고 취소 처리'

    def evidence_image_display(self, obj):
        if obj.evidence_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a><br/>'
                '<a href="{}" download>다운로드</a>',
                obj.evidence_image.url, obj.evidence_image.url, obj.evidence_image.url
            )
        return "없음"
    evidence_image_display.short_description = "증빙 파일 1"

    def evidence_image_2_display(self, obj):
        if obj.evidence_image_2:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a><br/>'
                '<a href="{}" download>다운로드</a>',
                obj.evidence_image_2.url, obj.evidence_image_2.url, obj.evidence_image_2.url
            )
        return "없음"
    evidence_image_2_display.short_description = "증빙 파일 2"

    def evidence_image_3_display(self, obj):
        if obj.evidence_image_3:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 200px; max-height: 200px;" /></a><br/>'
                '<a href="{}" download>다운로드</a>',
                obj.evidence_image_3.url, obj.evidence_image_3.url, obj.evidence_image_3.url
            )
        return "없음"
    evidence_image_3_display.short_description = "증빙 파일 3"

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            if obj.status in ['confirmed', 'rejected'] and not obj.processed_by:
                obj.processed_by = request.user
                obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CustomPenalty)
class CustomPenaltyAdmin(admin.ModelAdmin):
    list_display = ['get_user_display', 'penalty_type', 'get_duration_display',
                    'get_status_display', 'start_date', 'end_date', 'count', 'created_by']
    list_filter = ['is_active', 'penalty_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__name', 'reason']
    readonly_fields = ['created_at', 'created_by']
    autocomplete_fields = ['user']
    fieldsets = (
        ('사용자 선택', {
            'fields': ('user',),
            'description': '사용자 닉네임(username) 또는 이메일을 입력하여 검색하세요. 자동완성이 지원됩니다.'
        }),
        ('패널티 정보', {
            'fields': ('penalty_type', 'reason', 'count')
        }),
        ('기간 설정', {
            'fields': ('duration_hours', 'start_date', 'end_date'),
            'description': '패널티 기간을 시간 단위로 입력하세요. end_date를 비워두면 자동 계산됩니다.'
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('기록', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        })
    )

    def get_user_display(self, obj):
        nickname = obj.user.nickname if obj.user.nickname else obj.user.username
        return f"{obj.user.username} ({nickname})"
    get_user_display.short_description = '사용자'
    get_user_display.admin_order_field = 'user__username'

    def get_duration_display(self, obj):
        return f"{obj.duration_hours}시간"
    get_duration_display.short_description = '패널티 기간'
    get_duration_display.admin_order_field = 'duration_hours'

    def get_status_display(self, obj):
        if obj.is_active:
            if obj.end_date and timezone.now() < obj.end_date:
                remaining = obj.end_date - timezone.now()
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return f"✅ 활성 (남은시간: {hours}시간 {minutes}분)"
            return mark_safe('<span style="color: red;">⚠️ 활성 (만료됨)</span>')
        return "❌ 비활성"
    get_status_display.short_description = '상태'
    get_status_display.admin_order_field = 'is_active'

    actions = ['deactivate_penalties', 'activate_penalties']

    def deactivate_penalties(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()}개의 패널티를 비활성화했습니다.")
    deactivate_penalties.short_description = '선택한 패널티 비활성화'

    def activate_penalties(self, request, queryset):
        count = 0
        for penalty in queryset:
            if penalty.end_date and timezone.now() < penalty.end_date:
                penalty.is_active = True
                penalty.save()
                count += 1
        self.message_user(request, f"{count}개의 패널티를 활성화했습니다.")
    activate_penalties.short_description = '선택한 패널티 활성화'


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_user_display', 'phone_number', 'message_type',
        'status', 'get_groupbuy_display', 'sent_at'
    ]
    list_filter = ['status', 'message_type', 'sent_at']
    search_fields = [
        'phone_number', 'user__username', 'user__email',
        'custom_groupbuy__title', 'message_content'
    ]
    readonly_fields = [
        'user', 'phone_number', 'message_type', 'message_content',
        'status', 'error_message', 'custom_groupbuy', 'sent_at'
    ]
    date_hierarchy = 'sent_at'

    fieldsets = (
        ('수신자 정보', {
            'fields': ('user', 'phone_number')
        }),
        ('메시지 정보', {
            'fields': ('message_type', 'message_content')
        }),
        ('발송 결과', {
            'fields': ('status', 'error_message', 'sent_at')
        }),
        ('관련 정보', {
            'fields': ('custom_groupbuy',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """SMS 로그는 시스템에서만 생성 가능"""
        return False

    def has_change_permission(self, request, obj=None):
        """SMS 로그는 수정 불가"""
        return False

    def has_delete_permission(self, request, obj=None):
        """SMS 로그는 삭제 가능 (관리자만)"""
        return request.user.is_superuser

    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.username}"
        return "-"
    get_user_display.short_description = '수신자'
    get_user_display.admin_order_field = 'user__username'

    def get_groupbuy_display(self, obj):
        if obj.custom_groupbuy:
            return f"{obj.custom_groupbuy.title}"
        return "-"
    get_groupbuy_display.short_description = '관련 공구'
    get_groupbuy_display.admin_order_field = 'custom_groupbuy__title'