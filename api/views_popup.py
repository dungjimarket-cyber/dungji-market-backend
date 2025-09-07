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
from .permissions import IsAdminRole


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
        return [IsAdminRole()]
    
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
        
        # 디버그 로그
        import logging
        logger = logging.getLogger(__name__)
        
        # 메인 페이지에 표시할 팝업 - 더 간단한 쿼리로 시작
        popups = Popup.objects.filter(
            is_active=True,
            show_on_main=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by('-priority', '-created_at')
        
        logger.info(f"Active popups query count: {popups.count()}")
        logger.info(f"Active popups: {list(popups.values('id', 'title', 'is_active', 'show_on_main'))}")
        
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
    
    @action(detail=False, methods=['get'])
    def debug_popups(self, request):
        """디버그용 - 모든 팝업 확인"""
        from django.utils import timezone
        now = timezone.now()
        
        all_popups = Popup.objects.all()
        active_popups = Popup.objects.filter(is_active=True)
        main_popups = Popup.objects.filter(is_active=True, show_on_main=True)
        valid_popups = Popup.objects.filter(
            is_active=True,
            show_on_main=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        
        return Response({
            'current_time': now,
            'all_popups_count': all_popups.count(),
            'active_popups_count': active_popups.count(),
            'main_popups_count': main_popups.count(),
            'valid_popups_count': valid_popups.count(),
            'all_popups': list(all_popups.values('id', 'title', 'is_active', 'show_on_main', 'start_date', 'end_date')),
            'valid_popups': list(valid_popups.values('id', 'title', 'is_active', 'show_on_main', 'start_date', 'end_date'))
        })
    
    @action(detail=True, methods=['post'])
    def record_view(self, request, pk=None):
        """팝업 조회수 증가"""
        try:
            popup = Popup.objects.get(pk=pk)
            popup.increment_view_count()
            return Response({'status': 'view recorded', 'view_count': popup.view_count})
        except Popup.DoesNotExist:
            return Response({'error': 'Popup not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def record_click(self, request, pk=None):
        """팝업 클릭수 증가"""
        try:
            popup = Popup.objects.get(pk=pk)
            popup.increment_click_count()
            return Response({'status': 'click recorded', 'click_count': popup.click_count})
        except Popup.DoesNotExist:
            return Response({'error': 'Popup not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)