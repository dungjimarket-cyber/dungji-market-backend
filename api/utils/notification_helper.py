"""
알림 발송 헬퍼 함수
인앱 알림 생성 + 푸시 알림 발송을 통합 처리
"""
import logging
from typing import Optional, Dict, Any
from api.models import Notification, NotificationSetting
from api.utils.push_notification import send_push_to_user

logger = logging.getLogger(__name__)


def format_price(price: int) -> str:
    """
    금액을 천단위 쉼표 포맷으로 변환

    Args:
        price: 금액 (정수)

    Returns:
        str: "100,000원" 형식의 문자열
    """
    return f"{price:,}원"


def send_notification(
    user,
    notification_type: str,
    message: str,
    groupbuy=None,
    item_type: Optional[str] = None,
    item_id: Optional[int] = None,
    push_title: Optional[str] = None,
    push_data: Optional[Dict[str, Any]] = None
) -> Optional[Notification]:
    """
    통합 알림 발송 (인앱 + 푸시)

    Args:
        user: 알림 받을 User 인스턴스
        notification_type: 알림 타입 (Notification.NOTIFICATION_TYPES 참조)
        message: 알림 메시지
        groupbuy: 공구 인스턴스 (선택)
        item_type: 아이템 타입 ('phone', 'electronics') (선택)
        item_id: 아이템 ID (선택)
        push_title: 푸시 알림 제목 (선택, 기본값: "둥지마켓")
        push_data: 푸시 알림 추가 데이터 (선택)

    Returns:
        Notification: 생성된 알림 인스턴스 (알림 설정으로 차단된 경우 None)
    """
    try:
        # 1. 알림 설정 확인
        settings, _ = NotificationSetting.objects.get_or_create(user=user)

        # 마케팅 알림은 별도 체크
        if notification_type == 'marketing':
            if not settings.marketing_notifications:
                logger.info(f"Marketing notification disabled for user {user.id}")
                return None
        else:
            # 거래 알림 체크
            if not settings.trade_notifications:
                logger.info(f"Trade notification disabled for user {user.id}")
                return None

        # 2. 인앱 알림 생성 (DB 저장)
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            message=message,
            groupbuy=groupbuy,
            item_type=item_type,
            item_id=item_id
        )

        logger.info(f"In-app notification created: {notification.id} for user {user.id}")

        # 3. 푸시 알림 발송
        title = push_title or "둥지마켓"
        body = message
        data = push_data or {}

        # 알림 타입별 추가 데이터
        if groupbuy:
            data['groupbuy_id'] = str(groupbuy.id)
        if item_type and item_id:
            data['item_type'] = item_type
            data['item_id'] = str(item_id)
        data['notification_id'] = str(notification.id)

        success_count = send_push_to_user(user, title, body, data)

        if success_count > 0:
            logger.info(f"Push sent to {success_count} devices for user {user.id}")
        else:
            logger.warning(f"No push sent for user {user.id} (no active tokens or push failed)")

        return notification

    except Exception as e:
        logger.error(f"Error in send_notification: {str(e)}")
        # 에러가 발생해도 알림 시스템이 전체 흐름을 막지 않도록
        return None


def send_groupbuy_notification(
    user,
    groupbuy,
    notification_type: str,
    message: str,
    push_title: Optional[str] = None
) -> Optional[Notification]:
    """
    공구 알림 발송 (편의 함수)

    Args:
        user: 알림 받을 User 인스턴스
        groupbuy: GroupBuy 인스턴스
        notification_type: 알림 타입
        message: 알림 메시지
        push_title: 푸시 제목 (선택)

    Returns:
        Notification: 생성된 알림 인스턴스
    """
    return send_notification(
        user=user,
        notification_type=notification_type,
        message=message,
        groupbuy=groupbuy,
        push_title=push_title or "공구 알림",
        push_data={'type': 'groupbuy'}
    )


def send_custom_groupbuy_notification(
    user,
    custom_groupbuy,
    notification_type: str,
    message: str,
    push_title: Optional[str] = None
) -> Optional[Notification]:
    """
    커스텀 공구 알림 발송 (편의 함수)

    Args:
        user: 알림 받을 User 인스턴스
        custom_groupbuy: CustomGroupBuy 인스턴스
        notification_type: 알림 타입
        message: 알림 메시지
        push_title: 푸시 제목 (선택)

    Returns:
        Notification: 생성된 알림 인스턴스
    """
    try:
        # 커스텀 공구 알림은 custom_groupbuy 필드 사용
        settings, _ = NotificationSetting.objects.get_or_create(user=user)

        # 거래 알림 체크
        if not settings.trade_notifications:
            logger.info(f"Trade notification disabled for user {user.id}")
            return None

        # 인앱 알림 생성
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            message=message,
            custom_groupbuy=custom_groupbuy
        )

        logger.info(f"Custom groupbuy notification created: {notification.id} for user {user.id}")

        # 푸시 알림 발송
        title = push_title or "커스텀 공구 알림"
        body = message
        data = {
            'type': 'custom_groupbuy',
            'custom_groupbuy_id': str(custom_groupbuy.id),
            'notification_id': str(notification.id)
        }

        success_count = send_push_to_user(user, title, body, data)

        if success_count > 0:
            logger.info(f"Push sent to {success_count} devices for user {user.id}")
        else:
            logger.warning(f"No push sent for user {user.id} (no active tokens or push failed)")

        return notification

    except Exception as e:
        logger.error(f"Error in send_custom_groupbuy_notification: {str(e)}")
        return None


def send_used_trade_notification(
    user,
    item_type: str,
    item_id: int,
    notification_type: str,
    message: str,
    push_title: Optional[str] = None
) -> Optional[Notification]:
    """
    중고거래 알림 발송 (편의 함수)

    Args:
        user: 알림 받을 User 인스턴스
        item_type: 'phone' 또는 'electronics'
        item_id: 상품 ID
        notification_type: 알림 타입
        message: 알림 메시지
        push_title: 푸시 제목 (선택)

    Returns:
        Notification: 생성된 알림 인스턴스
    """
    return send_notification(
        user=user,
        notification_type=notification_type,
        message=message,
        item_type=item_type,
        item_id=item_id,
        push_title=push_title or "거래 알림",
        push_data={'type': 'used'}
    )
