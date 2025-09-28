"""
Celery tasks for custom groupbuy expiration management
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_expired_custom_groupbuys():
    """
    만료된 커스텀 공구 체크 및 상태 업데이트
    5분마다 실행
    """
    from api.services.custom_expiration_service import CustomExpirationService

    try:
        CustomExpirationService.check_expired_groupbuys()
        logger.info(f"[{timezone.now()}] 커스텀 공구 만료 체크 완료")
        return "Success"
    except Exception as e:
        logger.error(f"커스텀 공구 만료 체크 중 오류: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def check_seller_decision_deadline():
    """
    판매자 결정 기한 체크
    5분마다 실행
    """
    from api.services.custom_expiration_service import CustomExpirationService

    try:
        CustomExpirationService.check_seller_decision_deadline()
        logger.info(f"[{timezone.now()}] 판매자 결정 기한 체크 완료")
        return "Success"
    except Exception as e:
        logger.error(f"판매자 결정 기한 체크 중 오류: {str(e)}")
        return f"Error: {str(e)}"