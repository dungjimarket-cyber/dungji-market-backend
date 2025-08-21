from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import (
    Category, Product, GroupBuy, Bid, Penalty, User, Badge,
    TelecomProductDetail, ElectronicsProductDetail, RentalProductDetail,
    SubscriptionProductDetail, StandardProductDetail, ProductCustomField,
    ProductCustomValue, ParticipantConsent, PhoneVerification, Banner, Event,
    Review, NoShowReport, BidToken, BidTokenPurchase, BidTokenAdjustmentLog
)
from .models_verification import BusinessNumberVerification
from .models_inquiry import Inquiry
from .models_partner import Partner, ReferralRecord, PartnerSettlement, PartnerLink, PartnerNotification
from django.utils.html import mark_safe
from django.conf import settings
import logging
from .views_auth import kakao_unlink
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
from django.http import HttpResponseRedirect

# 추가 어드민 클래스들 import (RemoteSalesCertification 포함)
from .admin_extra import *

logger = logging.getLogger(__name__)

# 설정 확인 로깅
logger.info(f"Admin 로드 시 USE_S3: {settings.USE_S3}")
logger.info(f"Admin 로드 시 DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")

# Admin 사이트 타이틀 한글화
AdminSite.site_header = '둥지마켓 관리자'
AdminSite.site_title = '둥지마켓 관리자 포털'
AdminSite.index_title = '둥지마켓 관리자 대시보드'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'detail_type']
    list_filter = ['detail_type', 'is_service']
    search_fields = ['name']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('name',)
        super().__init__(model, admin_site)
    
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        for action in perms:
            perms[action] = perms[action]
        return perms

@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'reason', 'start_date']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)

from .forms import UserCreationForm, UserChangeForm
from django.utils import timezone
from django.db.models import Count, Q
from django import forms

