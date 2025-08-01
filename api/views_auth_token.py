from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers_jwt import CustomTokenObtainPairSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_user_token(request):
    """
    현재 사용자의 JWT 토큰을 강제로 새로 발급
    role이 잘못된 경우 사용할 수 있는 엔드포인트
    """
    try:
        user = request.user
        
        # 새로운 토큰 발급
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # CustomTokenObtainPairSerializer의 get_token 메서드 사용하여 
        # 추가 클레임 포함
        token_serializer = CustomTokenObtainPairSerializer()
        token = token_serializer.get_token(user)
        
        # 새로운 access token에 클레임 추가
        for key, value in token.payload.items():
            if key not in ['token_type', 'exp', 'iat', 'jti', 'user_id']:
                access_token[key] = value
        
        logger.info(f"토큰 갱신 - User ID: {user.id}, Role: {user.role}")
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_superuser': user.is_superuser
            }
        })
        
    except Exception as e:
        logger.error(f"토큰 갱신 오류: {str(e)}")
        return Response(
            {'error': '토큰 갱신 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_token_role(request):
    """
    현재 JWT 토큰의 role 정보와 DB의 role 정보 비교
    디버깅용 엔드포인트
    """
    try:
        user = request.user
        
        # JWT 토큰에서 role 가져오기
        token_role = getattr(request.auth, 'payload', {}).get('role', 'unknown')
        
        # DB에서 실제 role 가져오기
        db_role = user.role
        
        response_data = {
            'user_id': user.id,
            'username': user.username,
            'token_role': token_role,
            'db_role': db_role,
            'role_match': token_role == db_role,
            'is_superuser': user.is_superuser,
            'message': '토큰과 DB의 role이 일치합니다.' if token_role == db_role else '토큰과 DB의 role이 다릅니다. 토큰을 갱신해주세요.'
        }
        
        if token_role != db_role:
            logger.warning(f"Role 불일치 - User ID: {user.id}, Token role: {token_role}, DB role: {db_role}")
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"토큰 검증 오류: {str(e)}")
        return Response(
            {'error': '토큰 검증 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )