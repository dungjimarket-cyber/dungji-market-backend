"""
팝업 뷰셋
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Q
from .models_popup import Popup
from .serializers_popup import (
    PopupListSerializer,
    PopupDetailSerializer,
    PopupCreateSerializer,
    PopupUpdateSerializer
)
from .permissions import IsAdminUser


class PopupViewSet(viewsets.ModelViewSet):
    """팝업 뷰셋"""
    
    queryset = Popup.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 반환"""
        if self.action == 'list':
            return PopupListSerializer
        elif self.action == 'create':
            return PopupCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PopupUpdateSerializer
        return PopupDetailSerializer
    
    def get_permissions(self):
        """액션에 따른 권한 설정"""
        if self.action in ['list', 'retrieve', 'active_popups', 'record_view', 'record_click']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        """쿼리셋 반환"""
        queryset = super().get_queryset()
        
        # 관리자가 아닌 경우 활성화되고 유효한 기간의 팝업만
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
            
            # 페이지 필터링
            current_page = self.request.query_params.get('page', '/')
            if current_page:
                # show_pages가 비어있으면 모든 페이지, 있으면 해당 페이지만
                queryset = queryset.filter(
                    Q(show_pages__len=0) | Q(show_pages__contains=current_page)
                )
                # exclude_pages에 있으면 제외
                queryset = queryset.exclude(
                    exclude_pages__contains=current_page
                )
            
            # 모바일 필터링
            is_mobile = self.request.query_params.get('is_mobile', 'false').lower() == 'true'
            if is_mobile:
                queryset = queryset.filter(show_on_mobile=True)
        
        return queryset.order_by('-priority', '-created_at')
    
    @action(detail=False, methods=['get'])
    def active_popups(self, request):
        """활성 팝업 목록 (메인 페이지용)"""
        now = timezone.now()
        
        # 메인 페이지에 표시할 팝업
        popups = self.get_queryset().filter(
            show_on_main=True
        )
        
        # 쿠키에서 오늘/일주일 숨김 팝업 확인
        hidden_today = request.COOKIES.get('hidden_popups_today', '').split(',')
        hidden_week = request.COOKIES.get('hidden_popups_week', '').split(',')
        
        # 숨김 처리된 팝업 제외
        if hidden_today[0]:  # 빈 문자열이 아닌 경우
            popups = popups.exclude(id__in=hidden_today)
        if hidden_week[0]:  # 빈 문자열이 아닌 경우
            popups = popups.exclude(id__in=hidden_week)
        
        serializer = PopupListSerializer(popups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def record_view(self, request, pk=None):
        """팝업 조회수 증가"""
        popup = self.get_object()
        popup.increment_view_count()
        return Response({'status': 'view recorded'})
    
    @action(detail=True, methods=['post'])
    def record_click(self, request, pk=None):
        """팝업 클릭수 증가"""
        popup = self.get_object()
        popup.increment_click_count()
        return Response({'status': 'click recorded'})