# BidToken 관련 인라인 Admin
class BidTokenInline(admin.TabularInline):
    model = BidToken
    extra = 0
    fields = ['token_type', 'status', 'expires_at', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    max_num = 10  # 최대 10개만 표시
    
    def get_queryset(self, request):
        # 최근 생성된 것부터 정렬 (슬라이싱 제거로 Django admin 오류 방지)
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')

class BidTokenAdjustmentLogInline(admin.TabularInline):
    model = BidTokenAdjustmentLog
    fk_name = 'seller'  # seller 필드를 기준으로 인라인 표시
    extra = 0
    fields = ['adjustment_type', 'quantity', 'reason', 'admin', 'created_at']
    readonly_fields = ['adjustment_type', 'quantity', 'reason', 'admin', 'created_at']
    can_delete = False
    max_num = 10  # 최대 10개만 표시
    
    def get_queryset(self, request):
        # 최근 생성된 것부터 정렬 (슬라이싱 제거로 Django admin 오류 방지)
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    list_display = ['get_user_id', 'nickname', 'email', 'role', 'get_sns_type', 'is_business_verified', 'get_bid_tokens_count', 'get_subscription_status', 'display_business_reg_file']
    list_filter = ['role', 'sns_type', 'is_active', 'is_staff', 'is_business_verified']
    search_fields = ['username', 'email', 'business_number', 'nickname']
    ordering = ['username']
    readonly_fields = ('display_business_reg_file_preview', 'sns_type', 'sns_id', 'get_bid_tokens_summary', 'get_adjustment_history', 'get_quick_token_adjustment')
    
    def get_user_id(self, obj):
        """사용자 아이디 표시 - SNS 사용자는 실제 SNS ID, 일반 사용자는 username"""
        if obj.sns_type and obj.sns_id:
            # 카카오나 구글 사용자의 경우 sns_type + sns_id 형태로 표시
            return f"{obj.sns_type}_{obj.sns_id}"
        # 일반 이메일 가입자나 sns_id가 없는 경우 username 사용
        return obj.username
    get_user_id.short_description = '아이디'
    get_user_id.admin_order_field = 'username'
    
    def get_sns_type(self, obj):
        """가입 유형 표시"""
        if obj.sns_type == 'kakao':
            return mark_safe('<span style="color: #FEE500; background: #3C1E1E; padding: 2px 8px; border-radius: 4px;">카카오</span>')
        elif obj.sns_type == 'google':
            return mark_safe('<span style="color: #4285F4; background: #F1F3F4; padding: 2px 8px; border-radius: 4px;">구글</span>')
        elif obj.sns_type == 'email':
            return mark_safe('<span style="color: #666; background: #F5F5F5; padding: 2px 8px; border-radius: 4px;">이메일</span>')
        return obj.sns_type or '직접가입'
    get_sns_type.short_description = '가입유형'
    get_sns_type.admin_order_field = 'sns_type'
    
    def get_bid_tokens_count(self, obj):
        """활성 입찰권 수 표시"""
        if obj.role != 'seller':
            return '-'
        count = BidToken.objects.filter(
            seller=obj,
            status='active',
            token_type='single'
        ).count()
        if count > 0:
            return mark_safe(f'<span style="color: green; font-weight: bold;">{count}개</span>')
        return mark_safe('<span style="color: gray;">0개</span>')
    get_bid_tokens_count.short_description = '입찰권'
    
    def get_subscription_status(self, obj):
        """구독권 상태 표시"""
        if obj.role != 'seller':
            return '-'
        active_subscription = BidToken.objects.filter(
            seller=obj,
            token_type='unlimited',
            status='active',
            expires_at__gt=timezone.now()
        ).first()
        if active_subscription:
            days_left = (active_subscription.expires_at - timezone.now()).days
            return mark_safe(f'<span style="color: blue; font-weight: bold;">활성 ({days_left}일 남음)</span>')
        return mark_safe('<span style="color: gray;">없음</span>')
    get_subscription_status.short_description = '구독권'
    
    def get_bid_tokens_summary(self, obj):
        """입찰권 상세 요약"""
        if obj.role != 'seller':
            return '판매회원이 아닙니다'
        
        active_single = BidToken.objects.filter(
            seller=obj, status='active', token_type='single'
        ).count()
        
        used_tokens = BidToken.objects.filter(
            seller=obj, status='used'
        ).count()
        
        active_subscription = BidToken.objects.filter(
            seller=obj,
            token_type='unlimited',
            status='active',
            expires_at__gt=timezone.now()
        ).first()
        
        summary = f"""
        <div style="line-height: 1.8;">
            <strong>입찰권 현황:</strong><br>
            • 활성 입찰권: {active_single}개<br>
            • 사용된 입찰권: {used_tokens}개<br>
            • 구독권: {'활성' if active_subscription else '없음'}
        """
        
        if active_subscription:
            summary += f"<br>• 구독권 만료일: {active_subscription.expires_at.strftime('%Y-%m-%d %H:%M')}"
        
        summary += "</div>"
        return mark_safe(summary)
    get_bid_tokens_summary.short_description = '입찰권 요약'
    
    def get_adjustment_history(self, obj):
        """최근 조정 이력"""
        if obj.role != 'seller':
            return '판매회원이 아닙니다'
        
        recent_logs = BidTokenAdjustmentLog.objects.filter(
            seller=obj
        ).order_by('-created_at')[:5]
        
        if not recent_logs:
            return '조정 이력 없음'
        
        history = '<div style="line-height: 1.6;">'
        history += '<strong>최근 조정 이력:</strong><br>'
        for log in recent_logs:
            adjustment_type = {'add': '추가', 'subtract': '차감', 'grant_subscription': '구독권'}.get(log.adjustment_type, log.adjustment_type)
            history += f"• {log.created_at.strftime('%Y-%m-%d')} - {adjustment_type} {log.quantity}{'일' if log.adjustment_type == 'grant_subscription' else '개'} (사유: {log.reason[:20]}...)<br>"
        history += '</div>'
        
        return mark_safe(history)
    get_adjustment_history.short_description = '최근 조정 이력'
    
    def get_quick_token_adjustment(self, obj):
        """빠른 견적 티켓 조정 인터페이스"""
        if obj.role != 'seller':
            return '판매회원이 아닙니다'
        
        current_tokens = BidToken.objects.filter(
            seller=obj,
            status='active',
            token_type='single'
        ).count()
        
        quick_actions = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
            <div style="margin-bottom: 15px;">
                <strong>현재 활성 견적 티켓: {current_tokens}개</strong>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-bottom: 15px;">
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'add', 1)" 
                        style="background: #28A745; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    +1개
                </button>
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'add', 5)" 
                        style="background: #28A745; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    +5개
                </button>
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'add', 10)" 
                        style="background: #28A745; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    +10개
                </button>
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'subtract', 1)" 
                        style="background: #DC3545; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    -1개
                </button>
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'subtract', 5)" 
                        style="background: #DC3545; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    -5개
                </button>
                <button type="button" onclick="quickAdjustTokens({obj.id}, 'set', 0)" 
                        style="background: #6C757D; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    모두 제거
                </button>
            </div>
            
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <input type="number" id="custom-tokens-{obj.id}" min="0" max="100" placeholder="개수" 
                       style="width: 80px; padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;">
                <button type="button" onclick="customAdjustTokens({obj.id})" 
                        style="background: #007BFF; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    개수 설정
                </button>
                <input type="text" id="custom-reason-{obj.id}" placeholder="조정 사유" 
                       style="flex: 1; min-width: 150px; padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;">
            </div>
            
            <div id="token-status-{obj.id}" style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; font-size: 12px; display: none;"></div>
        </div>
        
        <script>
        function quickAdjustTokens(sellerId, type, quantity) {{
            const reason = prompt('조정 사유를 입력해주세요:', type === 'add' ? '관리자 추가' : type === 'subtract' ? '관리자 차감' : '관리자 설정');
            if (!reason) return;
            
            adjustTokensAjax(sellerId, type, quantity, reason);
        }}
        
        function customAdjustTokens(sellerId) {{
            const quantity = document.getElementById('custom-tokens-' + sellerId).value;
            const reason = document.getElementById('custom-reason-' + sellerId).value;
            
            if (!quantity || !reason) {{
                alert('개수와 사유를 모두 입력해주세요.');
                return;
            }}
            
            adjustTokensAjax(sellerId, 'set', parseInt(quantity), reason);
        }}
        
        function adjustTokensAjax(sellerId, type, quantity, reason) {{
            const statusDiv = document.getElementById('token-status-' + sellerId);
            statusDiv.style.display = 'block';
            statusDiv.innerHTML = '처리 중...';
            statusDiv.style.background = '#fff3cd';
            
            // Django admin의 CSRF 토큰 가져오기
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
            
            console.log('요청 정보:', {{
                url: '/api/admin/user/' + sellerId + '/adjust-tokens/',
                sellerId: sellerId,
                type: type,
                quantity: quantity,
                csrfToken: csrfToken
            }});
            
            // 전체 URL 구성 (프로덕션 환경 고려) - API 경로 사용
            const baseUrl = window.location.origin;
            const adjustUrl = baseUrl + '/api/admin/user/' + sellerId + '/adjust-tokens/';
            
            console.log('전체 요청 URL:', adjustUrl);
            
            fetch(adjustUrl, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }},
                credentials: 'same-origin',
                body: JSON.stringify({{
                    adjustment_type: type,
                    quantity: quantity,
                    reason: reason
                }})
            }})
            .then(response => {{
                console.log('응답 상태:', response.status);
                console.log('응답 헤더 Content-Type:', response.headers.get('content-type'));
                
                // Content-Type 확인
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {{
                    throw new Error(`서버가 JSON이 아닌 응답을 반환했습니다. Content-Type: ${{contentType}}`);
                }}
                
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                return response.json();
            }})
            .then(data => {{
                console.log('응답 데이터:', data);
                if (data.success) {{
                    statusDiv.innerHTML = data.message + ' (현재: ' + data.current_tokens + '개)';
                    statusDiv.style.background = '#d4edda';
                    // 페이지 새로고침
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    statusDiv.innerHTML = '오류: ' + data.error;
                    statusDiv.style.background = '#f8d7da';
                }}
            }})
            .catch(error => {{
                console.error('에러 발생:', error);
                statusDiv.innerHTML = '처리 중 오류가 발생했습니다: ' + error.message;
                statusDiv.style.background = '#f8d7da';
            }});
        }}
        
        function getCookie(name) {{
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {{
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {{
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }}
                }}
            }}
            return cookieValue;
        }}
        </script>
        """
        
        return mark_safe(quick_actions)
    get_quick_token_adjustment.short_description = '빠른 견적 티켓 조정'
    
    def display_business_reg_file(self, obj):
        """어드민 목록에서 사업자등록증 표시"""
        if obj.business_license_image:
            return mark_safe(f'<a href="{obj.business_license_image}" target="_blank">보기</a>')
        return "없음"
    display_business_reg_file.short_description = '사업자등록증'
    
    def display_business_reg_file_preview(self, obj):
        """어드민 상세 페이지에서 사업자등록증 미리보기"""
        if obj.business_license_image:
            # URL 형태이므로 이미지로 처리
            return mark_safe(f'<img src="{obj.business_license_image}" width="400" />')
        return "사업자등록증 없음"
    display_business_reg_file_preview.short_description = '사업자등록증 미리보기'
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'role', 'password')}),
        ('가입정보', {'fields': ('sns_type', 'sns_id')}),
        ('개인정보', {'fields': ('nickname', 'phone_number', 'address_region')}),
        ('사업자정보', {'fields': ('business_number', 'business_license_image', 'display_business_reg_file_preview', 'is_business_verified', 'is_remote_sales')}),
        ('입찰권 관리', {'fields': ('get_bid_tokens_summary', 'get_quick_token_adjustment', 'get_adjustment_history')}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('중요 날짜', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')
    inlines = [BidTokenInline, BidTokenAdjustmentLogInline]
    actions = ['add_5_bid_tokens', 'add_10_bid_tokens', 'grant_7day_subscription', 'grant_30day_subscription', 'approve_business_verification', 'custom_adjust_bid_tokens', 'remove_bid_tokens', 'reset_bid_tokens']

    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('get_user_id',)
        super().__init__(model, admin_site)
    
    def get_fieldsets(self, request, obj=None):
        """사용자 역할에 따라 다른 fieldsets 표시"""
        if obj and obj.role == 'seller':
            # 판매자용 fieldsets (입찰권 관리 포함)
            return (
                (None, {'fields': ('username', 'email', 'role', 'password')}),
                ('가입정보', {'fields': ('sns_type', 'sns_id')}),
                ('개인정보', {'fields': ('nickname', 'phone_number', 'address_region')}),
                ('사업자정보', {'fields': ('business_number', 'business_license_image', 'display_business_reg_file_preview', 'is_business_verified', 'is_remote_sales')}),
                ('입찰권 관리', {'fields': ('get_bid_tokens_summary', 'get_quick_token_adjustment', 'get_adjustment_history')}),
                ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                ('중요 날짜', {'fields': ('last_login', 'date_joined')}),
            )
        else:
            # 일반 사용자용 fieldsets (입찰권 관리 제외)
            return (
                (None, {'fields': ('username', 'email', 'role', 'password')}),
                ('가입정보', {'fields': ('sns_type', 'sns_id')}),
                ('개인정보', {'fields': ('nickname', 'phone_number', 'address_region')}),
                ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                ('중요 날짜', {'fields': ('last_login', 'date_joined')}),
            )
    
    def get_inlines(self, request, obj):
        """판매회원인 경우에만 BidToken 관련 인라인 표시"""
        if obj and obj.role == 'seller':
            return self.inlines
        return []
    
    # 대량 액션들
    def add_5_bid_tokens(self, request, queryset):
        """선택한 판매회원들에게 입찰권 5개 추가"""
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 입찰권 5개 생성
            for _ in range(5):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='add',
                quantity=5,
                reason='관리자 대량 추가 (5개)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 입찰권 5개씩 추가했습니다.')
    add_5_bid_tokens.short_description = '선택한 판매회원에게 입찰권 5개 추가'
    
    def add_10_bid_tokens(self, request, queryset):
        """선택한 판매회원들에게 입찰권 10개 추가"""
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 입찰권 10개 생성
            for _ in range(10):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='add',
                quantity=10,
                reason='관리자 대량 추가 (10개)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 입찰권 10개씩 추가했습니다.')
    add_10_bid_tokens.short_description = '선택한 판매회원에게 입찰권 10개 추가'
    
    def grant_7day_subscription(self, request, queryset):
        """선택한 판매회원들에게 7일 구독권 부여"""
        from datetime import timedelta
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 기존 구독권 만료
            BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active'
            ).update(status='expired')
            
            # 새 구독권 생성
            expires_at = timezone.now() + timedelta(days=7)
            BidToken.objects.create(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at=expires_at
            )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='grant_subscription',
                quantity=7,
                reason='관리자 대량 부여 (7일)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 7일 구독권을 부여했습니다.')
    grant_7day_subscription.short_description = '선택한 판매회원에게 7일 구독권 부여'
    
    def grant_30day_subscription(self, request, queryset):
        """선택한 판매회원들에게 30일 구독권 부여"""
        from datetime import timedelta
        sellers = queryset.filter(role='seller')
        count = 0
        for seller in sellers:
            # 기존 구독권 만료
            BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active'
            ).update(status='expired')
            
            # 새 구독권 생성
            expires_at = timezone.now() + timedelta(days=30)
            BidToken.objects.create(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at=expires_at
            )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='grant_subscription',
                quantity=30,
                reason='관리자 대량 부여 (30일)'
            )
            count += 1
        self.message_user(request, f'{count}명의 판매회원에게 30일 구독권을 부여했습니다.')
    grant_30day_subscription.short_description = '선택한 판매회원에게 30일 구독권 부여'
    
    def approve_business_verification(self, request, queryset):
        """선택한 판매회원들의 사업자 인증 승인"""
        sellers = queryset.filter(role='seller', is_business_verified=False)
        count = sellers.update(is_business_verified=True)
        self.message_user(request, f'{count}명의 판매회원 사업자 인증을 승인했습니다.')
    approve_business_verification.short_description = '선택한 판매회원 사업자 인증 승인'
    
    def custom_adjust_bid_tokens(self, request, queryset):
        """선택한 판매회원들의 견적 티켓 개별 조정"""
        from django import forms
        from django.template.response import TemplateResponse
        
        class BidTokenAdjustmentForm(forms.Form):
            adjustment_type = forms.ChoiceField(
                choices=[
                    ('add', '티켓 추가'),
                    ('subtract', '티켓 차감'),
                    ('set', '티켓 개수 설정'),
                ],
                label='조정 유형',
                initial='add'
            )
            quantity = forms.IntegerField(
                min_value=0,
                max_value=100,
                initial=1,
                label='수량',
                help_text='추가/차감할 티켓 수량 또는 설정할 총 티켓 수량'
            )
            reason = forms.CharField(
                max_length=200,
                required=True,
                label='조정 사유',
                help_text='티켓 조정 사유를 입력해주세요'
            )
        
        # POST 요청 (폼 제출)
        if request.method == 'POST':
            form = BidTokenAdjustmentForm(request.POST)
            if form.is_valid():
                adjustment_type = form.cleaned_data['adjustment_type']
                quantity = form.cleaned_data['quantity']
                reason = form.cleaned_data['reason']
                
                sellers = queryset.filter(role='seller')
                adjusted_count = 0
                
                for seller in sellers:
                    current_tokens = BidToken.objects.filter(
                        seller=seller,
                        status='active',
                        token_type='single'
                    ).count()
                    
                    if adjustment_type == 'add':
                        # 티켓 추가
                        for _ in range(quantity):
                            BidToken.objects.create(
                                seller=seller,
                                token_type='single',
                                status='active'
                            )
                        adjusted_count += 1
                        
                    elif adjustment_type == 'subtract':
                        # 티켓 차감
                        tokens_to_remove = BidToken.objects.filter(
                            seller=seller,
                            status='active',
                            token_type='single'
                        ).order_by('created_at')[:quantity]
                        
                        for token in tokens_to_remove:
                            token.status = 'expired'
                            token.expires_at = timezone.now()
                            token.save()
                        adjusted_count += 1
                        
                    elif adjustment_type == 'set':
                        # 티켓 개수 설정
                        if quantity > current_tokens:
                            # 부족한 만큼 추가
                            for _ in range(quantity - current_tokens):
                                BidToken.objects.create(
                                    seller=seller,
                                    token_type='single',
                                    status='active'
                                )
                        elif quantity < current_tokens:
                            # 초과한 만큼 제거
                            tokens_to_remove = BidToken.objects.filter(
                                seller=seller,
                                status='active',
                                token_type='single'
                            ).order_by('created_at')[:current_tokens - quantity]
                            
                            for token in tokens_to_remove:
                                token.status = 'expired'
                                token.expires_at = timezone.now()
                                token.save()
                        adjusted_count += 1
                    
                    # 조정 이력 기록
                    BidTokenAdjustmentLog.objects.create(
                        seller=seller,
                        admin=request.user,
                        adjustment_type=adjustment_type,
                        quantity=quantity,
                        reason=reason
                    )
                
                self.message_user(request, f'{adjusted_count}명의 판매회원 견적 티켓이 조정되었습니다.')
                return None
        else:
            # GET 요청 (폼 표시)
            form = BidTokenAdjustmentForm()
        
        # 선택된 판매회원 정보
        sellers = queryset.filter(role='seller')
        seller_info = []
        for seller in sellers:
            current_tokens = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            ).count()
            seller_info.append({
                'seller': seller,
                'current_tokens': current_tokens
            })
        
        context = {
            'form': form,
            'seller_info': seller_info,
            'action_name': '견적 티켓 개별 조정',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/bid_token_adjustment_form.html', context)
    custom_adjust_bid_tokens.short_description = '견적 티켓 개별 조정'
    
    def remove_bid_tokens(self, request, queryset):
        """선택한 판매회원들의 모든 활성 견적 티켓 제거"""
        sellers = queryset.filter(role='seller')
        total_removed = 0
        
        for seller in sellers:
            # 활성 상태인 단일 티켓들을 만료 처리
            active_tokens = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            )
            count = active_tokens.count()
            active_tokens.update(
                status='expired',
                expires_at=timezone.now()
            )
            total_removed += count
            
            # 조정 이력 기록
            if count > 0:
                BidTokenAdjustmentLog.objects.create(
                    seller=seller,
                    admin=request.user,
                    adjustment_type='subtract',
                    quantity=count,
                    reason='관리자에 의한 모든 티켓 제거'
                )
        
        self.message_user(request, f'{sellers.count()}명의 판매회원에서 총 {total_removed}개의 견적 티켓이 제거되었습니다.')
    remove_bid_tokens.short_description = '모든 견적 티켓 제거'
    
    def reset_bid_tokens(self, request, queryset):
        """선택한 판매회원들의 견적 티켓을 10개로 초기화"""
        sellers = queryset.filter(role='seller')
        
        for seller in sellers:
            # 기존 활성 티켓 모두 만료 처리
            active_tokens = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            )
            removed_count = active_tokens.count()
            active_tokens.update(
                status='expired',
                expires_at=timezone.now()
            )
            
            # 새로 10개 생성
            for _ in range(10):
                BidToken.objects.create(
                    seller=seller,
                    token_type='single',
                    status='active'
                )
            
            # 조정 이력 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type='set',
                quantity=10,
                reason=f'관리자에 의한 티켓 초기화 (기존 {removed_count}개 → 10개)'
            )
        
        self.message_user(request, f'{sellers.count()}명의 판매회원 견적 티켓이 10개로 초기화되었습니다.')
    reset_bid_tokens.short_description = '견적 티켓 10개로 초기화'
    
    def delete_model(self, request, obj):
        """개별 사용자 삭제 시 카카오 연결 해제"""
        if obj.sns_type == 'kakao' and obj.sns_id:
            kakao_unlink_success = kakao_unlink(obj.sns_id)
            if not kakao_unlink_success:
                logger.warning(f"관리자 삭제: 카카오 연결 끊기 실패했지만 삭제는 진행합니다. User ID: {obj.id}")
            else:
                logger.info(f"관리자 삭제: 카카오 연결 끊기 성공. User ID: {obj.id}")
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """다중 사용자 삭제 시 카카오 연결 해제"""
        for user in queryset:
            if user.sns_type == 'kakao' and user.sns_id:
                kakao_unlink_success = kakao_unlink(user.sns_id)
                if not kakao_unlink_success:
                    logger.warning(f"관리자 대량 삭제: 카카오 연결 끊기 실패했지만 삭제는 진행합니다. User ID: {user.id}")
                else:
                    logger.info(f"관리자 대량 삭제: 카카오 연결 끊기 성공. User ID: {user.id}")
        super().delete_queryset(request, queryset)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'icon']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)


# 카테고리별 상세 정보 모델 인라인
class TelecomProductDetailInline(admin.StackedInline):
    model = TelecomProductDetail
    can_delete = True
    verbose_name_plural = '통신 상품 상세 정보'

class ElectronicsProductDetailInline(admin.StackedInline):
    model = ElectronicsProductDetail
    can_delete = True
    verbose_name_plural = '가전 제품 상세 정보'

class RentalProductDetailInline(admin.StackedInline):
    model = RentalProductDetail
    can_delete = True
    verbose_name_plural = '렌탈 상품 상세 정보'

class SubscriptionProductDetailInline(admin.StackedInline):
    model = SubscriptionProductDetail
    can_delete = True
    verbose_name_plural = '구독 상품 상세 정보'

class StandardProductDetailInline(admin.StackedInline):
    model = StandardProductDetail
    can_delete = True
    verbose_name_plural = '일반 상품 상세 정보'

class ProductCustomValueInline(admin.TabularInline):
    model = ProductCustomValue
    extra = 1
    verbose_name_plural = '커스텀 필드 값'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'is_available', 'display_image']
    list_filter = ['is_available', 'category__detail_type']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('category_name', 'display_image_preview')
    
    def display_image(self, obj):
        """어드민 목록에서 이미지 썸네일 표시"""
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        elif obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="50" height="50" />')
        return "이미지 없음"
    display_image.short_description = '이미지'
    
    def display_image_preview(self, obj):
        """어드민 상세 페이지에서 이미지 미리보기"""
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="300" />')
        elif obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="300" />')
        return "이미지 없음"
    display_image_preview.short_description = '이미지 미리보기'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'slug', 'description', 'category', 'product_type', 'base_price', 'is_available', 'release_date')
        }),
        ('이미지', {
            'fields': ('image', 'image_url', 'display_image_preview'),
            'description': '이미지 파일을 업로드하거나 외부 URL을 입력하세요. 둘 다 입력된 경우 업로드된 이미지가 우선 사용됩니다.'
        }),
        ('추가 정보', {
            'fields': ('attributes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 이미지 처리"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 이미지 필드가 변경되었는지 확인
        if 'image' in form.changed_data:
            logger.info(f"ProductAdmin: 이미지 필드 변경 감지 - {form.cleaned_data.get('image')}")
        
        # 기본 저장 처리
        super().save_model(request, obj, form, change)
        
        # 저장 후 이미지 정보 로깅
        if obj.image:
            logger.info(f"ProductAdmin: 상품 '{obj.name}' 이미지 저장 완료")
            logger.info(f"ProductAdmin: 이미지 경로 - {obj.image.name}")
            logger.info(f"ProductAdmin: 이미지 URL - {obj.image.url}")
        else:
            logger.info(f"ProductAdmin: 상품 '{obj.name}' 이미지 없음")
    
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        if obj is None:
            return inline_instances
            
        inlines = self.get_inlines(request, obj)
        
        # 카테고리 유형에 따라 적절한 인라인 선택
        if obj.category and obj.category.detail_type == 'telecom':
            inlines = [TelecomProductDetailInline] + [i for i in inlines if i != TelecomProductDetailInline]
        elif obj.category and obj.category.detail_type == 'electronics':
            inlines = [ElectronicsProductDetailInline] + [i for i in inlines if i != ElectronicsProductDetailInline]
        elif obj.category and obj.category.detail_type == 'rental':
            inlines = [RentalProductDetailInline] + [i for i in inlines if i != RentalProductDetailInline]
        elif obj.category and obj.category.detail_type == 'subscription':
            inlines = [SubscriptionProductDetailInline] + [i for i in inlines if i != SubscriptionProductDetailInline]
        else:
            inlines = [StandardProductDetailInline] + [i for i in inlines if i != StandardProductDetailInline]
        
        # 커스텀 필드 값 인라인 추가
        inlines.append(ProductCustomValueInline)
            
        for inline_class in inlines:
            inline = inline_class(self.model, self.admin_site)
            inline_instances.append(inline)
            
        return inline_instances

@admin.register(ProductCustomField)
class ProductCustomFieldAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'field_label', 'category', 'field_type', 'is_required']
    list_filter = ['category', 'field_type', 'is_required']
    search_fields = ['field_name', 'field_label']

@admin.register(TelecomProductDetail)
class TelecomProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'carrier', 'registration_type', 'plan_info']
    list_filter = ['carrier', 'registration_type']
    search_fields = ['product__name']

@admin.register(ElectronicsProductDetail)
class ElectronicsProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'manufacturer', 'warranty_period']
    list_filter = ['manufacturer']
    search_fields = ['product__name']

@admin.register(RentalProductDetail)
class RentalProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'monthly_fee', 'deposit_amount']
    search_fields = ['product__name']

@admin.register(SubscriptionProductDetail)
class SubscriptionProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'billing_cycle', 'auto_renewal', 'free_trial_days']
    list_filter = ['billing_cycle', 'auto_renewal']
    search_fields = ['product__name']

@admin.register(StandardProductDetail)
class StandardProductDetailAdmin(admin.ModelAdmin):
    list_display = ['product', 'brand', 'shipping_fee']
    list_filter = ['brand']
    search_fields = ['product__name']

@admin.register(GroupBuy)
class GroupBuyAdmin(admin.ModelAdmin):
    list_display = ('product', 'creator', 'status', 'current_participants', 'end_time')
    raw_id_fields = ('participants',)
    readonly_fields = ('current_participants',)
    actions = ['force_complete_groupbuy']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('product',)
        super().__init__(model, admin_site)
        
    def force_complete_groupbuy(self, request, queryset):
        for groupbuy in queryset:
            groupbuy.status = 'completed'
            groupbuy.save()
    force_complete_groupbuy.short_description = '선택한 공구를 강제 완료 처리'

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('seller', 'groupbuy', 'bid_type', 'display_amount', 'is_selected')
    list_editable = ('is_selected',)
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('seller',)
        super().__init__(model, admin_site)

    def display_amount(self, obj):
        return f"{obj.amount // 10000}****"  # 부분 마스킹 처리
    display_amount.short_description = '입찰 금액'


@admin.register(ParticipantConsent)
class ParticipantConsentAdmin(admin.ModelAdmin):
    list_display = ['get_participant_name', 'get_groupbuy_title', 'status', 'agreed_at', 'disagreed_at', 'consent_deadline']
    list_filter = ['status', 'created_at']
    search_fields = ['participation__user__username', 'participation__groupbuy__title']
    readonly_fields = ['agreed_at', 'disagreed_at', 'created_at', 'updated_at']
    
    def get_participant_name(self, obj):
        return obj.participation.user.username
    get_participant_name.short_description = '참여자'
    
    def get_groupbuy_title(self, obj):
        return obj.participation.groupbuy.title
    get_groupbuy_title.short_description = '공구명'


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    """휴대폰 인증 관리"""
    list_display = ['phone_number', 'status', 'purpose', 'user', 'created_at', 'expires_at', 'attempt_count']
    list_filter = ['status', 'purpose', 'created_at']
    search_fields = ['phone_number', 'user__username', 'user__email']
    readonly_fields = ['verification_code', 'created_at', 'expires_at', 'verified_at', 'ip_address']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('phone_number', 'verification_code', 'status', 'purpose')
        }),
        ('인증 정보', {
            'fields': ('created_at', 'expires_at', 'verified_at', 'attempt_count', 'max_attempts')
        }),
        ('사용자 정보', {
            'fields': ('user', 'ip_address')
        }),
    )
    
    def has_add_permission(self, request):
        """관리자 페이지에서 직접 생성 불가"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가"""
        return False


