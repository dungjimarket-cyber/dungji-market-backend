"""
공지사항 시리얼라이저
"""
from rest_framework import serializers
from .models_notice import Notice, NoticeImage, NoticeComment
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class NoticeImageSerializer(serializers.ModelSerializer):
    """공지사항 이미지 시리얼라이저"""
    
    class Meta:
        model = NoticeImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class NoticeCommentSerializer(serializers.ModelSerializer):
    """공지사항 댓글 시리얼라이저"""
    
    author_name = serializers.CharField(source='author.username', read_only=True)
    is_mine = serializers.SerializerMethodField()
    
    class Meta:
        model = NoticeComment
        fields = [
            'id', 'author', 'author_name', 'content',
            'is_active', 'created_at', 'updated_at', 'is_mine'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']
    
    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.author == request.user
        return False


class NoticeListSerializer(serializers.ModelSerializer):
    """공지사항 목록 시리얼라이저"""
    
    author_name = serializers.CharField(source='author.username', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    
    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'category', 'category_display', 'summary', 'content',
            'author_name', 'is_pinned', 'is_new', 'view_count',
            'comment_count', 'created_at', 'updated_at', 'published_at', 'thumbnail',
            'show_in_main', 'display_type', 'main_banner_image', 'banner_link', 'main_display_order'
        ]


class NoticeDetailSerializer(serializers.ModelSerializer):
    """공지사항 상세 시리얼라이저"""
    
    author_name = serializers.CharField(source='author.username', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    images = NoticeImageSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    prev_notice = serializers.SerializerMethodField()
    next_notice = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'category', 'category_display', 'content', 'summary',
            'author', 'author_name', 'is_pinned', 'is_published', 'is_new',
            'view_count', 'created_at', 'updated_at', 'published_at',
            'meta_title', 'meta_description', 'thumbnail', 'images',
            'comments', 'prev_notice', 'next_notice'
        ]
        read_only_fields = [
            'author', 'view_count', 'created_at', 'updated_at'
        ]
    
    def get_comments(self, obj):
        """활성 댓글만 반환"""
        comments = obj.comments.filter(is_active=True)
        return NoticeCommentSerializer(
            comments,
            many=True,
            context=self.context
        ).data
    
    def get_prev_notice(self, obj):
        """이전 공지사항"""
        prev = Notice.objects.filter(
            is_published=True,
            published_at__lt=obj.published_at or obj.created_at
        ).first()
        
        if prev:
            return {
                'id': prev.id,
                'title': prev.title,
                'category': prev.get_category_display()
            }
        return None
    
    def get_next_notice(self, obj):
        """다음 공지사항"""
        next_notice = Notice.objects.filter(
            is_published=True,
            published_at__gt=obj.published_at or obj.created_at
        ).last()
        
        if next_notice:
            return {
                'id': next_notice.id,
                'title': next_notice.title,
                'category': next_notice.get_category_display()
            }
        return None


class NoticeCreateSerializer(serializers.ModelSerializer):
    """공지사항 생성 시리얼라이저 (관리자용)"""
    
    class Meta:
        model = Notice
        fields = [
            'title', 'category', 'content', 'summary',
            'is_pinned', 'is_published', 'published_at',
            'meta_title', 'meta_description', 'thumbnail'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['author'] = request.user
        return super().create(validated_data)


class NoticeUpdateSerializer(serializers.ModelSerializer):
    """공지사항 수정 시리얼라이저 (관리자용)"""
    
    class Meta:
        model = Notice
        fields = [
            'title', 'category', 'content', 'summary',
            'is_pinned', 'is_published', 'published_at',
            'meta_title', 'meta_description', 'thumbnail'
        ]