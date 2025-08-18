from rest_framework import serializers
from .models_inquiry import Inquiry


class InquirySerializer(serializers.ModelSerializer):
    """문의사항 시리얼라이저"""
    
    class Meta:
        model = Inquiry
        fields = [
            'id', 'title', 'content', 'status', 'answer', 
            'answered_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'answer', 'answered_at', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class InquiryDetailSerializer(serializers.ModelSerializer):
    """문의사항 상세 시리얼라이저 (관리자용)"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Inquiry
        fields = [
            'id', 'user_name', 'user_email', 'title', 'content', 
            'status', 'answer', 'answered_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_name', 'user_email', 'created_at', 'updated_at']