# Partner 관련 Admin 클래스들
@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['partner_name', 'partner_code', 'commission_rate', 'is_active', 'get_total_referrals', 'get_available_settlement', 'created_at']
    list_filter = ['is_active', 'commission_rate', 'created_at']
    search_fields = ['partner_name', 'partner_code', 'user__username', 'user__email']
    readonly_fields = ['partner_code', 'created_at', 'updated_at', 'get_total_referrals', 'get_active_subscribers', 'get_available_settlement']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'partner_name', 'partner_code', 'is_active')
        }),
        ('수수료 설정', {
            'fields': ('commission_rate', 'minimum_settlement_amount')
        }),
        ('계좌 정보', {
            'fields': ('bank_name', 'account_number', 'account_holder')
        }),
        ('통계', {
            'fields': ('get_total_referrals', 'get_active_subscribers', 'get_available_settlement'),
            'classes': ('collapse',)
        }),
        ('관리 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_referrals(self, obj):
        return obj.get_total_referrals()
    get_total_referrals.short_description = '총 추천 수'
    
    def get_active_subscribers(self, obj):
        return obj.get_active_subscribers()
    get_active_subscribers.short_description = '활성 구독자'
    
    def get_available_settlement(self, obj):
        amount = obj.get_available_settlement_amount()
        return f"{amount:,}원"
    get_available_settlement.short_description = '정산 가능 금액'


@admin.register(ReferralRecord)
class ReferralRecordAdmin(admin.ModelAdmin):
    list_display = ['partner', 'get_member_name', 'total_amount', 'commission_amount', 'subscription_status', 'settlement_status', 'created_at']
    list_filter = ['subscription_status', 'settlement_status', 'partner', 'created_at']
    search_fields = ['partner__partner_name', 'referred_user__username', 'referred_user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('partner', 'referred_user', 'joined_date')
        }),
        ('구독 정보', {
            'fields': ('subscription_status', 'subscription_amount', 'subscription_start_date', 'subscription_end_date')
        }),
        ('티켓 정보', {
            'fields': ('ticket_count', 'ticket_amount')
        }),
        ('결제 정보', {
            'fields': ('total_amount', 'commission_amount')
        }),
        ('정산 정보', {
            'fields': ('settlement_status', 'settlement_date')
        }),
        ('관리 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_member_name(self, obj):
        name = obj.referred_user.nickname or obj.referred_user.username
        if len(name) > 2:
            return f"{name[0]}○{name[-1]}"
        elif len(name) == 2:
            return f"{name[0]}○"
        return name
    get_member_name.short_description = '회원명'
    
    actions = ['mark_as_settled']
    
    def mark_as_settled(self, request, queryset):
        """선택한 기록들을 정산 완료로 처리"""
        from django.utils import timezone
        updated = queryset.filter(settlement_status='requested').update(
            settlement_status='completed',
            settlement_date=timezone.now()
        )
        self.message_user(request, f'{updated}개의 기록이 정산 완료 처리되었습니다.')
    mark_as_settled.short_description = '정산 완료 처리'


@admin.register(PartnerSettlement)
class PartnerSettlementAdmin(admin.ModelAdmin):
    list_display = ['partner', 'settlement_amount', 'status', 'tax_invoice_requested', 'requested_at', 'processed_at']
    list_filter = ['status', 'tax_invoice_requested', 'requested_at']
    search_fields = ['partner__partner_name', 'partner__partner_code']
    readonly_fields = ['requested_at', 'updated_at']
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('partner', 'settlement_amount', 'status')
        }),
        ('계좌 정보', {
            'fields': ('bank_name', 'account_number', 'account_holder')
        }),
        ('세금계산서', {
            'fields': ('tax_invoice_requested',)
        }),
        ('처리 정보', {
            'fields': ('processed_at', 'processed_by', 'receipt_url')
        }),
        ('메모', {
            'fields': ('memo',)
        }),
        ('관리 정보', {
            'fields': ('requested_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_settlements', 'reject_settlements']
    
    def approve_settlements(self, request, queryset):
        """선택한 정산을 승인 처리"""
        count = 0
        for settlement in queryset.filter(status='pending'):
            if settlement.complete_settlement(processed_by=request.user):
                count += 1
        self.message_user(request, f'{count}건의 정산이 승인 처리되었습니다.')
    approve_settlements.short_description = '정산 승인'
    
    def reject_settlements(self, request, queryset):
        """선택한 정산을 거절 처리"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='failed',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(request, f'{updated}건의 정산이 거절 처리되었습니다.')
    reject_settlements.short_description = '정산 거절'


@admin.register(PartnerLink)
class PartnerLinkAdmin(admin.ModelAdmin):
    list_display = ['partner', 'short_code', 'click_count', 'conversion_count', 'get_conversion_rate', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['partner__partner_name', 'short_code', 'original_url']
    readonly_fields = ['short_code', 'short_url', 'click_count', 'conversion_count', 'created_at', 'updated_at']
    
    def get_conversion_rate(self, obj):
        if obj.click_count == 0:
            return "0%"
        rate = (obj.conversion_count / obj.click_count) * 100
        return f"{rate:.2f}%"
    get_conversion_rate.short_description = '전환율'


@admin.register(PartnerNotification)
class PartnerNotificationAdmin(admin.ModelAdmin):
    list_display = ['partner', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['partner__partner_name', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        """선택한 알림을 읽음 처리"""
        from django.utils import timezone
        updated = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated}개의 알림이 읽음 처리되었습니다.')
    mark_as_read.short_description = '읽음 처리'
    
    actions = ['cleanup_expired']
    
    def cleanup_expired(self, request, queryset):
        """만료된 인증 정리"""
        PhoneVerification.cleanup_expired()
        self.message_user(request, "만료된 인증이 정리되었습니다.")
    cleanup_expired.short_description = "만료된 인증 정리"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'banner_type', 'order', 'is_active', 'start_date', 'end_date', 'event', 'created_at']
    list_filter = ['banner_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['title', 'link_url']
    ordering = ['order', '-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'banner_type', 'order', 'is_active')
        }),
        ('이미지', {
            'fields': ('image', 'image_url', 'image_preview'),
            'description': '이미지를 업로드하거나 URL을 직접 입력하세요. 이미지 업로드 시 자동으로 S3에 업로드됩니다.'
        }),
        ('링크', {
            'fields': ('event', 'link_url'),
            'description': '이벤트를 선택하거나 외부 링크 URL을 입력하세요. 이벤트가 우선됩니다.'
        }),
        ('표시 기간', {
            'fields': ('start_date', 'end_date'),
            'description': '배너가 표시될 기간을 설정하세요. 비워두면 항상 표시됩니다.'
        }),
        ('메타 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'image_url', 'image_preview']
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" width="300" style="border-radius: 8px;" />')
        elif obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="300" style="border-radius: 8px;" />')
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # 유효한 배너인지 표시하기 위해 어노테이션 추가 가능
        return qs
    
    actions = ['activate_banners', 'deactivate_banners']
    
    def activate_banners(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 배너가 활성화되었습니다.')
    activate_banners.short_description = '선택한 배너 활성화'
    
    def deactivate_banners(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 배너가 비활성화되었습니다.')
    deactivate_banners.short_description = '선택한 배너 비활성화'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'status', 'start_date', 'end_date', 'is_active', 'view_count', 'created_at']
    list_filter = ['event_type', 'status', 'is_active', 'start_date', 'end_date']
    search_fields = ['title', 'content', 'short_description']
    ordering = ['-start_date', '-created_at']
    prepopulated_fields = {}  # 동적으로 설정
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'slug', 'event_type', 'status', 'is_active')
        }),
        ('이벤트 내용', {
            'fields': ('short_description', 'content'),
            'description': 'HTML 태그를 사용할 수 있습니다.'
        }),
        ('이미지', {
            'fields': ('thumbnail', 'thumbnail_url', 'thumbnail_preview', 'content_image', 'content_image_url', 'content_image_preview'),
            'description': '썸네일은 목록에서 표시되고, 본문 이미지는 상세 페이지에서 표시됩니다.'
        }),
        ('기간 설정', {
            'fields': ('start_date', 'end_date')
        }),
        ('통계', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'thumbnail_url', 'content_image_url', 'view_count', 'status', 'thumbnail_preview', 'content_image_preview']
    
    def thumbnail_preview(self, obj):
        """썸네일 미리보기"""
        if obj.thumbnail_url:
            return mark_safe(f'<img src="{obj.thumbnail_url}" width="200" style="border-radius: 8px;" />')
        elif obj.thumbnail:
            return mark_safe(f'<img src="{obj.thumbnail.url}" width="200" style="border-radius: 8px;" />')
        return "썸네일 없음"
    thumbnail_preview.short_description = '썸네일 미리보기'
    
    def content_image_preview(self, obj):
        """본문 이미지 미리보기"""
        if obj.content_image_url:
            return mark_safe(f'<img src="{obj.content_image_url}" width="300" style="border-radius: 8px;" />')
        elif obj.content_image:
            return mark_safe(f'<img src="{obj.content_image.url}" width="300" style="border-radius: 8px;" />')
        return "본문 이미지 없음"
    content_image_preview.short_description = '본문 이미지 미리보기'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # 수정하는 경우
            readonly.append('slug')  # 슬러그는 수정 불가
        return readonly
    
    def get_prepopulated_fields(self, request, obj=None):
        if obj is None:  # 새로 생성하는 경우에만
            return {'slug': ('title',)}
        return {}
    
    actions = ['activate_events', 'deactivate_events', 'reset_view_count']
    
    def activate_events(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개의 이벤트가 활성화되었습니다.')
    activate_events.short_description = '선택한 이벤트 활성화'
    
    def deactivate_events(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 이벤트가 비활성화되었습니다.')
    deactivate_events.short_description = '선택한 이벤트 비활성화'
    
    def reset_view_count(self, request, queryset):
        updated = queryset.update(view_count=0)
        self.message_user(request, f'{updated}개의 이벤트 조회수가 초기화되었습니다.')
    reset_view_count.short_description = '조회수 초기화'


# BidTokenAdjustmentLog는 아래에서 더 완벽한 버전으로 등록됨
# @admin.register(BidTokenAdjustmentLog)
class OldBidTokenAdjustmentLogAdmin(admin.ModelAdmin):
    list_display = ['seller', 'admin', 'adjustment_type', 'quantity', 'reason_summary', 'created_at']
    list_filter = ['adjustment_type', 'created_at']
    search_fields = ['seller__username', 'seller__email', 'admin__username', 'reason']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def reason_summary(self, obj):
        """사유 요약"""
        if len(obj.reason) > 30:
            return f"{obj.reason[:30]}..."
        return obj.reason
    reason_summary.short_description = '사유'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('seller', 'admin')
    
    def has_add_permission(self, request):
        """직접 생성 불가"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가"""
        return False




@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    """문의사항 관리"""
    list_display = ["id", "user", "title", "status", "created_at", "answered_at"]
    list_filter = ["status", "created_at", "answered_at"]
    search_fields = ["title", "content", "user__username", "user__email"]
    readonly_fields = ["user", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    
    fieldsets = (
        ("문의 정보", {
            "fields": ("user", "title", "content", "status")
        }),
        ("답변 정보", {
            "fields": ("answer", "answered_at"),
            "classes": ("collapse",)
        }),
        ("관리 정보", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """답변 작성 시 자동으로 상태 변경 및 답변 시간 설정"""
        from django.utils import timezone
        if "answer" in form.changed_data and obj.answer:
            if obj.status != "answered":
                obj.status = "answered"
                obj.answered_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """관련 객체를 미리 가져와 성능 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related("user")
    
    actions = ["mark_as_answered", "mark_as_pending"]
    
    def mark_as_answered(self, request, queryset):
        """선택한 문의를 답변완료로 처리"""
        from django.utils import timezone
        updated = 0
        for inquiry in queryset.filter(status="pending"):
            if inquiry.answer:  # 답변이 있는 경우에만
                inquiry.status = "answered"
                inquiry.answered_at = timezone.now()
                inquiry.save()
                updated += 1
        self.message_user(request, f"{updated}개의 문의가 답변완료 처리되었습니다.")
    mark_as_answered.short_description = "답변완료 처리 (답변이 있는 경우만)"
    
    def mark_as_pending(self, request, queryset):
        """선택한 문의를 답변대기로 처리"""
        updated = queryset.filter(status="answered").update(
            status="pending",
            answered_at=None
        )
        self.message_user(request, f"{updated}개의 문의가 답변대기로 처리되었습니다.")
    mark_as_pending.short_description = "답변대기 처리"


@admin.register(BusinessNumberVerification)
class BusinessNumberVerificationAdmin(admin.ModelAdmin):
    """사업자번호 검증 관리"""
    list_display = ['user', 'business_number', 'status', 'business_name', 'business_status', 'created_at', 'verified_at']
    list_filter = ['status', 'business_status', 'created_at', 'verified_at']
    search_fields = ['user__username', 'user__email', 'business_number', 'business_name']
    readonly_fields = ['user', 'business_number', 'status', 'business_name', 'representative_name', 
                      'business_status', 'business_type', 'establishment_date', 'address',
                      'created_at', 'verified_at', 'error_message', 'api_response_summary']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'business_number', 'status', 'created_at', 'verified_at')
        }),
        ('사업자 정보', {
            'fields': ('business_name', 'representative_name', 'business_status', 'business_type', 
                      'establishment_date', 'address'),
            'classes': ('collapse',)
        }),
        ('오류 정보', {
            'fields': ('error_message', 'api_response_summary'),
            'classes': ('collapse',)
        }),
    )
    
    def api_response_summary(self, obj):
        """API 응답 요약"""
        if not obj.api_response:
            return "응답 없음"
        
        try:
            import json
            response = obj.api_response
            if isinstance(response, str):
                response = json.loads(response)
            
            # 요약 정보 추출
            summary = []
            if 'data' in response and response['data']:
                data = response['data'][0] if response['data'] else {}
                if 'b_stt' in data:
                    summary.append(f"상태: {data['b_stt']}")
                if 'tax_type' in data:
                    summary.append(f"과세유형: {data['tax_type'][:50]}...")
            
            if 'message' in response:
                summary.append(f"메시지: {response['message']}")
                
            return ' | '.join(summary) if summary else "데이터 없음"
        except:
            return "응답 파싱 오류"
    api_response_summary.short_description = 'API 응답 요약'
    
    def get_queryset(self, request):
        """관련 객체를 미리 가져와 성능 최적화"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """직접 생성 불가 - API를 통해서만 생성"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가 - 검증 기록은 읽기 전용"""
        return False
    
    actions = ['retry_verification']
    
    def retry_verification(self, request, queryset):
        """선택한 사업자번호 재검증"""
        from .utils.business_verification_service import BusinessVerificationService
        from django.utils import timezone
        
        verification_service = BusinessVerificationService()
        success_count = 0
        error_count = 0
        
        for verification in queryset.filter(status__in=['invalid', 'error']):
            try:
                result = verification_service.verify_business_number(verification.business_number)
                
                # 새로운 검증 기록 생성
                BusinessNumberVerification.objects.create(
                    user=verification.user,
                    business_number=verification.business_number,
                    status=result['status'],
                    business_name=result['data'].get('business_name', '') if result['success'] else '',
                    business_status=result['data'].get('business_status', '') if result['success'] else '',
                    verified_at=timezone.now() if result['success'] and result['status'] == 'valid' else None,
                    error_message=result.get('error_message', '') if not result['success'] else '',
                    api_response=result.get('api_response', {})
                )
                
                success_count += 1
            except Exception as e:
                error_count += 1
                
        message = f"재검증 완료: 성공 {success_count}건, 실패 {error_count}건"
        self.message_user(request, message)
    retry_verification.short_description = "선택한 사업자번호 재검증"


@admin.register(BidToken)
class BidTokenAdmin(admin.ModelAdmin):
    """견적티켓 관리"""
    list_display = ['id', 'seller', 'token_type', 'status', 'expires_at', 'created_at']
    list_filter = ['token_type', 'status', 'created_at', 'expires_at']
    search_fields = ['seller__username', 'seller__email', 'seller__nickname']
    readonly_fields = ['created_at', 'used_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('seller', 'token_type', 'status')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'expires_at', 'used_at')
        }),
    )
    
    actions = ['activate_tokens', 'expire_tokens', 'add_tokens_to_seller', 'grant_subscription_to_seller']
    
    def activate_tokens(self, request, queryset):
        """선택한 토큰 활성화"""
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated}개의 토큰이 활성화되었습니다.")
    activate_tokens.short_description = "선택한 토큰 활성화"
    
    def expire_tokens(self, request, queryset):
        """선택한 토큰 만료 처리"""
        updated = queryset.update(status='expired')
        self.message_user(request, f"{updated}개의 토큰이 만료 처리되었습니다.")
    expire_tokens.short_description = "선택한 토큰 만료 처리"
    
    def add_tokens_to_seller(self, request, queryset):
        """판매자에게 토큰 추가"""
        from django import forms
        from django.shortcuts import render
        from django.http import HttpResponseRedirect
        
        class TokenAddForm(forms.Form):
            seller = forms.ModelChoiceField(
                queryset=User.objects.filter(role='seller'),
                label='판매자 선택',
                required=True
            )
            quantity = forms.IntegerField(
                min_value=1,
                max_value=100,
                initial=5,
                label='추가할 토큰 수'
            )
            reason = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3}),
                label='추가 사유',
                initial='관리자 수동 추가'
            )
        
        if 'apply' in request.POST:
            form = TokenAddForm(request.POST)
            if form.is_valid():
                seller = form.cleaned_data['seller']
                quantity = form.cleaned_data['quantity']
                reason = form.cleaned_data['reason']
                
                # 토큰 생성
                for _ in range(quantity):
                    BidToken.objects.create(
                        seller=seller,
                        token_type='single',
                        status='active'
                    )
                
                # 조정 이력 기록
                BidTokenAdjustmentLog.objects.create(
                    seller=seller,
                    admin=request.user,
                    adjustment_type='add',
                    quantity=quantity,
                    reason=reason
                )
                
                self.message_user(request, f"{seller.nickname or seller.username}님에게 {quantity}개의 토큰을 추가했습니다.")
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = TokenAddForm()
        
        return render(request, 'admin/token_add_form.html', {
            'form': form,
            'title': '견적티켓 추가',
            'opts': self.model._meta,
        })
    add_tokens_to_seller.short_description = "판매자에게 토큰 추가"
    
    def grant_subscription_to_seller(self, request, queryset):
        """판매자에게 구독권 부여"""
        from django import forms
        from django.shortcuts import render
        from django.http import HttpResponseRedirect
        from datetime import timedelta
        from django.utils import timezone
        
        class SubscriptionGrantForm(forms.Form):
            seller = forms.ModelChoiceField(
                queryset=User.objects.filter(role='seller'),
                label='판매자 선택',
                required=True
            )
            days = forms.IntegerField(
                min_value=1,
                max_value=365,
                initial=30,
                label='구독 기간 (일)'
            )
            reason = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3}),
                label='부여 사유',
                initial='관리자 구독권 부여'
            )
        
        if 'apply' in request.POST:
            form = SubscriptionGrantForm(request.POST)
            if form.is_valid():
                seller = form.cleaned_data['seller']
                days = form.cleaned_data['days']
                reason = form.cleaned_data['reason']
                
                # 기존 구독권 만료 처리
                BidToken.objects.filter(
                    seller=seller,
                    token_type='unlimited',
                    status='active'
                ).update(status='expired')
                
                # 새 구독권 생성
                expires_at = timezone.now() + timedelta(days=days)
                BidToken.objects.create(
                    seller=seller,
                    token_type='unlimited',
                    status='active',
                    expires_at=expires_at
                )
                
                # 조정 이력 기록
                BidTokenAdjustmentLog.objects.create(
                    seller=seller,
                    admin=request.user,
                    adjustment_type='grant_subscription',
                    quantity=days,
                    reason=reason
                )
                
                self.message_user(request, f"{seller.nickname or seller.username}님에게 {days}일 구독권을 부여했습니다.")
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = SubscriptionGrantForm()
        
        return render(request, 'admin/subscription_grant_form.html', {
            'form': form,
            'title': '구독권 부여',
            'opts': self.model._meta,
        })
    grant_subscription_to_seller.short_description = "판매자에게 구독권 부여"


