# 추가 어드민 클래스들을 별도 파일로 관리
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Review, NoShowReport
from .models_remote_sales import RemoteSalesCertification


@admin.register(RemoteSalesCertification)
class RemoteSalesCertificationAdmin(admin.ModelAdmin):
    """비대면 판매 인증 관리"""
    list_display = ['id', 'seller_info', 'status_badge', 'submitted_at', 'reviewed_at', 'expires_at', 'display_certification', 'action_buttons']
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = ['seller__username', 'seller__email', 'seller__business_number', 'seller__nickname']
    readonly_fields = ['submitted_at', 'reviewed_at', 'approved_at', 'display_certification_preview', 'display_business_license_preview']
    date_hierarchy = 'submitted_at'
    list_per_page = 20
    
    fieldsets = (
        ('📋 신청 정보', {
            'fields': ('seller', 'submitted_at', 'status'),
            'description': '판매자가 제출한 비대면 판매 인증 신청 정보입니다.'
        }),
        ('📄 인증 서류', {
            'fields': ('certification_file', 'display_certification_preview', 'business_license_file', 'display_business_license_preview'),
            'description': '제출된 인증 서류를 확인하세요. 서류가 명확하고 유효한지 검토해주세요.'
        }),
        ('✅ 심사 정보', {
            'fields': ('reviewed_by', 'reviewed_at', 'approved_at', 'expires_at', 'rejection_reason', 'admin_notes'),
            'description': '승인 시 1년간 유효합니다. 거절 시 반드시 사유를 입력해주세요.'
        }),
    )
    
    def seller_info(self, obj):
        """판매자 정보 표시"""
        seller = obj.seller
        info = f"<strong>{seller.nickname or seller.username}</strong><br>"
        if hasattr(seller, 'business_number') and seller.business_number:
            info += f"<small>사업자번호: {seller.business_number}</small><br>"
        info += f"<small>{seller.email}</small>"
        return mark_safe(info)
    seller_info.short_description = '판매자 정보'
    
    def status_badge(self, obj):
        """상태를 배지로 표시"""
        colors = {
            'pending': '#FFA500',  # 주황색
            'approved': '#28A745',  # 녹색
            'rejected': '#DC3545',  # 빨간색
            'expired': '#6C757D',  # 회색
        }
        color = colors.get(obj.status, '#6C757D')
        return mark_safe(
            f'<span style="background-color: {color}; color: white; padding: 3px 8px; '
            f'border-radius: 3px; font-size: 11px; font-weight: bold;">'
            f'{obj.get_status_display()}</span>'
        )
    status_badge.short_description = '상태'
    
    def action_buttons(self, obj):
        """빠른 액션 버튼"""
        if obj.status == 'pending':
            return mark_safe(
                f'<a href="/admin/api/remotesalescertification/{obj.id}/change/" '
                f'class="button" style="padding: 5px 10px; background: #28A745; color: white; '
                f'text-decoration: none; border-radius: 3px; margin-right: 5px;">승인</a>'
                f'<a href="/admin/api/remotesalescertification/{obj.id}/change/" '
                f'class="button" style="padding: 5px 10px; background: #DC3545; color: white; '
                f'text-decoration: none; border-radius: 3px;">거절</a>'
            )
        elif obj.status == 'approved':
            if obj.expires_at:
                from django.utils import timezone
                days_left = (obj.expires_at - timezone.now()).days
                if days_left > 0:
                    return mark_safe(f'<small>만료까지 {days_left}일</small>')
                else:
                    return mark_safe('<small style="color: red;">만료됨</small>')
            return mark_safe('<small>승인됨</small>')
        return '-'
    action_buttons.short_description = '빠른 작업'
    
    def display_certification(self, obj):
        """어드민 목록에서 인증서 표시"""
        if obj.certification_file:
            return mark_safe(
                f'<a href="{obj.certification_file}" target="_blank" '
                f'style="color: #007BFF; text-decoration: none;">📄 보기</a>'
            )
        return "없음"
    display_certification.short_description = '인증서'
    
    def display_certification_preview(self, obj):
        """어드민 상세 페이지에서 인증서 미리보기"""
        if obj.certification_file:
            return mark_safe(f'<img src="{obj.certification_file}" width="600" />')
        return "인증서 없음"
    display_certification_preview.short_description = '인증서 미리보기'
    
    def display_business_license_preview(self, obj):
        """어드민 상세 페이지에서 사업자등록증 미리보기"""
        if obj.business_license_file:
            return mark_safe(f'<img src="{obj.business_license_file}" width="600" />')
        return "사업자등록증 없음"
    display_business_license_preview.short_description = '사업자등록증 미리보기'
    
    actions = ['approve_certifications', 'reject_certifications', 'check_expired']
    
    def approve_certifications(self, request, queryset):
        """선택한 인증 승인 (1년 유효)"""
        approved_count = 0
        already_processed = 0
        
        for cert in queryset:
            if cert.status == 'pending':
                cert.approve(request.user, expires_days=365)
                approved_count += 1
            else:
                already_processed += 1
        
        if approved_count > 0:
            self.message_user(request, f'✅ {approved_count}개의 인증이 승인되었습니다. (1년 유효)', level='SUCCESS')
        if already_processed > 0:
            self.message_user(request, f'⚠️ {already_processed}개는 이미 처리된 상태입니다.', level='WARNING')
    approve_certifications.short_description = '✅ 선택한 인증 승인 (1년 유효)'
    
    def reject_certifications(self, request, queryset):
        """선택한 인증 거절"""
        rejected_count = 0
        already_processed = 0
        
        for cert in queryset:
            if cert.status == 'pending':
                cert.reject(request.user, '서류 미비 또는 요건 불충족')
                rejected_count += 1
            else:
                already_processed += 1
        
        if rejected_count > 0:
            self.message_user(request, f'❌ {rejected_count}개의 인증이 거절되었습니다.', level='ERROR')
        if already_processed > 0:
            self.message_user(request, f'⚠️ {already_processed}개는 이미 처리된 상태입니다.', level='WARNING')
    reject_certifications.short_description = '❌ 선택한 인증 거절'
    
    def check_expired(self, request, queryset):
        """만료된 인증 확인"""
        from django.utils import timezone
        expired_count = 0
        
        for cert in queryset.filter(status='approved'):
            if cert.expires_at and cert.expires_at < timezone.now():
                cert.status = 'expired'
                cert.save()
                # 사용자 인증 상태도 업데이트
                cert.seller.remote_sales_verified = False
                cert.seller.save()
                expired_count += 1
        
        self.message_user(request, f'🕐 {expired_count}개의 만료된 인증을 처리했습니다.')
    check_expired.short_description = '🕐 만료된 인증 확인'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 심사 처리"""
        if change and 'status' in form.changed_data:
            # 이전 상태 확인
            old_status = RemoteSalesCertification.objects.get(pk=obj.pk).status
            
            # pending → approved: 승인 처리
            if old_status == 'pending' and obj.status == 'approved':
                if not obj.reviewed_by:
                    obj.approve(request.user, expires_days=365)
                    self.message_user(request, f'✅ {obj.seller.nickname or obj.seller.username}님의 비대면 판매 인증이 승인되었습니다.', level='SUCCESS')
            
            # pending → rejected: 거절 처리
            elif old_status == 'pending' and obj.status == 'rejected':
                if not obj.reviewed_by:
                    rejection_reason = form.cleaned_data.get('rejection_reason', '서류 미비 또는 요건 불충족')
                    obj.reject(request.user, rejection_reason)
                    self.message_user(request, f'❌ {obj.seller.nickname or obj.seller.username}님의 비대면 판매 인증이 거절되었습니다.', level='ERROR')
            
            # approved → expired: 만료 처리
            elif old_status == 'approved' and obj.status == 'expired':
                obj.seller.remote_sales_verified = False
                obj.seller.save()
                self.message_user(request, f'🕐 {obj.seller.nickname or obj.seller.username}님의 비대면 판매 인증이 만료 처리되었습니다.', level='WARNING')
        
        super().save_model(request, obj, form, change)


@admin.register(NoShowReport)
class NoShowReportAdmin(admin.ModelAdmin):
    """노쇼 신고 관리"""
    list_display = ['reporter', 'reported_user', 'groupbuy', 'report_type', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'report_type', 'created_at', 'processed_at']
    search_fields = ['reporter__username', 'reported_user__username', 'groupbuy__title', 'content']
    readonly_fields = ['created_at', 'processed_at', 'processed_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('신고 정보', {
            'fields': ('reporter', 'reported_user', 'groupbuy', 'report_type', 'content', 'created_at')
        }),
        ('증빙 자료', {
            'fields': ('evidence_image',)
        }),
        ('처리 정보', {
            'fields': ('status', 'admin_comment', 'processed_by', 'processed_at')
        }),
    )
    
    actions = ['confirm_reports', 'reject_reports']
    
    def confirm_reports(self, request, queryset):
        """선택한 신고 확인 처리"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'{updated}개의 신고가 확인 처리되었습니다.')
    confirm_reports.short_description = '선택한 신고 확인'
    
    def reject_reports(self, request, queryset):
        """선택한 신고 반려"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'{updated}개의 신고가 반려되었습니다.')
    reject_reports.short_description = '선택한 신고 반려'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 처리자 정보 업데이트"""
        if change and 'status' in form.changed_data:
            from django.utils import timezone
            if obj.status in ['confirmed', 'rejected'] and not obj.processed_by:
                obj.processed_by = request.user
                obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """리뷰 관리"""
    list_display = ['user', 'groupbuy', 'get_product', 'rating', 'created_at', 'get_is_visible', 'display_image']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'groupbuy__title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'groupbuy', 'rating')
        }),
        ('리뷰 내용', {
            'fields': ('content',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_product(self, obj):
        """공구의 상품명 표시"""
        return obj.groupbuy.product.name if obj.groupbuy.product else '-'
    get_product.short_description = '상품'
    
    def get_is_visible(self, obj):
        """표시 여부 (필드가 없는 경우 대비)"""
        return getattr(obj, 'is_visible', True)
    get_is_visible.short_description = '표시'
    get_is_visible.boolean = True
    
    def display_image(self, obj):
        """리뷰 이미지 (필드가 있는 경우)"""
        if hasattr(obj, 'image') and obj.image:
            return mark_safe(f'<img src="{obj.image}" width="50" height="50" />')
        return "없음"
    display_image.short_description = '이미지'
    
    actions = ['hide_reviews', 'show_reviews']
    
    def hide_reviews(self, request, queryset):
        """선택한 리뷰 숨기기 (is_visible 필드가 있는 경우)"""
        count = 0
        for review in queryset:
            if hasattr(review, 'is_visible'):
                review.is_visible = False
                review.save()
                count += 1
        self.message_user(request, f'{count}개의 리뷰가 숨겨졌습니다.')
    hide_reviews.short_description = '선택한 리뷰 숨기기'
    
    def show_reviews(self, request, queryset):
        """선택한 리뷰 표시 (is_visible 필드가 있는 경우)"""
        count = 0
        for review in queryset:
            if hasattr(review, 'is_visible'):
                review.is_visible = True
                review.save()
                count += 1
        self.message_user(request, f'{count}개의 리뷰가 표시되었습니다.')
    show_reviews.short_description = '선택한 리뷰 표시'