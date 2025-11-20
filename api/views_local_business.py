"""
지역 업체 정보 ViewSet
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.utils import timezone

from api.models_local_business import (
    LocalBusinessCategory,
    LocalBusiness,
    LocalBusinessView
)
from api.serializers_local_business import (
    LocalBusinessCategorySerializer,
    LocalBusinessListSerializer,
    LocalBusinessDetailSerializer
)


class LocalBusinessCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """업종 카테고리 ViewSet (읽기 전용)"""

    queryset = LocalBusinessCategory.objects.filter(is_active=True)
    serializer_class = LocalBusinessCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """활성화된 카테고리만 정렬순으로"""
        return self.queryset.order_by('order_index', 'name')


class LocalBusinessViewSet(viewsets.ReadOnlyModelViewSet):
    """지역 업체 ViewSet (읽기 전용)"""

    queryset = LocalBusiness.objects.select_related(
        'category', 'region'
    ).prefetch_related('links')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'region', 'is_verified', 'is_new']
    search_fields = ['name', 'address']
    ordering_fields = ['popularity_score', 'rating', 'review_count', 'rank_in_region', 'created_at']
    ordering = ['rank_in_region']  # 기본 정렬: 순위순

    def get_serializer_class(self):
        """액션별 Serializer 선택"""
        if self.action == 'retrieve':
            return LocalBusinessDetailSerializer
        return LocalBusinessListSerializer

    def retrieve(self, request, *args, **kwargs):
        """상세 조회 시 조회수 증가"""
        instance = self.get_object()

        # 조회수 증가
        LocalBusiness.objects.filter(pk=instance.pk).update(
            view_count=F('view_count') + 1
        )

        # 조회 로그 기록
        ip_address = self.get_client_ip(request)
        LocalBusinessView.objects.create(
            business=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address
        )

        # 인스턴스 새로고침 (view_count 업데이트 반영)
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @action(detail=False, methods=['get'])
    def by_region_category(self, request):
        """지역+업종별 상위 업체 조회

        Query Params:
            - region: 지역 코드 (예: 1111010100)
            - category: 카테고리 ID
            - limit: 조회 개수 (기본: 5)
        """
        region_code = request.query_params.get('region')
        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 5))

        if not region_code or not category_id:
            return Response(
                {'error': 'region과 category 파라미터가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        businesses = self.queryset.filter(
            region__code=region_code,
            category_id=category_id
        ).order_by('rank_in_region')[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """인기 업체 조회 (전체)

        Query Params:
            - category: 카테고리 ID (선택)
            - limit: 조회 개수 (기본: 10)
        """
        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))

        businesses = self.queryset.order_by('-popularity_score')

        if category_id:
            businesses = businesses.filter(category_id=category_id)

        businesses = businesses[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new(self, request):
        """신규 업체 조회

        Query Params:
            - category: 카테고리 ID (선택)
            - limit: 조회 개수 (기본: 10)
        """
        category_id = request.query_params.get('category')
        limit = int(request.query_params.get('limit', 10))

        businesses = self.queryset.filter(
            is_new=True
        ).order_by('-created_at')

        if category_id:
            businesses = businesses.filter(category_id=category_id)

        businesses = businesses[:limit]

        serializer = self.get_serializer(businesses, many=True)
        return Response(serializer.data)
