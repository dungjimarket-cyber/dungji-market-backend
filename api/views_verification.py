from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
import logging

from .models_verification import PhoneVerification, BusinessNumberVerification
from .utils.sms_service import SMSService
from .utils.business_verification_service import BusinessVerificationService
from rest_framework.permissions import IsAuthenticated

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_business_number(request):
    """사업자번호 검증 API
    
    Request:
        {
            "business_number": "123-45-67890",
            "business_name": "회사명"  # 선택사항
        }
    """
    business_number = request.data.get('business_number', '').strip()
    business_name = request.data.get('business_name', '').strip() or None
    
    if not business_number:
        return Response(
            {'error': '사업자등록번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 판매자 권한 확인 (선택적 - 필요에 따라 주석 처리)
    if request.user.role != 'seller':
        return Response(
            {'error': '판매회원만 사업자번호를 검증할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # 사업자번호 검증 서비스 사용
        verification_service = BusinessVerificationService()
        verification = verification_service.verify_and_save(
            user=request.user,
            business_number=business_number,
            business_name=business_name
        )
        
        # 응답 데이터 구성
        response_data = {
            'verification_id': verification.id,
            'business_number': verification.format_business_number(),
            'status': verification.status,
            'message': {
                'valid': '유효한 사업자등록번호입니다.',
                'invalid': '유효하지 않은 사업자등록번호입니다.',
                'error': '검증 중 오류가 발생했습니다.'
            }.get(verification.status, '검증이 완료되었습니다.')
        }
        
        # 검증 성공 시 상세 정보 포함
        if verification.status == 'valid':
            response_data['business_info'] = {
                'business_name': verification.business_name,
                'representative_name': verification.representative_name,
                'business_status': verification.business_status,
                'business_type': verification.business_type,
                'establishment_date': verification.establishment_date.isoformat() if verification.establishment_date else None,
                'address': verification.address,
                'is_verified': True
            }
            
            # 사용자 정보 업데이트 확인
            request.user.refresh_from_db()
            response_data['user_verified'] = request.user.is_business_verified
        else:
            response_data['business_info'] = None
            response_data['error_message'] = verification.error_message
        
        # HTTP 상태 코드 결정
        if verification.status == 'valid':
            http_status = status.HTTP_200_OK
        elif verification.status == 'invalid':
            http_status = status.HTTP_400_BAD_REQUEST
        else:  # error
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        return Response(response_data, status=http_status)
        
    except Exception as e:
        logger.error(f"사업자번호 검증 오류: {e}", exc_info=True)
        return Response(
            {'error': '사업자번호 검증 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business_verification_history(request):
    """사업자번호 검증 이력 조회
    
    Query Parameters:
        - limit: 조회 개수 제한 (기본값: 10)
    """
    limit = min(int(request.GET.get('limit', 10)), 50)  # 최대 50개
    
    verifications = BusinessNumberVerification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:limit]
    
    verification_data = []
    for verification in verifications:
        data = {
            'id': verification.id,
            'business_number': verification.format_business_number(),
            'status': verification.status,
            'status_display': verification.get_status_display(),
            'created_at': verification.created_at.isoformat(),
            'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
        }
        
        if verification.status == 'valid':
            data['business_info'] = {
                'business_name': verification.business_name,
                'representative_name': verification.representative_name,
                'business_status': verification.business_status,
                'business_type': verification.business_type,
                'establishment_date': verification.establishment_date.isoformat() if verification.establishment_date else None,
                'address': verification.address,
            }
        elif verification.error_message:
            data['error_message'] = verification.error_message
        
        verification_data.append(data)
    
    return Response({
        'verifications': verification_data,
        'count': len(verification_data),
        'user_verified': request.user.is_business_verified,
        'user_business_number': request.user.business_number
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_business_number_format(request):
    """사업자번호 형식 검사 (실제 검증 없이 형식만 확인)
    
    Request:
        {
            "business_number": "123-45-67890"
        }
    """
    business_number = request.data.get('business_number', '').strip()
    
    if not business_number:
        return Response(
            {'error': '사업자등록번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 형식 검증
    is_valid, result = BusinessNumberVerification.validate_business_number_format(business_number)
    
    if is_valid:
        formatted_number = f'{result[:3]}-{result[3:5]}-{result[5:]}'
        return Response({
            'valid': True,
            'business_number': result,
            'formatted_number': formatted_number,
            'message': '올바른 사업자등록번호 형식입니다.'
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'valid': False,
            'error': result,
            'message': result
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_business_number_registration(request):
    """회원가입용 사업자번호 검증 API (인증 불필요)
    
    Request:
        {
            "business_number": "123-45-67890"
        }
    """
    business_number = request.data.get('business_number', '').strip()
    
    if not business_number:
        return Response(
            {'error': '사업자등록번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 먼저 형식 검증
    is_valid_format, clean_number_or_message = BusinessNumberVerification.validate_business_number_format(business_number)
    
    if not is_valid_format:
        return Response({
            'valid': False,
            'verified': False,
            'error': clean_number_or_message,
            'message': clean_number_or_message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    clean_number = clean_number_or_message
    
    # 사업자번호 중복 체크 추가
    from api.models import User
    if User.objects.filter(business_reg_number=clean_number).exists():
        return Response({
            'valid': False,
            'verified': False,
            'error': '이미 등록된 사업자등록번호입니다.',
            'message': '이미 등록된 사업자등록번호입니다. 동일한 사업자번호로는 하나의 계정만 생성할 수 있습니다.',
            'is_duplicate': True
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 실제 사업자번호 검증
        verification_service = BusinessVerificationService()
        result = verification_service.verify_business_number(clean_number)
        
        response_data = {
            'business_number': clean_number,
            'formatted_number': f'{clean_number[:3]}-{clean_number[3:5]}-{clean_number[5:]}',
            'status': result['status'],
            'verified': result['success'] and result['status'] == 'valid'
        }
        
        if result['success'] and result['status'] == 'valid':
            response_data.update({
                'valid': True,
                'message': '유효한 사업자등록번호입니다.',
                'business_info': result['data']
            })
            http_status = status.HTTP_200_OK
        else:
            response_data.update({
                'valid': False,
                'error': result['message'],
                'message': result['message']
            })
            http_status = status.HTTP_400_BAD_REQUEST
        
        return Response(response_data, status=http_status)
        
    except Exception as e:
        logger.error(f"회원가입용 사업자번호 검증 오류: {e}", exc_info=True)
        return Response({
            'valid': False,
            'verified': False,
            'error': '사업자번호 검증 중 오류가 발생했습니다.',
            'message': '사업자번호 검증 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)