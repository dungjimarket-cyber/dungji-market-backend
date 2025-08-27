"""
이메일 인증 관련 API 뷰
비밀번호 재설정, 이메일 확인 등
"""

import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from api.utils.email_auth_service import email_auth_service

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    비밀번호 재설정 요청
    이메일로 재설정 링크 발송
    """
    try:
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({
                'success': False,
                'message': '이메일을 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 확인
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 보안상 사용자가 존재하지 않아도 성공 응답
            logger.warning(f"비밀번호 재설정 요청 - 존재하지 않는 이메일: {email}")
            return Response({
                'success': True,
                'message': '입력하신 이메일로 비밀번호 재설정 링크를 발송했습니다.'
            })
        
        # 비밀번호 재설정 이메일 발송
        success, result = email_auth_service.send_password_reset_email(email, user)
        
        if success:
            logger.info(f"비밀번호 재설정 이메일 발송 성공: {email}")
            return Response({
                'success': True,
                'message': '입력하신 이메일로 비밀번호 재설정 링크를 발송했습니다.'
            })
        else:
            logger.error(f"비밀번호 재설정 이메일 발송 실패: {email}, {result}")
            return Response({
                'success': False,
                'message': '이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"비밀번호 재설정 요청 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_token(request):
    """
    비밀번호 재설정 토큰 검증
    """
    try:
        email = request.data.get('email', '').strip().lower()
        token = request.data.get('token', '').strip()
        
        if not email or not token:
            return Response({
                'success': False,
                'message': '이메일과 토큰이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 토큰 검증
        is_valid = email_auth_service.verify_reset_token(email, token)
        
        if is_valid:
            return Response({
                'success': True,
                'message': '유효한 토큰입니다.'
            })
        else:
            return Response({
                'success': False,
                'message': '유효하지 않거나 만료된 토큰입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"토큰 검증 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '토큰 검증에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    비밀번호 재설정
    """
    try:
        email = request.data.get('email', '').strip().lower()
        token = request.data.get('token', '').strip()
        new_password = request.data.get('password', '').strip()
        
        # 필수 필드 확인
        if not all([email, token, new_password]):
            return Response({
                'success': False,
                'message': '모든 필드를 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 비밀번호 강도 확인
        if len(new_password) < 8:
            return Response({
                'success': False,
                'message': '비밀번호는 최소 8자 이상이어야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 토큰 검증
        if not email_auth_service.verify_reset_token(email, token):
            return Response({
                'success': False,
                'message': '유효하지 않거나 만료된 토큰입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 찾기
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': '사용자를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 비밀번호 변경
        user.password = make_password(new_password)
        user.save()
        
        # 토큰 삭제
        email_auth_service.clear_reset_token(email)
        
        logger.info(f"비밀번호 재설정 성공: {email}")
        
        return Response({
            'success': True,
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '비밀번호 재설정에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_email(request):
    """
    이메일 인증 코드 발송
    """
    try:
        email = request.data.get('email', '').strip().lower()
        name = request.data.get('name', '').strip()
        
        if not email:
            return Response({
                'success': False,
                'message': '이메일을 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 이메일 중복 확인 (회원가입의 경우)
        purpose = request.data.get('purpose', 'email_verification')
        if purpose == 'signup':
            if User.objects.filter(email=email).exists():
                return Response({
                    'success': False,
                    'message': '이미 사용중인 이메일입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 인증 이메일 발송
        success, result = email_auth_service.send_verification_email(email, name)
        
        if success:
            logger.info(f"인증 이메일 발송 성공: {email}")
            return Response({
                'success': True,
                'message': '인증 코드를 이메일로 발송했습니다.'
            })
        else:
            logger.error(f"인증 이메일 발송 실패: {email}, {result}")
            return Response({
                'success': False,
                'message': '이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"인증 이메일 발송 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_code(request):
    """
    이메일 인증 코드 확인
    """
    try:
        email = request.data.get('email', '').strip().lower()
        code = request.data.get('code', '').strip()
        purpose = request.data.get('purpose', 'email_verification')
        
        if not email or not code:
            return Response({
                'success': False,
                'message': '이메일과 인증 코드를 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 인증 코드 확인
        is_valid = email_auth_service.verify_code(email, code, purpose)
        
        if is_valid:
            logger.info(f"이메일 인증 성공: {email}")
            return Response({
                'success': True,
                'message': '이메일 인증이 완료되었습니다.'
            })
        else:
            logger.warning(f"이메일 인증 실패: {email}")
            return Response({
                'success': False,
                'message': '잘못된 인증 코드이거나 만료되었습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"이메일 인증 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '인증에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_email(request):
    """
    이메일 주소 변경 (로그인한 사용자)
    """
    try:
        user = request.user
        new_email = request.data.get('email', '').strip().lower()
        code = request.data.get('code', '').strip()
        
        if not new_email:
            return Response({
                'success': False,
                'message': '새 이메일 주소를 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 이메일 중복 확인
        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            return Response({
                'success': False,
                'message': '이미 사용중인 이메일입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 인증 코드 확인
        if code:
            if not email_auth_service.verify_code(new_email, code, 'email_change'):
                return Response({
                    'success': False,
                    'message': '잘못된 인증 코드이거나 만료되었습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 이메일 변경
            user.email = new_email
            user.save()
            
            logger.info(f"이메일 변경 성공: {user.username} -> {new_email}")
            
            return Response({
                'success': True,
                'message': '이메일이 성공적으로 변경되었습니다.'
            })
        else:
            # 인증 이메일 발송
            success, result = email_auth_service.send_verification_email(new_email, user.name)
            
            if success:
                # purpose를 email_change로 재저장
                email_auth_service.store_verification_code(new_email, result, 'email_change')
                
                return Response({
                    'success': True,
                    'message': '새 이메일로 인증 코드를 발송했습니다.',
                    'require_verification': True
                })
            else:
                return Response({
                    'success': False,
                    'message': '인증 이메일 발송에 실패했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    except Exception as e:
        logger.error(f"이메일 변경 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '이메일 변경에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)