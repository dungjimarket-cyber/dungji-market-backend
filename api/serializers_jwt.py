from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT 토큰에 사용자 역할 정보를 추가하는 커스텀 시리얼라이저
    """
    
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except serializers.ValidationError as e:
            # 기본 에러 메시지를 커스텀 메시지로 변경
            if 'No active account found with the given credentials' in str(e.detail.get('detail', '')):
                raise serializers.ValidationError(
                    {'detail': '아이디 또는 비밀번호가 일치하지 않습니다. 다시 확인해 주세요.'}
                )
            # 다른 에러는 그대로 전달
            raise e
        return data
    
    @classmethod
    def get_token(cls, user) -> Token:
        token = super().get_token(user)

        # 토큰에 사용자 역할 정보 추가
        # 슈퍼유저인 경우 role을 admin으로 설정
        if user.is_superuser:
            token['role'] = 'admin'
        else:
            token['role'] = user.role
        token['email'] = user.email
        token['is_superuser'] = user.is_superuser
        
        # 필요하다면 여기에 추가 정보(username 등)를 더 넣을 수 있습니다.
        token['username'] = user.username
        
        return token
