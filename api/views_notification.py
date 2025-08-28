from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Notification
from .serializers_notification import NotificationSerializer
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
