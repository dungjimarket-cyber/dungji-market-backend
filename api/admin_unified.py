"""
통합 찜/후기 Django Admin 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from .models_unified_simple import UnifiedFavorite, UnifiedReview


@admin.register(UnifiedFavorite)
class UnifiedFavoriteAdmin(admin.ModelAdmin):
    """통합 찜 관리"""
    list_display = ['id', 'user', 'item_type_display', 'item_link', 'created_at']
    list_filter = ['item_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def item_type_display(self, obj):
        """상품 타입 표시"""
        if obj.item_type == 'phone':
            return format_html('<span style="color: #2196F3;">📱 휴대폰</span>')
        else:
            return format_html('<span style="color: #4CAF50;">🖥️ 전자제품</span>')
    item_type_display.short_description = '상품 타입'

    def item_link(self, obj):
        """상품 정보 및 링크"""
        item = obj.get_item()
        if item:
            if obj.item_type == 'phone':
                text = f"{item.brand} {item.model}"
                url = f"/admin/used_phones/usedphone/{item.id}/change/"
            else:
                text = f"{item.brand} {item.model_name}"
                url = f"/admin/used_electronics/usedelectronics/{item.id}/change/"

            return format_html(
                '<a href="{}" target="_blank">{} (#{}) - {:,}원</a>',
                url, text, item.id, item.price
            )
        return f"#{obj.item_id} (삭제된 상품)"
    item_link.short_description = '상품 정보'

    def get_queryset(self, request):
        """쿼리 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(UnifiedReview)
class UnifiedReviewAdmin(admin.ModelAdmin):
    """통합 후기 관리"""
    list_display = ['id', 'item_type_display', 'reviewer', 'reviewee', 'rating_display',
                   'comment_preview', 'buyer_seller_type', 'created_at']
    list_filter = ['item_type', 'rating', 'is_from_buyer', 'created_at']
    search_fields = ['reviewer__username', 'reviewee__username', 'comment']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'transaction_info']
    ordering = ['-created_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('item_type', 'transaction_id', 'transaction_info')
        }),
        ('평가', {
            'fields': ('reviewer', 'reviewee', 'rating', 'comment', 'is_from_buyer')
        }),
        ('추가 평가 항목', {
            'fields': ('is_punctual', 'is_friendly', 'is_honest', 'is_fast_response'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def item_type_display(self, obj):
        """상품 타입 표시"""
        if obj.item_type == 'phone':
            return format_html('<span style="color: #2196F3;">📱 휴대폰</span>')
        else:
            return format_html('<span style="color: #4CAF50;">🖥️ 전자제품</span>')
    item_type_display.short_description = '상품 타입'

    def rating_display(self, obj):
        """평점 별표 표시"""
        stars = '⭐' * obj.rating + '☆' * (5 - obj.rating)
        color_map = {5: '#4CAF50', 4: '#8BC34A', 3: '#FFC107', 2: '#FF9800', 1: '#F44336'}
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span> <b>{}</b>점',
            color_map.get(obj.rating, '#000'), stars, obj.rating
        )
    rating_display.short_description = '평점'

    def comment_preview(self, obj):
        """후기 내용 미리보기"""
        if len(obj.comment) > 50:
            return obj.comment[:50] + "..."
        return obj.comment
    comment_preview.short_description = '후기 내용'

    def buyer_seller_type(self, obj):
        """구매자/판매자 구분"""
        if obj.is_from_buyer:
            return format_html('<span style="color: #2196F3;">구매자 → 판매자</span>')
        else:
            return format_html('<span style="color: #FF9800;">판매자 → 구매자</span>')
    buyer_seller_type.short_description = '후기 방향'

    def transaction_info(self, obj):
        """거래 정보 표시"""
        transaction = obj.get_transaction()
        if transaction:
            if obj.item_type == 'phone':
                item = transaction.phone
                text = f"{item.brand} {item.model} ({item.storage})"
                url = f"/admin/used_phones/usedphonetransaction/{transaction.id}/change/"
            else:
                item = transaction.electronics
                text = f"{item.brand} {item.model_name}"
                url = f"/admin/used_electronics/electronicstransaction/{transaction.id}/change/"

            return format_html(
                '<a href="{}" target="_blank">거래 #{} - {} ({:,}원)</a>',
                url, transaction.id, text, transaction.final_price
            )
        return f"거래 #{obj.transaction_id} (정보 없음)"
    transaction_info.short_description = '거래 정보'

    def get_queryset(self, request):
        """쿼리 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related('reviewer', 'reviewee')


# Admin 사이트 헤더 커스터마이징 (선택사항)
admin.site.site_header = "둥지마켓 관리"
admin.site.site_title = "둥지마켓"
admin.site.index_title = "관리자 페이지"