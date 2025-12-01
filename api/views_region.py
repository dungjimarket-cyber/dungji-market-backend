import logging
from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta
from .models_region import Region
from .serializers_region import RegionSerializer, RegionDetailSerializer, RegionTreeSerializer

logger = logging.getLogger(__name__)

# 지역 변경 제한 기간 (90일)
REGION_CHANGE_LIMIT_DAYS = 90


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def region_change_status(request):
    """
    사용자의 지역 변경 가능 상태를 확인하는 API

    Returns:
        - can_change: 변경 가능 여부
        - next_available_date: 다음 변경 가능 날짜 (변경 불가능한 경우)
        - days_remaining: 남은 일수 (변경 불가능한 경우)
        - last_changed_at: 마지막 변경일
    """
    try:
        user = request.user

        # 첫 설정인 경우 (지역이 없거나 변경 이력이 없는 경우)
        if not user.address_region or not user.region_last_changed_at:
            return Response({
                'can_change': True,
                'next_available_date': None,
                'days_remaining': 0,
                'last_changed_at': None,
                'is_first_setting': not user.address_region,
                'message': '지역을 설정해주세요.' if not user.address_region else '지역 변경이 가능합니다.'
            })

        # 90일 제한 체크
        limit_date = user.region_last_changed_at + timedelta(days=REGION_CHANGE_LIMIT_DAYS)
        now = timezone.now()

        if now >= limit_date:
            # 90일이 지났으면 변경 가능
            return Response({
                'can_change': True,
                'next_available_date': None,
                'days_remaining': 0,
                'last_changed_at': user.region_last_changed_at.isoformat(),
                'is_first_setting': False,
                'message': '지역 변경이 가능합니다.'
            })
        else:
            # 아직 90일이 안 지났음
            days_remaining = (limit_date - now).days + 1
            return Response({
                'can_change': False,
                'next_available_date': limit_date.isoformat(),
                'days_remaining': days_remaining,
                'last_changed_at': user.region_last_changed_at.isoformat(),
                'is_first_setting': False,
                'message': f'지역 변경은 {days_remaining}일 후에 가능합니다.'
            })

    except Exception as e:
        logger.error(f"지역 변경 상태 확인 오류: {str(e)}")
        # 에러 시에도 변경 가능한 상태로 반환 (사용자 차단 방지)
        return Response({
            'can_change': True,
            'next_available_date': None,
            'days_remaining': 0,
            'last_changed_at': None,
            'is_first_setting': True,
            'message': '지역 변경이 가능합니다.'
        })


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    지역 정보 API 뷰셋
    """
    queryset = Region.objects.filter(is_active=True)
    serializer_class = RegionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['level', 'parent']
    search_fields = ['name', 'full_name']
    permission_classes = [permissions.AllowAny]  # 인증 없이도 접근 가능하도록 설정
    
    def get_serializer_class(self):
        """요청에 따라 적절한 시리얼라이저 반환"""
        if self.action == 'retrieve':
            return RegionDetailSerializer
        elif self.action == 'tree':
            return RegionTreeSerializer
        return RegionSerializer
    
    def get_queryset(self):
        """요청에 따라 쿼리셋 필터링"""
        queryset = super().get_queryset()
        
        # 레벨별 필터링
        level = self.request.query_params.get('level')
        if level is not None:
            try:
                level = int(level)
                queryset = queryset.filter(level=level)
            except ValueError:
                pass
        
        # 상위 지역 코드로 필터링
        parent_code = self.request.query_params.get('parent_code')
        if parent_code:
            queryset = queryset.filter(parent__code=parent_code)
        
        # 루트 레벨만 필터링 (시/도)
        root_only = self.request.query_params.get('root_only')
        if root_only and root_only.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(level=0)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """특정 지역의 하위 지역 목록 반환"""
        region = self.get_object()
        children = region.get_children()
        serializer = RegionSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """특정 지역의 계층 구조 반환 (상위 및 하위 지역)"""
        region = self.get_object()
        serializer = RegionTreeSerializer(region)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_by_name(self, request):
        """지역명으로 검색"""
        name = request.query_params.get('name', '')
        if len(name) < 2:
            return Response(
                {"error": "검색어는 2글자 이상이어야 합니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        regions = self.queryset.filter(name__icontains=name)
        serializer = RegionSerializer(regions, many=True)
        return Response(serializer.data)
