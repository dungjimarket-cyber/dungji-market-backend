from rest_framework import serializers
from .models import Banner, Event


class EventSerializer(serializers.ModelSerializer):
    """이벤트 Serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'event_type', 'event_type_display',
            'status', 'status_display', 'thumbnail_url', 'content_image_url',
            'content', 'short_description', 'start_date', 'end_date',
            'is_active', 'is_valid', 'view_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'status', 'view_count', 'created_at', 'updated_at']


class EventListSerializer(serializers.ModelSerializer):
    """이벤트 목록용 Serializer (간략한 정보만)"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'event_type', 'event_type_display',
            'status', 'status_display', 'thumbnail_url', 'short_description',
            'start_date', 'end_date', 'is_valid', 'view_count', 'created_at'
        ]


class BannerSerializer(serializers.ModelSerializer):
    """배너 Serializer"""
    banner_type_display = serializers.CharField(source='get_banner_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    event_detail = EventListSerializer(source='event', read_only=True)
    target_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'banner_type', 'banner_type_display',
            'image_url', 'link_url', 'target_url', 'event', 'event_detail',
            'order', 'is_active', 'is_valid', 'start_date', 'end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_target_url(self, obj):
        """실제 클릭 시 이동할 URL"""
        if obj.event:
            return f'/events/{obj.event.slug}'
        return obj.link_url or '#'