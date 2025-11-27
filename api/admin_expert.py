"""
전문가 프로필 및 상담 매칭 Django Admin 설정
"""
from django.contrib import admin
from .models_expert import ExpertProfile, ConsultationMatch


@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'representative_name', 'business_name', 'category',
        'contact_phone', 'status', 'is_receiving_requests', 'created_at'
    ]
    list_filter = ['status', 'is_receiving_requests', 'is_business', 'category', 'created_at']
    search_fields = [
        'representative_name', 'business_name', 'business_number',
        'contact_phone', 'user__username', 'user__nickname'
    ]
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['regions']

    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'category', 'status', 'is_receiving_requests')
        }),
        ('기본 정보', {
            'fields': ('representative_name', 'contact_phone', 'contact_email')
        }),
        ('사업자 정보', {
            'fields': ('is_business', 'business_name', 'business_number', 'business_license_image'),
            'classes': ('collapse',)
        }),
        ('자격 정보', {
            'fields': ('license_number', 'license_image'),
            'classes': ('collapse',)
        }),
        ('활동 지역', {
            'fields': ('regions',)
        }),
        ('프로필', {
            'fields': ('profile_image', 'tagline', 'introduction')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'category')


@admin.register(ConsultationMatch)
class ConsultationMatchAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_consultation_info', 'get_expert_name',
        'status', 'created_at', 'replied_at', 'connected_at', 'completed_at'
    ]
    list_filter = ['status', 'created_at', 'replied_at', 'connected_at']
    search_fields = [
        'consultation__customer_name', 'consultation__customer_phone',
        'expert__representative_name', 'expert__business_name'
    ]
    readonly_fields = ['created_at', 'replied_at', 'connected_at', 'completed_at']

    fieldsets = (
        ('매칭 정보', {
            'fields': ('consultation', 'expert', 'status')
        }),
        ('전문가 답변', {
            'fields': ('expert_message', 'available_time')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'replied_at', 'connected_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def get_consultation_info(self, obj):
        # ConsultationRequest에는 customer_name 필드가 없고 name/phone을 사용함
        customer_name = getattr(obj.consultation, 'name', '') or ''
        return f"{obj.consultation.category.name} - {customer_name}"
    get_consultation_info.short_description = '상담 요청'

    def get_expert_name(self, obj):
        return obj.expert.representative_name
    get_expert_name.short_description = '전문가'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'consultation', 'consultation__category', 'expert'
        )
