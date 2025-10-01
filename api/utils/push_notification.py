"""
푸시 알림 발송 유틸리티
FCM (Firebase Cloud Messaging) 및 APNs (Apple Push Notification service) 연동
"""
import json
import logging
import requests
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def send_fcm_push(token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    FCM을 통해 푸시 알림 발송 (Android/Web)

    Args:
        token: FCM 디바이스 토큰
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 (선택)

    Returns:
        bool: 발송 성공 여부
    """
    try:
        # FCM 서버 키가 없으면 스킵
        server_key = getattr(settings, 'FCM_SERVER_KEY', None)
        if not server_key:
            logger.warning("FCM_SERVER_KEY not configured. Skipping push notification.")
            return False

        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"Bearer {server_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
                "icon": "/icons/icon-192x192.png",
                "badge": "/icons/icon-96x96.png",
                "click_action": settings.FRONTEND_URL or "https://dungji-market.com",
            },
            "data": data or {},
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('success', 0) > 0:
                logger.info(f"FCM push sent successfully to {token[:20]}...")
                return True
            else:
                logger.error(f"FCM push failed: {result}")
                return False
        else:
            logger.error(f"FCM request failed: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error("FCM request timeout")
        return False
    except Exception as e:
        logger.error(f"Error sending FCM push: {str(e)}")
        return False


def send_apns_push(token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    APNs를 통해 푸시 알림 발송 (iOS)

    Args:
        token: APNs 디바이스 토큰
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 (선택)

    Returns:
        bool: 발송 성공 여부
    """
    try:
        # APNs 설정이 없으면 스킵
        apns_key_id = getattr(settings, 'APNS_KEY_ID', None)
        apns_team_id = getattr(settings, 'APNS_TEAM_ID', None)
        apns_bundle_id = getattr(settings, 'APNS_BUNDLE_ID', None)

        if not all([apns_key_id, apns_team_id, apns_bundle_id]):
            logger.warning("APNs not configured. Skipping iOS push notification.")
            return False

        # TODO: APNs JWT 토큰 생성 및 발송 로직
        # 현재는 FCM을 통한 iOS 푸시를 사용하므로 이 함수는 나중에 구현
        logger.info("APNs push not yet implemented. Using FCM for iOS.")
        return send_fcm_push(token, title, body, data)

    except Exception as e:
        logger.error(f"Error sending APNs push: {str(e)}")
        return False


def send_push_to_user(user, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> int:
    """
    특정 사용자의 모든 활성 디바이스에 푸시 알림 발송

    Args:
        user: User 인스턴스
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 (선택)

    Returns:
        int: 성공적으로 발송된 개수
    """
    from api.models import PushToken

    tokens = PushToken.objects.filter(user=user, is_active=True)
    success_count = 0

    for push_token in tokens:
        try:
            if push_token.platform == 'ios':
                success = send_apns_push(push_token.token, title, body, data)
            else:  # android or web
                success = send_fcm_push(push_token.token, title, body, data)

            if success:
                success_count += 1
            else:
                # 푸시 발송 실패 시 토큰 비활성화 (선택)
                # push_token.is_active = False
                # push_token.save()
                pass

        except Exception as e:
            logger.error(f"Error sending push to token {push_token.id}: {str(e)}")

    return success_count
