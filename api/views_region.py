from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models_region import Region
from .serializers_region import RegionSerializer, RegionDetailSerializer, RegionTreeSerializer


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
