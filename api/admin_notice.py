"""
공지사항 어드민 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
from .models_notice import Notice, NoticeImage, NoticeComment


class NoticeImageInline(admin.TabularInline):
    """공지사항 이미지 인라인"""
    model = NoticeImage
    extra = 1
    fields = ['image', 'caption']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: auto;" />',
                obj.image.url
            )
        return "미리보기 없음"
    image_preview.short_description = "이미지 미리보기"


class NoticeAdminForm(forms.ModelForm):
    """공지사항 관리자 폼"""
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'vLargeTextField',
            'rows': 20,
            'cols': 100,
            'style': 'font-family: monospace; width: 100%;'
        }),
        help_text=mark_safe("""
            <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 4px;">
                <strong>HTML 에디터 사용법:</strong><br>
                • 제목: &lt;h1&gt;, &lt;h2&gt;, &lt;h3&gt;<br>
                • 단락: &lt;p&gt;텍스트&lt;/p&gt;<br>
                • 굵게: &lt;strong&gt;텍스트&lt;/strong&gt;<br>
                • 기울임: &lt;em&gt;텍스트&lt;/em&gt;<br>
                • 링크: &lt;a href="URL"&gt;텍스트&lt;/a&gt;<br>
                • 이미지: &lt;img src="URL" alt="설명" /&gt;<br>
                • 목록: &lt;ul&gt;&lt;li&gt;항목&lt;/li&gt;&lt;/ul&gt;<br>
                • 인용: &lt;blockquote&gt;텍스트&lt;/blockquote&gt;<br>
                • 구분선: &lt;hr /&gt;<br>
                • 테이블: &lt;table&gt;&lt;tr&gt;&lt;td&gt;셀&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;
            </div>
        """)
    )
    
    class Meta:
        model = Notice
        fields = '__all__'


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    """공지사항 관리자"""
    
    form = NoticeAdminForm
    list_display = [
        'id', 'category_badge', 'title_display', 'author',
        'is_pinned_display', 'is_published_display', 
        'view_count', 'published_at', 'created_at'
    ]
    list_filter = [
        'category', 'is_pinned', 'is_published',
        'created_at', 'published_at'
    ]
    search_fields = ['title', 'content', 'summary']
    readonly_fields = [
        'view_count', 'created_at', 'updated_at',
        'content_preview'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-is_pinned', '-created_at']
    inlines = [NoticeImageInline]
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'title', 'category', 'summary',
                ('is_pinned', 'is_published'),
                'published_at'
            )
        }),
        ('내용', {
            'fields': ('content', 'content_preview'),
            'classes': ('wide',)
        }),
        ('미디어', {
            'fields': ('thumbnail',),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('통계', {
            'fields': ('author', 'view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """저장 시 작성자 자동 설정"""
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def category_badge(self, obj):
        """카테고리 뱃지"""
        colors = {
            'general': '#6b7280',
            'event': '#10b981',
            'update': '#3b82f6',
            'maintenance': '#f59e0b',
            'important': '#ef4444',
        }
        color = colors.get(obj.category, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = "카테고리"
    
    def title_display(self, obj):
        """제목 표시"""
        if obj.is_new:
            return format_html(
                '{} <span style="color: #ef4444; font-weight: bold;">[NEW]</span>',
                obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
            )
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_display.short_description = "제목"
    
    def is_pinned_display(self, obj):
        """고정 상태 표시"""
        if obj.is_pinned:
            return format_html(
                '<span style="color: #ef4444;">📌 고정</span>'
            )
        return '-'
    is_pinned_display.short_description = "고정"
    
    def is_published_display(self, obj):
        """게시 상태 표시"""
        if obj.is_published:
            return format_html(
                '<span style="color: #10b981;">✅ 게시</span>'
            )
        return format_html(
            '<span style="color: #6b7280;">⏸ 미게시</span>'
        )
    is_published_display.short_description = "상태"
    
    def content_preview(self, obj):
        """내용 미리보기"""
        if obj.content:
            return format_html(
                '<div style="background: white; padding: 15px; border: 1px solid #e5e7eb; '
                'border-radius: 8px; margin-top: 10px;">'
                '<h4 style="margin-top: 0;">미리보기</h4>'
                '<div>{}</div>'
                '</div>',
                mark_safe(obj.content)
            )
        return "내용 없음"
    content_preview.short_description = "내용 미리보기"
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related('author').prefetch_related('images', 'comments')
    
    actions = ['make_published', 'make_unpublished', 'make_pinned', 'make_unpinned']
    
    def make_published(self, request, queryset):
        """선택한 공지사항 게시"""
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated}개의 공지사항이 게시되었습니다.')
    make_published.short_description = "선택한 공지사항 게시"
    
    def make_unpublished(self, request, queryset):
        """선택한 공지사항 미게시"""
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated}개의 공지사항이 미게시 처리되었습니다.')
    make_unpublished.short_description = "선택한 공지사항 미게시"
    
    def make_pinned(self, request, queryset):
        """선택한 공지사항 고정"""
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated}개의 공지사항이 고정되었습니다.')
    make_pinned.short_description = "선택한 공지사항 고정"
    
    def make_unpinned(self, request, queryset):
        """선택한 공지사항 고정 해제"""
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated}개의 공지사항이 고정 해제되었습니다.')
    make_unpinned.short_description = "선택한 공지사항 고정 해제"


@admin.register(NoticeComment)
class NoticeCommentAdmin(admin.ModelAdmin):
    """공지사항 댓글 관리자"""
    
    list_display = [
        'id', 'notice', 'author', 'content_preview',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['notice__title', 'author__username', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        """내용 미리보기"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = "내용"
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        """댓글 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 댓글이 활성화되었습니다.')
    make_active.short_description = "선택한 댓글 활성화"
    
    def make_inactive(self, request, queryset):
        """댓글 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 댓글이 비활성화되었습니다.')
    make_inactive.short_description = "선택한 댓글 비활성화"