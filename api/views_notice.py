"""
공지사항 뷰
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.db.models import Q, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models_notice import Notice, NoticeImage, NoticeComment
from .serializers_notice import (
    NoticeListSerializer,
    NoticeDetailSerializer,
    NoticeCreateSerializer,
    NoticeUpdateSerializer,
    NoticeCommentSerializer,
    NoticeImageSerializer
)


class NoticeViewSet(viewsets.ModelViewSet):
    """공지사항 뷰셋"""
    
    queryset = Notice.objects.filter(is_published=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['created_at', 'published_at', 'view_count', 'is_pinned']
    ordering = ['-is_pinned', '-published_at']
    filterset_fields = ['category', 'is_pinned']
    
    def get_permissions(self):
        """권한 설정"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['create_comment', 'update_comment', 'delete_comment']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """액션별 시리얼라이저"""
        if self.action == 'list':
            return NoticeListSerializer
        elif self.action == 'retrieve':
            return NoticeDetailSerializer
        elif self.action == 'create':
            return NoticeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NoticeUpdateSerializer
        elif self.action in ['create_comment', 'update_comment']:
            return NoticeCommentSerializer
        return NoticeDetailSerializer
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = super().get_queryset()
        
        # 관리자가 아닌 경우 게시된 공지만 표시
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                Q(published_at__lte=now) | Q(published_at__isnull=True)
            )
        
        # 카테고리 필터
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 검색어 필터
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(summary__icontains=search)
            )
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """공지사항 상세 조회"""
        instance = self.get_object()
        
        # 조회수 증가
        instance.increase_view_count()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pinned(self, request):
        """상단 고정 공지사항 목록"""
        queryset = self.get_queryset().filter(is_pinned=True)
        serializer = NoticeListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """최근 공지사항 (7일 이내)"""
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        queryset = self.get_queryset().filter(
            published_at__gte=seven_days_ago
        )
        serializer = NoticeListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """카테고리 목록"""
        categories = [
            {'value': choice[0], 'label': choice[1]}
            for choice in Notice.CATEGORY_CHOICES
        ]
        return Response(categories)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def create_comment(self, request, pk=None):
        """댓글 작성"""
        notice = self.get_object()
        serializer = NoticeCommentSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(
                notice=notice,
                author=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put'], permission_classes=[IsAuthenticated])
    def update_comment(self, request, pk=None):
        """댓글 수정"""
        notice = self.get_object()
        comment_id = request.data.get('comment_id')
        
        try:
            comment = notice.comments.get(
                id=comment_id,
                author=request.user
            )
        except NoticeComment.DoesNotExist:
            return Response(
                {'error': '댓글을 찾을 수 없거나 권한이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = NoticeCommentSerializer(
            comment,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def delete_comment(self, request, pk=None):
        """댓글 삭제"""
        notice = self.get_object()
        comment_id = request.query_params.get('comment_id')
        
        try:
            comment = notice.comments.get(
                id=comment_id,
                author=request.user
            )
        except NoticeComment.DoesNotExist:
            return Response(
                {'error': '댓글을 찾을 수 없거나 권한이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 소프트 삭제
        comment.is_active = False
        comment.save()
        
        return Response(
            {'message': '댓글이 삭제되었습니다.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def upload_image(self, request, pk=None):
        """이미지 업로드 (관리자용)"""
        notice = self.get_object()
        image_file = request.FILES.get('image')
        caption = request.data.get('caption', '')
        
        if not image_file:
            return Response(
                {'error': '이미지 파일이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notice_image = NoticeImage.objects.create(
            notice=notice,
            image=image_file,
            caption=caption
        )
        
        serializer = NoticeImageSerializer(notice_image)
        return Response(serializer.data, status=status.HTTP_201_CREATED)