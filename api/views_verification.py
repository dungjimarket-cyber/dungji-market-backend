from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
import logging

from .models_verification import PhoneVerification
from .utils.sms_service import SMSService

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """휴대폰 인증 코드 발송
    
    Request:
        {
            "phone_number": "010-1234-5678",
            "purpose": "signup"  # signup, reset_password, change_phone
        }
    """
    phone_number = request.data.get('phone_number', '').strip()
    purpose = request.data.get('purpose', 'signup')
    
    if not phone_number:
        return Response(
            {'error': '휴대폰 번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 전화번호 정규화
    sms_service = SMSService()
    normalized_phone = sms_service.normalize_phone_number(phone_number)
    
    # 전화번호 형식 검증
    if len(normalized_phone) not in [10, 11] or not normalized_phone.startswith('01'):
        return Response(
            {'error': '올바른 휴대폰 번호 형식이 아닙니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # IP 주소 가져오기
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                 request.META.get('REMOTE_ADDR')
    
    # 발송 제한 확인
    can_send, error_message = PhoneVerification.check_rate_limit(
        normalized_phone, 
        ip_address
    )
    
    if not can_send:
        return Response(
            {'error': error_message},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    try:
        with transaction.atomic():
            # 기존 대기중인 인증 무효화
            PhoneVerification.objects.filter(
                phone_number=normalized_phone,
                purpose=purpose,
                status='pending'
            ).update(status='expired')
            
            # 새 인증 생성
            verification = PhoneVerification.objects.create(
                phone_number=normalized_phone,
                purpose=purpose,
                ip_address=ip_address,
                user=request.user if request.user.is_authenticated else None
            )
            
            # SMS 발송
            success, sms_error = sms_service.send_verification_code(
                phone_number,
                verification.verification_code
            )
            
            if not success:
                verification.delete()
                return Response(
                    {'error': sms_error or 'SMS 발송에 실패했습니다.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 개발 모드에서는 인증 코드 반환 (프로덕션에서는 제거)
            response_data = {
                'message': '인증번호가 발송되었습니다.',
                'expires_in': 180,  # 3분
            }
            
            # 개발 환경에서만 코드 포함
            if settings.DEBUG:
                response_data['code'] = verification.verification_code
                logger.info(f"[DEV] 인증 코드: {verification.verification_code}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"인증 코드 발송 오류: {e}", exc_info=True)
        return Response(
            {'error': '인증 코드 발송 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    """휴대폰 인증 코드 확인
    
    Request:
        {
            "phone_number": "010-1234-5678",
            "code": "123456",
            "purpose": "signup",
            "name": "홍길동",  # optional
            "birthdate": "1990-01-01",  # optional
            "gender": "M"  # optional, M/F
        }
    """
    phone_number = request.data.get('phone_number', '').strip()
    code = request.data.get('code', '').strip()
    purpose = request.data.get('purpose', 'signup')
    
    # 추가 정보 (선택사항)
    name = request.data.get('name', '').strip()
    birthdate = request.data.get('birthdate', '').strip()
    gender = request.data.get('gender', '').strip().upper()
    
    if not phone_number or not code:
        return Response(
            {'error': '휴대폰 번호와 인증 코드를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 전화번호 정규화
    sms_service = SMSService()
    normalized_phone = sms_service.normalize_phone_number(phone_number)
    
    # 인증 코드 형식 검증
    if len(code) != 6 or not code.isdigit():
        return Response(
            {'error': '인증 코드는 6자리 숫자여야 합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 최근 인증 찾기
    verification = PhoneVerification.get_recent_verification(
        normalized_phone, 
        purpose
    )
    
    if not verification:
        return Response(
            {'error': '유효한 인증 요청이 없습니다. 다시 인증을 요청해주세요.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 인증 코드 확인
    success, message = verification.verify(code)
    
    if success:
        # 인증 성공 시 세션에 저장 (회원가입 시 활용)
        request.session[f'verified_phone_{purpose}'] = normalized_phone
        request.session[f'verified_phone_{purpose}_at'] = timezone.now().isoformat()
        
        # 추가 정보가 제공된 경우 세션에 저장
        if name:
            request.session[f'verified_phone_{purpose}_name'] = name
        if birthdate:
            request.session[f'verified_phone_{purpose}_birthdate'] = birthdate
        if gender in ['M', 'F']:
            request.session[f'verified_phone_{purpose}_gender'] = gender
        
        # 인증 레코드에도 추가 정보 저장 (선택사항)
        if name or birthdate or gender:
            verification.additional_info = {
                'name': name,
                'birthdate': birthdate,
                'gender': gender
            }
            verification.save()
        
        return Response({
            'message': message,
            'verified': True,
            'phone_number': sms_service.format_phone_number(normalized_phone),
            'additional_info': {
                'name': name,
                'birthdate': birthdate,
                'gender': gender
            } if (name or birthdate or gender) else None
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': message,
            'verified': False
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_verification_status(request):
    """인증 상태 확인
    
    Query Parameters:
        - phone_number: 휴대폰 번호
        - purpose: 용도 (기본값: signup)
    """
    phone_number = request.GET.get('phone_number', '').strip()
    purpose = request.GET.get('purpose', 'signup')
    
    if not phone_number:
        return Response(
            {'error': '휴대폰 번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 전화번호 정규화
    sms_service = SMSService()
    normalized_phone = sms_service.normalize_phone_number(phone_number)
    
    # 세션에서 인증 정보 확인
    verified_phone = request.session.get(f'verified_phone_{purpose}')
    verified_at = request.session.get(f'verified_phone_{purpose}_at')
    
    if verified_phone == normalized_phone and verified_at:
        # 인증 후 10분 이내인지 확인
        from datetime import datetime
        verified_time = datetime.fromisoformat(verified_at)
        if (timezone.now() - verified_time).total_seconds() < 600:  # 10분
            return Response({
                'verified': True,
                'phone_number': sms_service.format_phone_number(normalized_phone)
            }, status=status.HTTP_200_OK)
    
    # 데이터베이스에서 확인
    verification = PhoneVerification.objects.filter(
        phone_number=normalized_phone,
        purpose=purpose,
        status='verified',
        verified_at__gte=timezone.now() - timezone.timedelta(minutes=10)
    ).order_by('-verified_at').first()
    
    if verification:
        return Response({
            'verified': True,
            'phone_number': sms_service.format_phone_number(normalized_phone)
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'verified': False
        }, status=status.HTTP_200_OK)

# 관리 명령어용 (선택적)
@api_view(['POST'])
@permission_classes([AllowAny])  # 프로덕션에서는 관리자 권한으로 변경
def cleanup_expired_verifications(request):
    """만료된 인증 정리"""
    try:
        PhoneVerification.cleanup_expired()
        return Response({
            'message': '만료된 인증이 정리되었습니다.'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"인증 정리 오류: {e}", exc_info=True)
        return Response(
            {'error': '정리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# settings import 추가
from django.conf import settings