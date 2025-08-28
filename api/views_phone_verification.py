"""휴대폰 인증 관련 API 뷰"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import logging

from .models_verification import PhoneVerification
from .utils.sms_service import SMSService

logger = logging.getLogger(__name__)
User = get_user_model()


def get_client_ip(request):
    """클라이언트 IP 주소 가져오기"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([AllowAny])
def send_phone_verification(request):
    """휴대폰 인증번호 발송"""
    phone_number = request.data.get('phone_number', '').strip()
    purpose = request.data.get('purpose', 'signup')  # signup, profile
    
    if not phone_number:
        return Response({
            'success': False,
            'message': '휴대폰 번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 전화번호 형식 정규화
    phone_number = phone_number.replace('-', '').replace(' ', '')
    if not phone_number.startswith('01') or len(phone_number) not in [10, 11]:
        return Response({
            'success': False,
            'message': '올바른 휴대폰 번호 형식이 아닙니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # IP 주소 가져오기
    ip_address = get_client_ip(request)
    
    # 발송 제한 확인
    can_send, error_message = PhoneVerification.check_rate_limit(phone_number, ip_address)
    if not can_send:
        return Response({
            'success': False,
            'message': error_message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 회원가입 시 이미 등록된 번호인지 확인
    if purpose == 'signup':
        existing_user = User.objects.filter(
            phone_number=phone_number,
            phone_verified=True
        ).first()
        
        if existing_user:
            return Response({
                'success': False,
                'message': '이미 등록된 휴대폰 번호입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # 기존 pending 인증 만료 처리
            PhoneVerification.objects.filter(
                phone_number=phone_number,
                status='pending'
            ).update(status='expired')
            
            # 새 인증 생성
            verification = PhoneVerification.objects.create(
                phone_number=phone_number,
                purpose=purpose,
                ip_address=ip_address,
                user=request.user if request.user.is_authenticated else None
            )
            
            # SMS 발송
            sms_service = SMSService()
            success, error = sms_service.send_verification_code(
                phone_number, 
                verification.verification_code
            )
            
            if success:
                logger.info(f"인증번호 발송 성공: {phone_number}, code: {verification.verification_code}")
                return Response({
                    'success': True,
                    'message': '인증번호가 발송되었습니다. 3분 이내에 입력해주세요.',
                    'expires_at': verification.expires_at.isoformat()
                })
            else:
                verification.status = 'failed'
                verification.save()
                logger.error(f"SMS 발송 실패: {phone_number}, error: {error}")
                return Response({
                    'success': False,
                    'message': error or 'SMS 발송에 실패했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    except Exception as e:
        logger.error(f"인증번호 발송 오류: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': '인증번호 발송 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_phone(request):
    """휴대폰 인증번호 확인"""
    phone_number = request.data.get('phone_number', '').strip()
    verification_code = request.data.get('verification_code', '').strip()
    purpose = request.data.get('purpose', 'signup')
    
    if not phone_number or not verification_code:
        return Response({
            'success': False,
            'message': '휴대폰 번호와 인증번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 전화번호 형식 정규화
    phone_number = phone_number.replace('-', '').replace(' ', '')
    
    try:
        # 가장 최근의 유효한 인증 찾기
        verification = PhoneVerification.get_recent_verification(phone_number, purpose)
        
        if not verification:
            return Response({
                'success': False,
                'message': '유효한 인증 요청을 찾을 수 없습니다. 다시 인증을 요청해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 인증번호 확인
        success, message = verification.verify(verification_code)
        
        if success:
            # 프로필 수정인 경우 사용자 정보 업데이트
            if purpose == 'profile' and request.user.is_authenticated:
                request.user.phone_number = phone_number
                request.user.phone_verified = True
                request.user.phone_verified_at = timezone.now()
                request.user.save()
            
            return Response({
                'success': True,
                'message': message,
                'phone_number': phone_number
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"인증번호 확인 오류: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': '인증번호 확인 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_phone_verification_status(request):
    """휴대폰 인증 상태 확인"""
    user = request.user
    
    return Response({
        'success': True,
        'phone_number': user.phone_number,
        'phone_verified': user.phone_verified,
        'phone_verified_at': user.phone_verified_at.isoformat() if user.phone_verified_at else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_phone_number(request):
    """휴대폰 번호 변경 (마이페이지용)"""
    phone_number = request.data.get('phone_number', '').strip()
    verification_code = request.data.get('verification_code', '').strip()
    
    if not phone_number or not verification_code:
        return Response({
            'success': False,
            'message': '휴대폰 번호와 인증번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 전화번호 형식 정규화
    phone_number = phone_number.replace('-', '').replace(' ', '')
    
    # 다른 사용자가 사용 중인지 확인
    existing_user = User.objects.filter(
        phone_number=phone_number,
        phone_verified=True
    ).exclude(id=request.user.id).first()
    
    if existing_user:
        return Response({
            'success': False,
            'message': '이미 다른 계정에서 사용 중인 휴대폰 번호입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 인증 확인
        verification = PhoneVerification.get_recent_verification(phone_number, 'profile')
        
        if not verification:
            return Response({
                'success': False,
                'message': '유효한 인증 요청을 찾을 수 없습니다. 다시 인증을 요청해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success, message = verification.verify(verification_code)
        
        if success:
            # 사용자 정보 업데이트
            request.user.phone_number = phone_number
            request.user.phone_verified = True
            request.user.phone_verified_at = timezone.now()
            request.user.save()
            
            return Response({
                'success': True,
                'message': '휴대폰 번호가 변경되었습니다.',
                'phone_number': phone_number
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"휴대폰 번호 변경 오류: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': '휴대폰 번호 변경 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)