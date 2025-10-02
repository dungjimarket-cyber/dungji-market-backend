"""
푸시 알림 발송 유틸리티
FCM (Firebase Cloud Messaging) 및 APNs (Apple Push Notification service) 연동
"""
import json
import logging
import requests
from django.conf import settings
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os

logger = logging.getLogger(__name__)


def get_access_token():
    """
    Firebase Service Account를 사용하여 Access Token 생성
    환경변수 또는 파일에서 읽기
    """
    try:
        # 1. 환경변수에서 읽기 (Vercel 등 클라우드 환경)
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')

        if service_account_json:
            logger.info("Using Firebase credentials from environment variable")
            service_account_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
        else:
            # 2. 파일에서 읽기 (로컬 개발 환경)
            service_account_path = os.path.join(settings.BASE_DIR, 'firebase-service-account.json')

            if not os.path.exists(service_account_path):
                logger.warning("Firebase credentials not found in environment or file. Skipping push notification.")
                return None

            logger.info("Using Firebase credentials from file")
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )

        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None


def send_fcm_push(token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    FCM HTTP v1 API를 통해 푸시 알림 발송 (Android/Web/iOS)

    Args:
        token: FCM 디바이스 토큰
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 (선택)

    Returns:
        bool: 발송 성공 여부
    """
    try:
        access_token = get_access_token()
        if not access_token:
            return False

        project_id = "dungji-market-7c0e0"
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; UTF-8",
        }

        # 알림 타입에 따라 URL 결정
        if data and data.get('type') == 'used':
            link_url = "https://www.dungjimarket.com/used/mypage"
        else:
            link_url = "https://www.dungjimarket.com/mypage"

        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": data or {},
                "webpush": {
                    "fcm_options": {
                        "link": link_url
                    },
                    "notification": {
                        "icon": "/icons/icon-192x192.png",
                        "badge": "/icons/icon-96x96.png"
                    }
                }
            }
        }

        logger.info(f"Sending FCM to token: {token[:30]}... with title: {title}")
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info(f"✅ FCM SUCCESS - Status: {response.status_code}, Response: {response.text[:200]}")
            return True
        else:
            logger.error(f"❌ FCM FAILED - Status: {response.status_code}, Response: {response.text}")
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
