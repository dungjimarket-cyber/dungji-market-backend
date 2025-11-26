"""
상담 관련 어드민 설정
"""
import json
import logging
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required

from .models_consultation import ConsultationType, ConsultationRequest
from .models_consultation_flow import ConsultationFlow, ConsultationFlowOption
from .models_local_business import LocalBusinessCategory

logger = logging.getLogger(__name__)


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
        'consultation_type_text', 'region', 'created_at', 'contacted_at_display'
    ]
    list_filter = ['status', 'category', 'consultation_type_text', 'created_at', 'contacted_at', 'completed_at']
    search_fields = ['name', 'phone', 'email', 'content', 'region', 'consultation_type_text']
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
            'fields': ('category', 'consultation_type_text', 'region')
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
    change_list_template = 'admin/consultation_flow_changelist.html'

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ai-generate/', self.admin_site.admin_view(self.ai_generate_view), name='consultation_flow_ai_generate'),
            path('ai-generate/run/', self.admin_site.admin_view(self.ai_generate_run), name='consultation_flow_ai_generate_run'),
            path('preview/<int:category_id>/', self.admin_site.admin_view(self.preview_flow), name='consultation_flow_preview'),
            path('bulk-save/', self.admin_site.admin_view(self.bulk_save), name='consultation_flow_bulk_save'),
        ]
        return custom_urls + urls

    def ai_generate_view(self, request):
        """AI 플로우 생성 페이지"""
        categories = LocalBusinessCategory.objects.filter(is_active=True).order_by('order_index')
        context = {
            **self.admin_site.each_context(request),
            'title': 'AI 상담 플로우 생성',
            'categories': categories,
        }
        return render(request, 'admin/consultation_flow_ai_generate.html', context)

    def ai_generate_run(self, request):
        """AI로 플로우 생성 실행"""
        if request.method != 'POST':
            return JsonResponse({'error': 'POST만 허용'}, status=405)

        try:
            data = json.loads(request.body)
            category_id = data.get('category_id')
            prompt = data.get('prompt', '')
            replace_existing = data.get('replace_existing', False)

            if not category_id:
                return JsonResponse({'error': '카테고리를 선택해주세요.'}, status=400)

            # 카테고리 조회
            try:
                category = LocalBusinessCategory.objects.get(id=category_id)
            except LocalBusinessCategory.DoesNotExist:
                return JsonResponse({'error': '카테고리를 찾을 수 없습니다.'}, status=404)

            # OpenAI API 호출
            from .utils.ai_consultation_flow import generate_consultation_flow
            result = generate_consultation_flow(category.name, prompt)

            if not result.get('success'):
                return JsonResponse({'error': result.get('error', 'AI 생성 실패')}, status=500)

            flows_data = result.get('flows', [])

            # 기존 데이터 삭제 (옵션 선택 시)
            if replace_existing:
                ConsultationFlow.objects.filter(category=category).delete()

            # 플로우 생성
            created_count = 0
            for idx, flow_data in enumerate(flows_data):
                flow = ConsultationFlow.objects.create(
                    category=category,
                    step_number=flow_data.get('step_number', idx + 1),
                    question=flow_data.get('question', ''),
                    is_required=flow_data.get('is_required', True),
                    depends_on_step=flow_data.get('depends_on_step'),
                    depends_on_options=flow_data.get('depends_on_options', []),
                    order_index=idx,
                    is_active=True,
                )

                # 옵션 생성
                for opt_idx, opt_data in enumerate(flow_data.get('options', [])):
                    ConsultationFlowOption.objects.create(
                        flow=flow,
                        key=opt_data.get('key', f'opt_{opt_idx}'),
                        label=opt_data.get('label', ''),
                        icon=opt_data.get('icon', ''),
                        logo=opt_data.get('logo', ''),
                        description=opt_data.get('description', ''),
                        is_custom_input=opt_data.get('is_custom_input', False),
                        order_index=opt_idx,
                        is_active=True,
                    )

                created_count += 1

            return JsonResponse({
                'success': True,
                'message': f'{category.name} 카테고리에 {created_count}개의 질문 플로우가 생성되었습니다.',
                'flows': flows_data,
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 요청 형식'}, status=400)
        except Exception as e:
            logger.exception("AI 플로우 생성 오류")
            return JsonResponse({'error': str(e)}, status=500)

    def preview_flow(self, request, category_id):
        """카테고리별 플로우 미리보기"""
        try:
            category = LocalBusinessCategory.objects.get(id=category_id)
            flows = ConsultationFlow.objects.filter(
                category=category,
                is_active=True
            ).prefetch_related('options').order_by('step_number', 'order_index')

            flows_data = []
            for flow in flows:
                flow_dict = {
                    'id': flow.id,
                    'step_number': flow.step_number,
                    'question': flow.question,
                    'is_required': flow.is_required,
                    'depends_on_step': flow.depends_on_step,
                    'depends_on_options': flow.depends_on_options,
                    'options': [
                        {
                            'key': opt.key,
                            'label': opt.label,
                            'icon': opt.icon,
                            'logo': opt.logo,
                            'description': opt.description,
                            'is_custom_input': opt.is_custom_input,
                        }
                        for opt in flow.options.filter(is_active=True).order_by('order_index')
                    ]
                }
                flows_data.append(flow_dict)

            return JsonResponse({
                'category': category.name,
                'flows': flows_data,
            })
        except LocalBusinessCategory.DoesNotExist:
            return JsonResponse({'error': '카테고리를 찾을 수 없습니다.'}, status=404)

    def bulk_save(self, request):
        """플로우 일괄 저장 (수정 기능)"""
        if request.method != 'POST':
            return JsonResponse({'error': 'POST만 허용'}, status=405)

        try:
            data = json.loads(request.body)
            category_id = data.get('category_id')
            flows_data = data.get('flows', [])

            if not category_id:
                return JsonResponse({'error': '카테고리를 선택해주세요.'}, status=400)

            try:
                category = LocalBusinessCategory.objects.get(id=category_id)
            except LocalBusinessCategory.DoesNotExist:
                return JsonResponse({'error': '카테고리를 찾을 수 없습니다.'}, status=404)

            # 기존 플로우 삭제
            ConsultationFlow.objects.filter(category=category).delete()

            # 새 플로우 생성
            created_count = 0
            for idx, flow_data in enumerate(flows_data):
                flow = ConsultationFlow.objects.create(
                    category=category,
                    step_number=flow_data.get('step_number', idx + 1),
                    question=flow_data.get('question', ''),
                    is_required=flow_data.get('is_required', True),
                    depends_on_step=flow_data.get('depends_on_step'),
                    depends_on_options=flow_data.get('depends_on_options', []),
                    order_index=idx,
                    is_active=True,
                )

                # 옵션 생성
                for opt_idx, opt_data in enumerate(flow_data.get('options', [])):
                    ConsultationFlowOption.objects.create(
                        flow=flow,
                        key=opt_data.get('key', f'opt_{opt_idx}'),
                        label=opt_data.get('label', ''),
                        icon=opt_data.get('icon', ''),
                        logo=opt_data.get('logo', ''),
                        description=opt_data.get('description', ''),
                        is_custom_input=opt_data.get('is_custom_input', False),
                        order_index=opt_idx,
                        is_active=True,
                    )

                created_count += 1

            logger.info(f"플로우 일괄 저장: {category.name} - {created_count}개")

            return JsonResponse({
                'success': True,
                'message': f'{category.name} 카테고리에 {created_count}개의 질문 플로우가 저장되었습니다.',
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 요청 형식'}, status=400)
        except Exception as e:
            logger.exception("플로우 일괄 저장 오류")
            return JsonResponse({'error': str(e)}, status=500)

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