@admin.register(BidTokenAdjustmentLog)
class BidTokenAdjustmentLogAdmin(admin.ModelAdmin):
    """견적티켓 조정 이력 관리"""
    list_display = ['id', 'seller', 'admin', 'adjustment_type', 'quantity', 'reason', 'created_at']
    list_filter = ['adjustment_type', 'created_at']
    search_fields = ['seller__username', 'seller__email', 'seller__nickname', 'admin__username', 'reason']
    readonly_fields = ['seller', 'admin', 'adjustment_type', 'quantity', 'reason', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('조정 정보', {
            'fields': ('seller', 'admin', 'adjustment_type', 'quantity')
        }),
        ('상세 정보', {
            'fields': ('reason', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        """직접 생성 불가 - 조정 작업을 통해서만 생성"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가 - 이력은 읽기 전용"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """삭제 불가 - 이력 보존"""
        return False


@admin.register(BidTokenPurchase) 
class BidTokenPurchaseAdmin(admin.ModelAdmin):
    """견적티켓 구매 내역 관리"""
    list_display = ['id', 'seller', 'token_type', 'quantity', 'total_price', 'payment_status', 'payment_date']
    list_filter = ['token_type', 'payment_status', 'payment_date']
    search_fields = ['seller__username', 'seller__email', 'seller__nickname']
    readonly_fields = ['payment_date']
    date_hierarchy = 'payment_date'
    ordering = ['-payment_date']
    
    fieldsets = (
        ('구매 정보', {
            'fields': ('seller', 'token_type', 'quantity', 'total_price')
        }),
        ('결제 정보', {
            'fields': ('payment_status', 'payment_date')
        }),
    )
    
    def has_add_permission(self, request):
        """직접 생성 불가 - 결제를 통해서만 생성"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 불가 - 구매 내역은 읽기 전용"""
        return False

