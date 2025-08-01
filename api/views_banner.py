from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from .models import Banner, Event
from .serializers_banner import BannerSerializer, EventSerializer, EventListSerializer


class BannerListView(generics.ListAPIView):
    """활성화된 배너 목록 조회"""
    permission_classes = [AllowAny]
    serializer_class = BannerSerializer
    
    def get_queryset(self):
        now = timezone.now()
        # 활성화되고 기간이 유효한 배너만 반환
        queryset = Banner.objects.filter(
            is_active=True
        ).select_related('event')
        
        # 시작일이 설정된 경우 체크
        queryset = queryset.filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
        )
        
        # 종료일이 설정된 경우 체크
        queryset = queryset.filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        )
        
        return queryset.order_by('order', '-created_at')


class EventListView(generics.ListAPIView):
    """이벤트 목록 조회"""
    permission_classes = [AllowAny]
    serializer_class = EventListSerializer
    
    def get_queryset(self):
        queryset = Event.objects.filter(is_active=True)
        
        # 이벤트 타입 필터링
        event_type = self.request.query_params.get('type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # 상태 필터링
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 진행중인 이벤트만 보기
        ongoing_only = self.request.query_params.get('ongoing', None)
        if ongoing_only and ongoing_only.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                start_date__lte=now,
                end_date__gte=now
            )
        
        return queryset.order_by('-start_date')


class EventDetailView(generics.RetrieveAPIView):
    """이벤트 상세 조회"""
    permission_classes = [AllowAny]
    serializer_class = EventSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Event.objects.filter(is_active=True)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # 조회수 증가
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_main_banners(request):
    """메인 페이지용 배너 조회 (캐러셀용)"""
    now = timezone.now()
    
    banners = Banner.objects.filter(
        is_active=True
        # 모든 타입의 활성화된 배너를 메인에서 표시
    ).select_related('event').filter(
        models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
    ).order_by('order', '-created_at')[:10]  # 최대 10개까지만
    
    serializer = BannerSerializer(banners, many=True)
    return Response({
        'count': len(banners),
        'results': serializer.data
    })