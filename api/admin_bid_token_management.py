"""
관리자 전용 견적 티켓 수동 조절 시스템
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.urls import path, reverse
from django.utils.html import mark_safe
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import User, BidToken, BidTokenAdjustmentLog
import json

class BidTokenManagementAdmin:
    """견적 티켓 수동 조절 관리자 페이지"""
    
    def get_urls(self):
        """Admin URL 추가"""
        urls = [
            path('bid-token-management/', 
                 staff_member_required(self.token_management_view), 
                 name='bid_token_management'),
            path('bid-token-management/adjust/', 
                 staff_member_required(self.adjust_tokens_view), 
                 name='adjust_bid_tokens'),
            path('bid-token-management/seller-search/', 
                 staff_member_required(self.seller_search_view), 
                 name='seller_search'),
            path('bid-token-management/bulk-adjust/', 
                 staff_member_required(self.bulk_adjust_view), 
                 name='bulk_adjust_tokens'),
        ]
        return urls
    
    @method_decorator(csrf_exempt)
    def token_management_view(self, request):
        """메인 견적 티켓 관리 페이지"""
        # 전체 통계
        total_sellers = User.objects.filter(role='seller').count()
        total_active_tokens = BidToken.objects.filter(status='active', token_type='single').count()
        total_used_tokens = BidToken.objects.filter(status='used').count()
        total_unlimited_subscriptions = BidToken.objects.filter(
            token_type='unlimited', 
            status='active',
            expires_at__gt=timezone.now()
        ).count()
        
        # 최근 조정 이력 (최근 50개)
        recent_adjustments = BidTokenAdjustmentLog.objects.select_related(
            'seller', 'admin'
        ).order_by('-created_at')[:50]
        
        # 토큰 보유 현황별 판매자 수
        token_stats = []
        for count_range in [(0, 0), (1, 5), (6, 10), (11, 20), (21, float('inf'))]:
            if count_range[1] == float('inf'):
                sellers = User.objects.filter(
                    role='seller',
                    bid_tokens__status='active',
                    bid_tokens__token_type='single'
                ).annotate(
                    token_count=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single'))
                ).filter(token_count__gt=20).count()
                range_label = '21개 이상'
            else:
                sellers = User.objects.filter(
                    role='seller'
                ).annotate(
                    token_count=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single'))
                ).filter(token_count__gte=count_range[0], token_count__lte=count_range[1]).count()
                if count_range[0] == count_range[1]:
                    range_label = f'{count_range[0]}개'
                else:
                    range_label = f'{count_range[0]}-{count_range[1]}개'
            
            token_stats.append({
                'range': range_label,
                'count': sellers
            })
        
        context = {
            'title': '견적 티켓 수동 조절 관리',
            'total_sellers': total_sellers,
            'total_active_tokens': total_active_tokens,
            'total_used_tokens': total_used_tokens,
            'total_unlimited_subscriptions': total_unlimited_subscriptions,
            'recent_adjustments': recent_adjustments,
            'token_stats': token_stats,
        }
        
        return render(request, 'admin/bid_token_management.html', context)
    
    @method_decorator(csrf_exempt)
    @require_http_methods(["POST"])
    def adjust_tokens_view(self, request):
        """개별 판매자 토큰 조정"""
        try:
            data = json.loads(request.body)
            seller_id = data.get('seller_id')
            adjustment_type = data.get('adjustment_type')  # 'add', 'subtract', 'grant_subscription'
            quantity = int(data.get('quantity', 0))
            reason = data.get('reason', '관리자 수동 조정')
            
            if not all([seller_id, adjustment_type, quantity]):
                return JsonResponse({'success': False, 'error': '필수 정보가 누락되었습니다.'})
            
            seller = get_object_or_404(User, id=seller_id, role='seller')
            
            if adjustment_type == 'add':
                # 토큰 추가
                for _ in range(quantity):
                    BidToken.objects.create(
                        seller=seller,
                        token_type='single',
                        status='active'
                    )
                message = f'{quantity}개의 견적 티켓이 추가되었습니다.'
                
            elif adjustment_type == 'subtract':
                # 토큰 차감 (활성 토큰만)
                active_tokens = BidToken.objects.filter(
                    seller=seller,
                    status='active',
                    token_type='single'
                ).order_by('created_at')[:quantity]
                
                if len(active_tokens) < quantity:
                    return JsonResponse({
                        'success': False, 
                        'error': f'활성 토큰이 {len(active_tokens)}개만 있습니다. {quantity}개를 차감할 수 없습니다.'
                    })
                
                for token in active_tokens:
                    token.status = 'expired'
                    token.expires_at = timezone.now()
                    token.save()
                
                message = f'{quantity}개의 견적 티켓이 차감되었습니다.'
                
            elif adjustment_type == 'grant_subscription':
                # 구독권 부여 (기존 구독권은 만료 처리)
                BidToken.objects.filter(
                    seller=seller,
                    token_type='unlimited',
                    status='active'
                ).update(status='expired')
                
                # 새 구독권 생성 (quantity = 일수)
                expires_at = timezone.now() + timedelta(days=quantity)
                BidToken.objects.create(
                    seller=seller,
                    token_type='unlimited',
                    status='active',
                    expires_at=expires_at
                )
                message = f'{quantity}일 구독권이 부여되었습니다.'
            
            else:
                return JsonResponse({'success': False, 'error': '잘못된 조정 유형입니다.'})
            
            # 조정 로그 기록
            BidTokenAdjustmentLog.objects.create(
                seller=seller,
                admin=request.user,
                adjustment_type=adjustment_type,
                quantity=quantity,
                reason=reason
            )
            
            # 현재 토큰 상태 조회
            current_tokens = BidToken.objects.filter(
                seller=seller,
                status='active',
                token_type='single'
            ).count()
            
            current_subscription = BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at__gt=timezone.now()
            ).first()
            
            return JsonResponse({
                'success': True,
                'message': message,
                'current_tokens': current_tokens,
                'has_subscription': bool(current_subscription),
                'subscription_expires': current_subscription.expires_at.isoformat() if current_subscription else None
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    @method_decorator(csrf_exempt)
    def seller_search_view(self, request):
        """판매자 검색 API"""
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'sellers': []})
        
        sellers = User.objects.filter(
            role='seller'
        ).filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(nickname__icontains=query) |
            Q(business_number__icontains=query)
        ).annotate(
            active_tokens=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single')),
            used_tokens=Count('bid_tokens', filter=Q(bid_tokens__status='used'))
        )[:20]
        
        results = []
        for seller in sellers:
            # 구독권 확인
            has_subscription = BidToken.objects.filter(
                seller=seller,
                token_type='unlimited',
                status='active',
                expires_at__gt=timezone.now()
            ).exists()
            
            results.append({
                'id': seller.id,
                'username': seller.username,
                'email': seller.email,
                'nickname': seller.nickname or '',
                'business_number': seller.business_number or '',
                'active_tokens': seller.active_tokens,
                'used_tokens': seller.used_tokens,
                'has_subscription': has_subscription,
                'display_name': f"{seller.nickname or seller.username} ({seller.email})"
            })
        
        return JsonResponse({'sellers': results})
    
    @method_decorator(csrf_exempt)
    @require_http_methods(["POST"])
    def bulk_adjust_view(self, request):
        """대량 토큰 조정"""
        try:
            data = json.loads(request.body)
            filter_type = data.get('filter_type')  # 'all', 'no_tokens', 'low_tokens', 'business_verified'
            adjustment_type = data.get('adjustment_type')
            quantity = int(data.get('quantity', 0))
            reason = data.get('reason', '관리자 대량 조정')
            
            # 필터에 따라 대상 판매자 선택
            base_queryset = User.objects.filter(role='seller')
            
            if filter_type == 'no_tokens':
                # 토큰이 없는 판매자
                sellers = base_queryset.annotate(
                    token_count=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single'))
                ).filter(token_count=0)
            elif filter_type == 'low_tokens':
                # 토큰이 5개 이하인 판매자
                sellers = base_queryset.annotate(
                    token_count=Count('bid_tokens', filter=Q(bid_tokens__status='active', bid_tokens__token_type='single'))
                ).filter(token_count__lte=5)
            elif filter_type == 'business_verified':
                # 사업자 인증된 판매자
                sellers = base_queryset.filter(is_business_verified=True)
            else:
                # 모든 판매자
                sellers = base_queryset
            
            affected_count = 0
            
            for seller in sellers[:100]:  # 안전을 위해 최대 100명으로 제한
                if adjustment_type == 'add':
                    # 토큰 추가
                    for _ in range(quantity):
                        BidToken.objects.create(
                            seller=seller,
                            token_type='single',
                            status='active'
                        )
                    affected_count += 1
                    
                elif adjustment_type == 'grant_subscription':
                    # 구독권 부여
                    BidToken.objects.filter(
                        seller=seller,
                        token_type='unlimited',
                        status='active'
                    ).update(status='expired')
                    
                    expires_at = timezone.now() + timedelta(days=quantity)
                    BidToken.objects.create(
                        seller=seller,
                        token_type='unlimited',
                        status='active',
                        expires_at=expires_at
                    )
                    affected_count += 1
                
                # 로그 기록
                BidTokenAdjustmentLog.objects.create(
                    seller=seller,
                    admin=request.user,
                    adjustment_type=adjustment_type,
                    quantity=quantity,
                    reason=f"대량 조정: {reason}"
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{affected_count}명의 판매자에게 조정이 완료되었습니다.',
                'affected_count': affected_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

# 기존 Admin Site에 URL 추가
class BidTokenManagementSite(admin.AdminSite):
    """견적 티켓 관리 전용 Admin Site"""
    
    def get_urls(self):
        urls = super().get_urls()
        bid_token_admin = BidTokenManagementAdmin()
        urls += bid_token_admin.get_urls()
        return urls

# admin.py에서 import 후 사용할 수 있도록 export
bid_token_management = BidTokenManagementAdmin()