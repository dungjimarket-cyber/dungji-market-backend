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


def is_twa_app(request):
    """
    TWA(Trusted Web Activity) 앱 여부 감지

    User-Agent와 Referrer를 통해 Play Store TWA 앱인지 판단
    """
    import logging
    logger = logging.getLogger(__name__)

    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    referrer = request.META.get('HTTP_REFERER', '')

    # 디버깅 로그
    logger.info(f"[TWA Detection] User-Agent: {user_agent}")
    logger.info(f"[TWA Detection] Referrer: {referrer}")

    # android-app:// referrer는 확실한 TWA 표시
    if 'android-app://' in referrer:
        logger.info("[TWA Detection] Result: True (android-app referrer)")
        return True

    # User-Agent에서 WebView 표시 확인
    # TWA는 Chrome WebView 기반이므로 'wv' 포함
    if 'wv' in user_agent:
        logger.info("[TWA Detection] Result: True (wv in user agent)")
        return True

    # Samsung Browser 패턴 확인
    # Samsung Browser는 TWA 앱으로 실행될 때 특정 패턴을 가짐
    is_android = 'android' in user_agent
    is_samsung = 'samsungbrowser' in user_agent

    if is_android and is_samsung:
        # Samsung Browser는 일반 브라우저와 TWA 앱 구분이 어려움
        # 하지만 앱 패키지로 실행되면 보통 Version/ 태그가 없음
        # 또는 AppleWebKit만 있고 Chrome이 없음
        has_chrome = 'chrome' in user_agent

        # Samsung Browser + Android면 TWA로 간주
        # (일반 Samsung Browser로 웹 접속 시에는 보통 Mobile 태그가 더 명확함)
        logger.info(f"[TWA Detection] Result: True (Samsung Browser on Android, has_chrome={has_chrome})")
        return True

    # 추가 패턴: Android + Chrome + Mobile 조합
    is_chrome = 'chrome' in user_agent
    is_mobile = 'mobile' in user_agent

    # WebView 특성: Version/ 태그 확인
    has_version = 'version/' in user_agent

    if is_android and is_chrome and is_mobile and has_version:
        logger.info(f"[TWA Detection] Result: True (android+chrome+mobile+version)")
        return True

    logger.info(f"[TWA Detection] Result: False (is_android={is_android}, is_chrome={is_chrome}, is_mobile={is_mobile}, has_version={has_version}, is_samsung={is_samsung})")
    return False


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
        """활성 팝업 목록 (페이지별)"""
        now = timezone.now()
        page_type = request.query_params.get('page_type', 'main')

        # 기본 필터
        popups = Popup.objects.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )

        # 페이지 타입별 필터링
        if page_type == 'main':
            popups = popups.filter(show_on_main=True)
        elif page_type == 'groupbuy_list':
            popups = popups.filter(show_on_groupbuy_list=True)
        elif page_type == 'groupbuy_detail':
            popups = popups.filter(show_on_groupbuy_detail=True)
        elif page_type == 'used_list':
            popups = popups.filter(show_on_used_list=True)
        elif page_type == 'used_detail':
            popups = popups.filter(show_on_used_detail=True)
        elif page_type == 'mypage':
            popups = popups.filter(show_on_mypage=True)

        # TWA 앱 필터링
        is_twa = is_twa_app(request)
        if is_twa:
            # TWA 앱에서는 hide_on_twa_app=True인 팝업 제외
            popups = popups.exclude(hide_on_twa_app=True)
        else:
            # 웹에서는 show_only_on_twa_app=True인 팝업 제외
            popups = popups.exclude(show_only_on_twa_app=True)

        # 우선순위 정렬
        popups = popups.order_by('-priority', '-created_at')

        # 쿠키에서 오늘/일주일 숨김 팝업 확인
        hidden_today = request.COOKIES.get('hidden_popups_today', '').split(',')
        hidden_week = request.COOKIES.get('hidden_popups_week', '').split(',')

        # 숨김 처리된 팝업 제외
        if hidden_today[0]:  # 빈 문자열이 아닌 경우
            popups = popups.exclude(id__in=hidden_today)
        if hidden_week[0]:  # 빈 문자열이 아닌 경우
            popups = popups.exclude(id__in=hidden_week)

        serializer = PopupListSerializer(popups, many=True)

        # 디버그 정보 포함 (개발용)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referrer = request.META.get('HTTP_REFERER', '')

        return Response({
            'results': serializer.data,
            'debug_info': {
                'is_twa_detected': is_twa,
                'user_agent': user_agent,
                'referrer': referrer,
                'total_popups': len(serializer.data)
            }
        })
    
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