from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers_jwt import CustomTokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import FindUsernameSerializer, ResetPasswordSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    역할 정보가 포함된 JWT 토큰을 제공하는 커스텀 뷰
    """
    serializer_class = CustomTokenObtainPairSerializer

class FindUsernameView(APIView):
    """
    이메일로 가입된 아이디(유저명) 찾기
    로그인하지 않은 상태에서도 사용 가능
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = FindUsernameSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.get_username()
            # 일부 마스킹(앞 2글자 + ****)
            masked = username[:2] + '*' * (len(username)-2)
            return Response({'username': masked}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    """
    이메일+아이디로 임시 비밀번호 발급
    로그인하지 않은 상태에서도 사용 가능
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': '임시 비밀번호가 이메일로 발송되었습니다.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
