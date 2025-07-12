from rest_framework import serializers
from .models import Notification, GroupBuy
import re

class NotificationSerializer(serializers.ModelSerializer):
    """
    알림 데이터를 위한 시리얼라이저
    
    사용자에게 전송된 알림 정보를 관리합니다.
    """
    user_name = serializers.CharField(source='user.username', read_only=True)
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    message = serializers.SerializerMethodField()
    
    def get_message(self, obj):
        """
        알림 메시지 내의 영문 상태값을 한글로 변환합니다.
        예: 'completed'를 '완료'로 변환
        """
        message = obj.message
        
        # GroupBuy 모델의 STATUS_CHOICES에서 상태 코드와 한글 표시 매핑 가져오기
        status_mapping = dict(GroupBuy.STATUS_CHOICES)
        
        # 정규식을 사용하여 메시지 내의 영문 상태값을 한글로 변환
        for status_code, status_display in status_mapping.items():
            pattern = r'상태가 ' + re.escape(status_code) + r'로'
            if re.search(pattern, message):
                message = message.replace(f'상태가 {status_code}로', f'상태가 {status_display}로')
        
        return message
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'groupbuy', 'groupbuy_title', 
            'message', 'created_at', 'is_read'
        ]
        read_only_fields = ['user', 'groupbuy', 'created_at']
