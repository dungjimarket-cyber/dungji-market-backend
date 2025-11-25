"""
상담 관련 어드민 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models_consultation import ConsultationType, ConsultationRequest
from .models_consultation_flow import ConsultationFlow, ConsultationFlowOption


class ConsultationFlowOptionInline(admin.TabularInline):
    """질문 선택지 인라인"""
    model = ConsultationFlowOption
    extra = 1
    fields = ['key', 'label', 'icon', 'description', 'is_custom_input', 'order_index', 'is_active']
    ordering = ['order_index']


@admin.register(ConsultationType)
class ConsultationTypeAdmin(admin.ModelAdmin):
    """상담 유형 관리자"""

    list_display = [
        'id', 'category', 'name', 'icon', 'order_index',
        'is_active_display', 'created_at'
    ]
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    list_editable = ['order_index', 'icon']
    ordering = ['category', 'order_index']

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'name', 'icon', 'description')
        }),
        ('설정', {
            'fields': ('order_index', 'is_active')
        }),
    )

    def is_active_display(self, obj):
        """활성화 상태 표시"""
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981;">✅ 활성</span>'
            )
        return format_html(
            '<span style="color: #6b7280;">⏸ 비활성</span>'
        )
    is_active_display.short_description = "상태"

    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        """선택한 상담 유형 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 상담 유형이 활성화되었습니다.')
    make_active.short_description = "선택한 상담 유형 활성화"

    def make_inactive(self, request, queryset):
        """선택한 상담 유형 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 상담 유형이 비활성화되었습니다.')
    make_inactive.short_description = "선택한 상담 유형 비활성화"


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    """상담 신청 관리자"""

    list_display = [
        'id', 'status_badge', 'name', 'phone_display', 'category',
        'consultation_type', 'region', 'created_at', 'contacted_at_display'
    ]
    list_filter = ['status', 'category', 'created_at', 'contacted_at', 'completed_at']
    search_fields = ['name', 'phone', 'email', 'content', 'region']
    readonly_fields = [
        'user', 'created_at', 'updated_at', 'contacted_at', 'completed_at',
        'ai_summary', 'ai_recommended_types', 'content_preview'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('신청자 정보', {
            'fields': ('user', 'name', 'phone', 'email')
        }),
        ('상담 정보', {
            'fields': ('category', 'consultation_type', 'region')
        }),
        ('상담 내용', {
            'fields': ('content', 'content_preview')
        }),
        ('AI 분석', {
            'fields': ('ai_summary', 'ai_recommended_types'),
            'classes': ('collapse',)
        }),
        ('상태 관리', {
            'fields': ('status', 'admin_note')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at', 'contacted_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """상태 뱃지"""
        colors = {
            'pending': '#f59e0b',
            'contacted': '#3b82f6',
            'completed': '#10b981',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "상태"

    def phone_display(self, obj):
        """연락처 (클릭 시 전화)"""
        return format_html(
            '<a href="tel:{}">{}</a>',
            obj.phone.replace('-', ''),
            obj.phone
        )
    phone_display.short_description = "연락처"

    def contacted_at_display(self, obj):
        """연락일시 표시"""
        if obj.contacted_at:
            return obj.contacted_at.strftime('%m/%d %H:%M')
        return '-'
    contacted_at_display.short_description = "연락일시"

    def content_preview(self, obj):
        """내용 미리보기"""
        if obj.content:
            return format_html(
                '<div style="background: #f9fafb; padding: 15px; border: 1px solid #e5e7eb; '
                'border-radius: 8px; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">'
                '{}</div>',
                obj.content
            )
        return "내용 없음"
    content_preview.short_description = "내용 미리보기"

    def get_queryset(self, request):
        """쿼리셋 최적화"""
        return super().get_queryset(request).select_related(
            'user', 'category', 'consultation_type'
        )

    actions = ['mark_contacted', 'mark_completed', 'mark_cancelled']

    def mark_contacted(self, request, queryset):
        """선택한 신청 연락완료 처리"""
        updated = queryset.filter(status='pending').update(
            status='contacted',
            contacted_at=timezone.now()
        )
        self.message_user(request, f'{updated}개의 상담 신청이 연락완료 처리되었습니다.')
    mark_contacted.short_description = "선택한 신청 연락완료 처리"

    def mark_completed(self, request, queryset):
        """선택한 신청 상담완료 처리"""
        updated = queryset.filter(status__in=['pending', 'contacted']).update(
            status='completed',
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated}개의 상담 신청이 상담완료 처리되었습니다.')
    mark_completed.short_description = "선택한 신청 상담완료 처리"

    def mark_cancelled(self, request, queryset):
        """선택한 신청 취소 처리"""
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled'
        )
        self.message_user(request, f'{updated}개의 상담 신청이 취소 처리되었습니다.')
    mark_cancelled.short_description = "선택한 신청 취소 처리"


@admin.register(ConsultationFlow)
class ConsultationFlowAdmin(admin.ModelAdmin):
    """상담 질문 플로우 관리자"""

    list_display = [
        'id', 'category', 'step_number', 'question', 'depends_info',
        'options_count', 'is_required', 'is_active_display'
    ]
    list_filter = ['category', 'step_number', 'is_required', 'is_active']
    search_fields = ['question', 'category__name']
    list_editable = ['step_number', 'is_required']
    ordering = ['category', 'step_number', 'order_index']
    inlines = [ConsultationFlowOptionInline]

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'step_number', 'question')
        }),
        ('조건부 표시', {
            'fields': ('depends_on_step', 'depends_on_options'),
            'description': '특정 단계의 특정 선택지가 선택되었을 때만 이 질문을 표시합니다.'
        }),
        ('설정', {
            'fields': ('is_required', 'order_index', 'is_active')
        }),
    )

    def depends_info(self, obj):
        """조건부 표시 정보"""
        if obj.depends_on_step and obj.depends_on_options:
            return format_html(
                '<span style="color: #8b5cf6;">Step {} → {}</span>',
                obj.depends_on_step,
                ', '.join(obj.depends_on_options)
            )
        return '-'
    depends_info.short_description = "조건"

    def options_count(self, obj):
        """선택지 개수"""
        count = obj.options.count()
        return format_html(
            '<span style="color: #3b82f6;">{} 개</span>',
            count
        )
    options_count.short_description = "선택지"

    def is_required_display(self, obj):
        """필수 여부 표시"""
        if obj.is_required:
            return format_html('<span style="color: #ef4444;">필수</span>')
        return format_html('<span style="color: #6b7280;">선택</span>')
    is_required_display.short_description = "필수"

    def is_active_display(self, obj):
        """활성화 상태 표시"""
        if obj.is_active:
            return format_html('<span style="color: #10b981;">✅</span>')
        return format_html('<span style="color: #6b7280;">⏸</span>')
    is_active_display.short_description = "활성"

    def get_queryset(self, request):
        """쿼리셋 최적화"""
        return super().get_queryset(request).select_related('category').prefetch_related('options')

    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        """선택한 질문 플로우 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 질문 플로우가 활성화되었습니다.')
    make_active.short_description = "선택한 질문 플로우 활성화"

    def make_inactive(self, request, queryset):
        """선택한 질문 플로우 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 질문 플로우가 비활성화되었습니다.')
    make_inactive.short_description = "선택한 질문 플로우 비활성화"


@admin.register(ConsultationFlowOption)
class ConsultationFlowOptionAdmin(admin.ModelAdmin):
    """상담 선택지 관리자"""

    list_display = [
        'id', 'flow_info', 'key', 'label', 'icon',
        'is_custom_input_display', 'order_index', 'is_active_display'
    ]
    list_filter = ['flow__category', 'is_custom_input', 'is_active']
    search_fields = ['key', 'label', 'description', 'flow__question']
    list_editable = ['order_index', 'icon']
    ordering = ['flow', 'order_index']

    fieldsets = (
        ('연결 정보', {
            'fields': ('flow',)
        }),
        ('선택지 정보', {
            'fields': ('key', 'label', 'icon', 'description')
        }),
        ('설정', {
            'fields': ('is_custom_input', 'order_index', 'is_active')
        }),
    )

    def flow_info(self, obj):
        """질문 플로우 정보"""
        return format_html(
            '<span title="{}">{} - Step {}</span>',
            obj.flow.question,
            obj.flow.category.name,
            obj.flow.step_number
        )
    flow_info.short_description = "질문"

    def is_custom_input_display(self, obj):
        """직접 입력 여부 표시"""
        if obj.is_custom_input:
            return format_html('<span style="color: #f59e0b;">✏️ 입력</span>')
        return '-'
    is_custom_input_display.short_description = "직접입력"

    def is_active_display(self, obj):
        """활성화 상태 표시"""
        if obj.is_active:
            return format_html('<span style="color: #10b981;">✅</span>')
        return format_html('<span style="color: #6b7280;">⏸</span>')
    is_active_display.short_description = "활성"

    def get_queryset(self, request):
        """쿼리셋 최적화"""
        return super().get_queryset(request).select_related('flow', 'flow__category')
