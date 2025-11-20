"""
지역 업체 정보 Admin
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.http import HttpResponse
from django.contrib import messages
from django.utils.html import format_html
from django.core.management import call_command
from .models_local_business import (
    LocalBusinessCategory,
    LocalBusiness,
    LocalBusinessLink,
    LocalBusinessView
)
import io


@admin.register(LocalBusinessCategory)
class LocalBusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'name_en', 'google_place_type', 'order_index', 'is_active']
    list_editable = ['order_index', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'name_en']
    ordering = ['order_index', 'name']

    actions = ['init_categories']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('init-categories/', self.admin_site.admin_view(self.init_categories_view), name='init_local_business_categories_url'),
        ]
        return custom_urls + urls

    def init_categories_view(self, request):
        """카테고리 초기화 실행 (URL 직접 접속용)"""
        try:
            call_command('init_local_business_categories')
            self.message_user(request, "✅ 7개 업종 카테고리가 생성되었습니다!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ 오류 발생: {str(e)}", messages.ERROR)

        return redirect('../')

    def init_categories(self, request, queryset):
        """카테고리 초기화 액션"""
        try:
            call_command('init_local_business_categories')
            self.message_user(request, "카테고리가 초기화되었습니다.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    init_categories.short_description = "📋 카테고리 초기화 (7개 업종 생성)"


@admin.register(LocalBusiness)
class LocalBusinessAdmin(admin.ModelAdmin):
    list_display = [
        'rank_badge',
        'name',
        'region_name',
        'category_name',
        'rating_display',
        'review_count',
        'view_count',
        'is_new',
        'is_verified',
        'last_synced_at'
    ]
    list_filter = ['region_name', 'category', 'is_verified', 'is_new']
    search_fields = ['name', 'address', 'phone_number', 'region_name']
    ordering = ['region_name', 'category', 'rank_in_region']
    readonly_fields = [
        'google_place_id',
        'latitude',
        'longitude',
        'popularity_score',
        'view_count',
        'last_synced_at',
        'created_at',
        'updated_at',
        'google_maps_link'
    ]

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'region_name', 'name', 'address', 'phone_number')
        }),
        ('평점 및 순위', {
            'fields': ('rating', 'review_count', 'popularity_score', 'rank_in_region')
        }),
        ('상태', {
            'fields': ('is_verified', 'is_new', 'view_count')
        }),
        ('Google Places 정보', {
            'fields': ('google_place_id', 'latitude', 'longitude', 'photo_url', 'google_maps_link'),
            'classes': ('collapse',)
        }),
        ('시스템', {
            'fields': ('last_synced_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['collect_region_businesses', 'collect_all_businesses', 'update_selected_businesses']

    def rank_badge(self, obj):
        """순위 배지"""
        if obj.rank_in_region == 1:
            return format_html('<span style="background: gold; padding: 2px 8px; border-radius: 4px; font-weight: bold;">🥇 1위</span>')
        elif obj.rank_in_region == 2:
            return format_html('<span style="background: silver; padding: 2px 8px; border-radius: 4px; font-weight: bold;">🥈 2위</span>')
        elif obj.rank_in_region == 3:
            return format_html('<span style="background: #cd7f32; padding: 2px 8px; border-radius: 4px; font-weight: bold; color: white;">🥉 3위</span>')
        else:
            return f"{obj.rank_in_region}위"
    rank_badge.short_description = '순위'

    # region_name은 이제 모델 필드이므로 메서드 불필요

    def category_name(self, obj):
        return f"{obj.category.icon} {obj.category.name}"
    category_name.short_description = '업종'

    def rating_display(self, obj):
        if obj.rating:
            return format_html('⭐ {}', obj.rating)
        return '-'
    rating_display.short_description = '평점'

    def google_maps_link(self, obj):
        if obj.google_maps_url:
            return format_html('<a href="{}" target="_blank">Google 지도에서 보기</a>', obj.google_maps_url)
        return '-'
    google_maps_link.short_description = 'Google 지도'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('collect-businesses/', self.admin_site.admin_view(self.collect_businesses_view), name='collect_local_businesses'),
        ]
        return custom_urls + urls

    def collect_businesses_view(self, request):
        """데이터 수집 실행 페이지"""
        if request.method == 'POST':
            region = request.POST.get('region', '')
            category = request.POST.get('category', '')
            limit = request.POST.get('limit', '5')

            # AJAX 요청인지 확인
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            try:
                # 커맨드 실행
                out = io.StringIO()
                call_command(
                    'collect_local_businesses',
                    region=region if region else None,
                    category=category if category else None,
                    limit=int(limit),
                    stdout=out
                )

                output = out.getvalue()
                logs = output.split('\n')

                # 성공/실패 개수 계산
                success_count = sum(1 for log in logs if '✅' in log)
                fail_count = sum(1 for log in logs if '❌' in log)
                total_count = success_count + fail_count

                if is_ajax:
                    # AJAX 응답: JSON
                    from django.http import JsonResponse
                    return JsonResponse({
                        'status': 'completed',
                        'logs': logs,
                        'success': success_count,
                        'fail': fail_count,
                        'total': total_count,
                    })
                else:
                    # 일반 요청: 리다이렉트
                    self.message_user(request, f"데이터 수집 완료! 성공: {success_count}개, 실패: {fail_count}개", messages.SUCCESS)
                    return redirect('..')

            except Exception as e:
                if is_ajax:
                    from django.http import JsonResponse
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e),
                        'logs': [f'❌ 오류 발생: {str(e)}']
                    }, status=500)
                else:
                    self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)
                    return redirect('..')

        # GET 요청 시 폼 표시
        from django.template.response import TemplateResponse

        # 지역 목록 (하드코딩)
        TARGET_REGIONS = [
            '서울특별시 강남구', '서울특별시 서초구', '서울특별시 송파구',
            '서울특별시 강동구', '서울특별시 마포구',
            '경기도 성남시', '경기도 수원시', '경기도 고양시',
            '경기도 용인시', '경기도 화성시'
        ]
        regions = [{'name': region} for region in TARGET_REGIONS]

        # 카테고리 목록
        categories = LocalBusinessCategory.objects.filter(is_active=True).order_by('order_index')

        context = {
            **self.admin_site.each_context(request),
            'title': '지역 업체 정보 수집',
            'regions': regions,
            'categories': categories,
            'opts': self.model._meta,
        }

        return TemplateResponse(
            request,
            'admin/local_business_collect.html',
            context
        )

    def collect_region_businesses(self, request, queryset):
        """선택한 지역의 업체 수집"""
        # 선택된 업체들의 지역 추출
        regions = set(queryset.values_list('region_name', flat=True))

        if not regions:
            self.message_user(request, "지역을 선택해주세요.", messages.WARNING)
            return

        try:
            for region in regions:
                call_command('collect_local_businesses', region=region, limit=5)

            self.message_user(
                request,
                f"{len(regions)}개 지역의 업체 정보를 수집했습니다.",
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    collect_region_businesses.short_description = "🔄 선택한 지역의 업체 정보 다시 수집"

    def collect_all_businesses(self, request, queryset):
        """전체 업체 수집 (주의: API 비용 발생)"""
        if not request.POST.get('confirm'):
            self.message_user(
                request,
                "전체 수집은 API 비용이 발생합니다. 다시 한 번 실행하여 확인해주세요.",
                messages.WARNING
            )
            return

        try:
            call_command('collect_local_businesses', limit=5)
            self.message_user(request, "전체 지역 업체 정보를 수집했습니다.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"오류 발생: {str(e)}", messages.ERROR)

    collect_all_businesses.short_description = "⚠️ 전체 지역 업체 수집 (API 비용 주의)"

    def update_selected_businesses(self, request, queryset):
        """선택한 업체 정보만 업데이트"""
        count = queryset.count()
        if count > 20:
            self.message_user(
                request,
                f"한 번에 20개까지만 업데이트할 수 있습니다. (선택: {count}개)",
                messages.WARNING
            )
            return

        # TODO: 선택한 업체들의 Place ID로 API 호출하여 업데이트
        self.message_user(request, "개별 업체 업데이트 기능은 준비 중입니다.", messages.INFO)

    update_selected_businesses.short_description = "🔄 선택한 업체 정보 업데이트"

    def changelist_view(self, request, extra_context=None):
        """목록 페이지에 커스텀 버튼 추가"""
        extra_context = extra_context or {}
        extra_context['show_collect_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(LocalBusinessLink)
class LocalBusinessLinkAdmin(admin.ModelAdmin):
    list_display = ['business', 'link_type', 'title', 'source', 'published_at', 'created_at']
    list_filter = ['link_type', 'source']
    search_fields = ['business__name', 'title', 'url']
    ordering = ['-published_at', '-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business')


@admin.register(LocalBusinessView)
class LocalBusinessViewAdmin(admin.ModelAdmin):
    list_display = ['business', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['business__name', 'user__email', 'ip_address']
    ordering = ['-viewed_at']
    readonly_fields = ['business', 'user', 'ip_address', 'viewed_at']

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'user')
