"""
팝업 시리얼라이저
"""
from rest_framework import serializers
from .models_popup import Popup


class PopupListSerializer(serializers.ModelSerializer):
    """팝업 목록 시리얼라이저"""
    
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Popup
        fields = [
            'id', 'title', 'popup_type', 'content', 'image',
            'link_url', 'link_target', 'position', 'position_x', 'position_y',
            'width', 'height', 'show_today_close', 'show_week_close',
            'is_valid', 'priority'
        ]
    
    def get_is_valid(self, obj):
        """현재 시간 기준 유효성 확인"""
        return obj.is_valid_period()


class PopupDetailSerializer(serializers.ModelSerializer):
    """팝업 상세 시리얼라이저"""
    
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Popup
        fields = '__all__'
        read_only_fields = ['view_count', 'click_count', 'created_at', 'updated_at']
    
    def get_is_valid(self, obj):
        """현재 시간 기준 유효성 확인"""
        return obj.is_valid_period()


class PopupCreateSerializer(serializers.ModelSerializer):
    """팝업 생성 시리얼라이저 (관리자용)"""
    
    class Meta:
        model = Popup
        exclude = ['view_count', 'click_count', 'author']
    
    def create(self, validated_data):
        """팝업 생성"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PopupUpdateSerializer(serializers.ModelSerializer):
    """팝업 수정 시리얼라이저 (관리자용)"""
    
    class Meta:
        model = Popup
        exclude = ['view_count', 'click_count', 'author', 'created_at']