"""
Cron job API endpoints for status updates
"""
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from functools import wraps
from .utils import update_groupbuys_status
from .models import GroupBuy
import logging

logger = logging.getLogger(__name__)

# Cron job 인증을 위한 데코레이터
def cron_auth_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Vercel cron job에서 보낸 인증 토큰 확인
        auth_header = request.headers.get('Authorization')
        expected_token = os.getenv('CRON_SECRET_TOKEN', 'your-secret-token-here')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        token = auth_header.split(' ')[1]
        if token != expected_token:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        
        return view_func(request, *args, **kwargs)
    return wrapped_view


@csrf_exempt
@require_http_methods(["POST"])
@cron_auth_required
def update_groupbuy_status_cron(request):
    """
    Cron job endpoint for updating groupbuy statuses
    """
    try:
        logger.info("Starting cron job for groupbuy status update")
        
        # 업데이트가 필요한 공구들 조회 (v3.0: bidding 제거)
        groupbuys_to_update = GroupBuy.objects.filter(
            status__in=['recruiting', 'final_selection_buyers', 'final_selection_seller']
        ).exclude(
            status='completed'
        ).exclude(
            status='cancelled'
        )
        
        count = groupbuys_to_update.count()
        logger.info(f"Found {count} groupbuys to check")
        
        # 상태 업데이트 실행
        updated_count = update_groupbuys_status(groupbuys_to_update)
        
        logger.info(f"Updated {updated_count} groupbuys")
        
        return JsonResponse({
            'success': True,
            'checked': count,
            'updated': updated_count,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in cron job: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@cron_auth_required
def send_reminder_notifications_cron(request):
    """
    Cron job endpoint for sending reminder notifications
    """
    try:
        from .utils.notification_scheduler import send_reminder_notifications
        
        logger.info("Starting cron job for reminder notifications")
        
        sent_count = send_reminder_notifications()
        
        logger.info(f"Sent {sent_count} reminder notifications")
        
        return JsonResponse({
            'success': True,
            'sent': sent_count,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in reminder notifications cron job: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def cron_health_check(request):
    """
    Health check endpoint for cron jobs (no auth required)
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })