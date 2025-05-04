from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers_jwt import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    역할 정보가 포함된 JWT 토큰을 제공하는 커스텀 뷰
    """
    serializer_class = CustomTokenObtainPairSerializer
