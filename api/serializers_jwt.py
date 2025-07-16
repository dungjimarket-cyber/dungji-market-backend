from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT 토큰에 사용자 역할 정보를 추가하는 커스텀 시리얼라이저
    """
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
