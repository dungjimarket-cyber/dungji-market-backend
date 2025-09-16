"""
팝업 관리자
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models_popup import Popup


@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
    """팝업 관리자"""
    
    list_display = [
        'id', 'title_display', 'popup_type_badge', 'is_active_display',
        'priority', 'period_display', 'statistics_display', 
        'author', 'created_at'
    ]
    
    list_filter = [
        'is_active', 'popup_type', 'show_on_main', 'show_on_groupbuy_list',
        'show_on_groupbuy_detail', 'show_on_used_list', 'show_on_used_detail',
        'show_on_mypage', 'show_on_mobile',
        'start_date', 'end_date', 'created_at'
    ]
    
    search_fields = ['title', 'content', 'link_url']
    
    readonly_fields = [
        'view_count', 'click_count', 'created_at', 'updated_at',
        'image_preview', 'statistics_chart'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'is_active', 'priority', 'author')
        }),
        ('팝업 내용', {
            'fields': (
                'popup_type', 'content', 'image', 'image_preview',
                'link_url', 'link_target'
            )
        }),
        ('페이지별 표시 설정', {
            'fields': (
                ('show_on_main', 'show_on_mypage'),
                ('show_on_groupbuy_list', 'show_on_groupbuy_detail'),
                ('show_on_used_list', 'show_on_used_detail'),
                'show_on_mobile'
            ),
            'description': '팝업을 표시할 페이지를 선택하세요. 여러 페이지 동시 선택 가능.'
        }),
        ('표시 위치 및 크기', {
            'fields': (
                'position', 'position_x', 'position_y',
                'width', 'height'
            ),
            'classes': ('collapse',)
        }),
        ('표시 기간', {
            'fields': ('start_date', 'end_date')
        }),
        ('사용자 옵션', {
            'fields': ('show_today_close', 'show_week_close')
        }),
        ('구버전 설정 (사용하지 마세요)', {
            'fields': ('show_pages', 'exclude_pages'),
            'classes': ('collapse',),
            'description': '⚠️ 구버전 호환용입니다. 위의 체크박스를 사용하세요.'
        }),
        ('통계', {
            'fields': ('view_count', 'click_count', 'statistics_chart'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_popups', 'deactivate_popups', 'duplicate_popup']
    
    def save_model(self, request, obj, form, change):
        """저장 시 작성자 자동 설정"""
        if not change:  # 새로 생성하는 경우
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def title_display(self, obj):
        """제목 표시"""
        status_icon = '🟢' if obj.is_active else '🔴'
        return format_html(
            '{} <strong>{}</strong>',
            status_icon,
            obj.title
        )
    title_display.short_description = '제목'
    
    def popup_type_badge(self, obj):
        """팝업 타입 배지"""
        colors = {
            'image': 'purple',
            'text': 'blue',
            'mixed': 'green'
        }
        color = colors.get(obj.popup_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_popup_type_display()
        )
    popup_type_badge.short_description = '타입'
    
    def is_active_display(self, obj):
        """활성화 상태 표시"""
        if obj.is_active:
            if obj.is_valid_period():
                return format_html(
                    '<span style="color: green;">✅ 활성</span>'
                )
            else:
                return format_html(
                    '<span style="color: orange;">⏰ 기간 외</span>'
                )
        return format_html(
            '<span style="color: red;">❌ 비활성</span>'
        )
    is_active_display.short_description = '상태'
    
    def period_display(self, obj):
        """표시 기간"""
        now = timezone.now()
        
        if obj.end_date:
            if obj.end_date < now:
                status = '종료됨'
                color = 'red'
            elif obj.start_date > now:
                status = '예정'
                color = 'blue'
            else:
                remaining = obj.end_date - now
                if remaining.days > 0:
                    status = f'{remaining.days}일 남음'
                else:
                    hours = remaining.seconds // 3600
                    status = f'{hours}시간 남음'
                color = 'green'
                
            return format_html(
                '<span style="color: {};">{}<br/>'
                '<small>{} ~ {}</small></span>',
                color,
                status,
                obj.start_date.strftime('%Y-%m-%d'),
                obj.end_date.strftime('%Y-%m-%d')
            )
        else:
            return format_html(
                '<span style="color: green;">무제한<br/>'
                '<small>{} ~</small></span>',
                obj.start_date.strftime('%Y-%m-%d')
            )
    period_display.short_description = '표시 기간'
    
    def statistics_display(self, obj):
        """통계 표시"""
        if obj.view_count > 0:
            ctr = (obj.click_count / obj.view_count) * 100
        else:
            ctr = 0
            
        return format_html(
            '👁 {}<br/>👆 {}<br/>'
            '<small>CTR: {}%</small>',
            obj.view_count,
            obj.click_count,
            f'{ctr:.1f}'
        )
    statistics_display.short_description = '통계'
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = '이미지 미리보기'
    
    def statistics_chart(self, obj):
        """통계 차트"""
        if obj.view_count > 0:
            ctr = (obj.click_count / obj.view_count) * 100
            return format_html(
                '<div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">'
                '<div>조회수: <strong>{}</strong></div>'
                '<div>클릭수: <strong>{}</strong></div>'
                '<div>클릭률: <strong>{}%</strong></div>'
                '<div style="margin-top: 10px;">'
                '<div style="background: #ddd; height: 20px; border-radius: 3px;">'
                '<div style="background: #4CAF50; height: 100%; width: {}%; border-radius: 3px;"></div>'
                '</div>'
                '</div>'
                '</div>',
                obj.view_count,
                obj.click_count,
                f'{ctr:.1f}',
                min(ctr, 100)
            )
        return '통계 없음'
    statistics_chart.short_description = '통계 차트'
    
    def activate_popups(self, request, queryset):
        """선택한 팝업 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 팝업을 활성화했습니다.')
    activate_popups.short_description = '선택한 팝업 활성화'
    
    def deactivate_popups(self, request, queryset):
        """선택한 팝업 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 팝업을 비활성화했습니다.')
    deactivate_popups.short_description = '선택한 팝업 비활성화'
    
    def duplicate_popup(self, request, queryset):
        """팝업 복제"""
        for popup in queryset:
            popup.pk = None
            popup.title = f"{popup.title} (복사본)"
            popup.is_active = False
            popup.view_count = 0
            popup.click_count = 0
            popup.save()
        self.message_user(request, f'{queryset.count()}개의 팝업을 복제했습니다.')
    duplicate_popup.short_description = '선택한 팝업 복제'