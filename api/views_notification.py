from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Notification, NotificationSetting, PushToken
from .serializers_notification import NotificationSerializer
from .utils.push_notification import send_push_notification
import logging

logger = logging.getLogger(__name__)

class NotificationViewSet(viewsets.ModelViewSet):
    """
    알림 관리를 위한 API 뷰셋
    
    사용자별 알림 조회, 읽음 처리 등을 제공합니다.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """사용자별 알림 목록을 반환합니다. (최근 7일 이내만)"""
        seven_days_ago = timezone.now() - timedelta(days=7)
        return Notification.objects.filter(
            user=self.request.user,
            created_at__gte=seven_days_ago
        ).order_by('-created_at')
    
    def list(self, request):
        """
        사용자의 최근 7일 이내 알림을 조회합니다.
        읽지 않은 알림과 읽은 알림을 구분하여 반환합니다.
        """
        queryset = self.get_queryset()
        unread = queryset.filter(is_read=False)
        read = queryset.filter(is_read=True)
        
        unread_serializer = self.serializer_class(unread, many=True)
        read_serializer = self.serializer_class(read, many=True)
        
        return Response({
            'unread': unread_serializer.data,
            'read': read_serializer.data,
            'unread_count': unread.count()
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """특정 알림을 읽음 처리합니다."""
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """모든 알림을 읽음 처리합니다."""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

    @action(detail=False, methods=['get', 'patch'], url_path='settings')
    def notification_settings(self, request):
        """
        알림 설정 조회/수정
        GET: 현재 알림 설정 조회
        PATCH: 알림 설정 수정
        """
        # 설정이 없으면 생성
        settings, created = NotificationSetting.objects.get_or_create(user=request.user)

        if request.method == 'GET':
            return Response({
                'trade_notifications': settings.trade_notifications,
                'marketing_notifications': settings.marketing_notifications
            })

        elif request.method == 'PATCH':
            # 거래 알림 설정
            if 'trade_notifications' in request.data:
                settings.trade_notifications = request.data['trade_notifications']

            # 마케팅 알림 설정
            if 'marketing_notifications' in request.data:
                settings.marketing_notifications = request.data['marketing_notifications']

            settings.save()

            return Response({
                'message': '알림 설정이 업데이트되었습니다.',
                'trade_notifications': settings.trade_notifications,
                'marketing_notifications': settings.marketing_notifications
            })

    @action(detail=False, methods=['post'], url_path='register-token')
    def register_push_token(self, request):
        """
        푸시 토큰 등록
        FCM/APNs 디바이스 토큰을 등록합니다.
        """
        token = request.data.get('token')
        platform = request.data.get('platform')  # 'ios', 'android', 'web'

        if not token:
            return Response(
                {'error': '토큰이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if platform not in ['ios', 'android', 'web']:
            return Response(
                {'error': '잘못된 플랫폼입니다. (ios, android, web 중 선택)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 기존 토큰이 있으면 업데이트, 없으면 생성
        push_token, created = PushToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'is_active': True
            }
        )

        action_text = '등록' if created else '업데이트'
        logger.info(f"Push token {action_text}: user={request.user.id}, platform={platform}")

        return Response({
            'message': f'푸시 토큰이 {action_text}되었습니다.',
            'token_id': push_token.id
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='unregister-token')
    def unregister_push_token(self, request):
        """
        푸시 토큰 비활성화
        로그아웃 시 호출
        """
        token = request.data.get('token')

        if not token:
            return Response(
                {'error': '토큰이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 토큰 비활성화
        updated = PushToken.objects.filter(
            token=token,
            user=request.user
        ).update(is_active=False)

        if updated:
            logger.info(f"Push token deactivated: user={request.user.id}")
            return Response({'message': '푸시 토큰이 비활성화되었습니다.'})
        else:
            return Response(
                {'error': '토큰을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='test-push')
    def test_push_notification(self, request):
        """
        FCM 푸시 알림 테스트 엔드포인트
        특정 사용자 또는 현재 로그인한 사용자에게 테스트 푸시를 전송합니다.

        Body: { "username": "seller10" } (선택사항)
        """
        try:
            # username 파라미터가 있으면 해당 사용자에게, 없으면 현재 사용자에게
            target_username = request.data.get('username')

            if target_username:
                from .models import User
                try:
                    target_user = User.objects.get(username=target_username)
                except User.DoesNotExist:
                    return Response({
                        'error': f'사용자 "{target_username}"를 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                target_user = request.user

            # 대상 사용자의 활성 푸시 토큰 찾기
            push_tokens = PushToken.objects.filter(
                user=target_user,
                is_active=True
            )

            if not push_tokens.exists():
                return Response({
                    'error': 'FCM 토큰이 등록되어 있지 않습니다.',
                    'detail': f'사용자 "{target_user.username}"에게 등록된 활성 토큰이 없습니다.',
                    'target_user': target_user.username
                }, status=status.HTTP_400_BAD_REQUEST)

            results = []
            for push_token in push_tokens:
                try:
                    # FCM 푸시 전송
                    result = send_push_notification(
                        token=push_token.token,
                        title="테스트 알림",
                        body="FCM 푸시 알림이 정상적으로 작동합니다!",
                        data={'test': 'true', 'type': 'test'}
                    )

                    results.append({
                        'token_id': push_token.id,
                        'platform': push_token.platform,
                        'success': True,
                        'result': result
                    })
                    logger.info(f"Test push sent successfully to user={request.user.id}, token={push_token.id}")

                except Exception as e:
                    results.append({
                        'token_id': push_token.id,
                        'platform': push_token.platform,
                        'success': False,
                        'error': str(e)
                    })
                    logger.error(f"Test push failed for user={request.user.id}, token={push_token.id}: {str(e)}")

            return Response({
                'message': f'{len(results)}개의 토큰에 테스트 푸시를 전송했습니다.',
                'target_user': target_user.username,
                'results': results,
                'total_tokens': len(results),
                'successful': sum(1 for r in results if r['success'])
            })

        except Exception as e:
            logger.error(f"Test push notification error: {str(e)}")
            return Response({
                'error': '푸시 알림 전송 중 오류가 발생했습니다.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
