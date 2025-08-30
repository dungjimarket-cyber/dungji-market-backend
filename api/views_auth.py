import logging
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Max, IntegerField
from django.db.models.functions import Cast, Substr
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, Region, GroupBuy, Participation, Partner
from .models_verification import EmailVerification, PhoneVerification
from .utils.s3_utils import upload_file_to_s3
from .utils.resend_sender import ResendSender
from .serializers_jwt import CustomTokenObtainPairSerializer
from django.conf import settings
import json
import re
import requests
import os

logger = logging.getLogger(__name__)

def kakao_unlink(user_id):
    """
    카카오 연결 끊기 API 호출
    """
    try:
        # 카카오 API 키 가져오기
        kakao_admin_key = os.environ.get('KAKAO_ADMIN_KEY')
        if not kakao_admin_key:
            logger.warning("카카오 Admin Key가 설정되지 않았습니다.")
            return False
        
        # 카카오 unlink API 호출
        url = "https://kapi.kakao.com/v1/user/unlink"
        headers = {
            "Authorization": f"KakaoAK {kakao_admin_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "target_id_type": "user_id",
            "target_id": user_id
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            logger.info(f"카카오 연결 끊기 성공: user_id={user_id}")
            return True
        else:
            logger.error(f"카카오 연결 끊기 실패: status={response.status_code}, response={response.text}")
            return False
            
    except Exception as e:
        logger.error(f"카카오 연결 끊기 오류: {str(e)}")
        return False

def generate_auto_nickname(role='buyer'):
    """
    카카오톡 가입 시 자동 닉네임 생성
    - buyer: 참새1, 참새2, ...
    - seller: 어미새1, 어미새2, ...
    """
    prefix = '참새' if role == 'buyer' else '어미새'
    
    # 해당 패턴의 닉네임 중 가장 큰 번호 찾기
    pattern = f'^{prefix}\\d+$'
    existing_users = User.objects.filter(
        username__regex=pattern
    ).annotate(
        nickname_number=Cast(
            Substr('username', len(prefix) + 1),
            output_field=IntegerField()
        )
    ).aggregate(max_number=Max('nickname_number'))
    
    # 다음 번호 계산
    next_number = (existing_users['max_number'] or 0) + 1
    
    # 중복 체크를 위한 반복
    while True:
        new_nickname = f'{prefix}{next_number}'
        if not User.objects.filter(username=new_nickname).exists():
            return new_nickname
        next_number += 1

class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT 토큰에 사용자 정보를 추가하는 커스텀 뷰"""
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user_v2(request):
    """
    향상된 회원가입 API
    일반회원과 판매회원을 구분하여 처리
    """
    try:
        # JSON 또는 multipart/form-data로 전송된 데이터 처리
        if request.content_type and 'application/json' in request.content_type:
            data = request.data
            files = {}
        else:
            data = request.POST
            files = request.FILES
        
        # 공통 필수 필드
        nickname = data.get('nickname')
        phone_number = data.get('phone_number')
        password = data.get('password')
        role = data.get('role', 'buyer')
        
        # 이메일 필드 추가 (이메일 회원가입용)
        email = data.get('email', '')
        username_field = data.get('username', '')  # 프론트엔드에서 username으로도 전송될 수 있음
        
        # 선택 필드
        region = data.get('region', '')
        address_region_id = data.get('address_region_id', '')  # 지역 코드 추가
        profile_image = files.get('profile_image')
        
        # 판매자 전용 필드
        business_name = data.get('business_name', '')
        business_reg_number = data.get('business_reg_number', '')
        representative_name = data.get('representative_name', '')
        business_address = data.get('business_address', '')
        is_remote_sales_enabled = data.get('is_remote_sales_enabled', 'false').lower() == 'true'
        business_reg_image = files.get('business_reg_image')
        
        # 소셜 로그인 정보
        social_provider = data.get('social_provider', '')
        social_id = data.get('social_id', '')
        
        # 추천인 코드
        referral_code = data.get('referral_code', '')
        
        # 모든 판매회원은 추천인 코드 스킵 (마이페이지에서 입력)
        if role == 'seller':
            referral_code = ''
            referrer_user = None
            logger.info(f"판매회원 가입 - 추천인 코드 스킵 (마이페이지에서 입력)")
        else:
            # 구매회원은 가입 시 추천인 코드 검증 (입력된 경우만)
            referrer_user = None
            if referral_code:
                # 실제 파트너 시스템과 연동하여 추천인 코드 검증
                from api.models_partner import Partner
                try:
                    # 파트너 코드로 파트너 조회 (대소문자 구분 없이)
                    partner = Partner.objects.filter(
                        partner_code__iexact=referral_code,
                        is_active=True
                    ).first()
                    
                    if partner:
                        referrer_user = partner.user
                        logger.info(f"유효한 추천인 코드 사용: {referral_code} (파트너: {partner.partner_name})")
                    else:
                        # 파트너가 아닌 일반 사용자의 추천 코드인지 확인 (향후 확장용)
                        if referral_code.upper() == 'PARTNER':
                            # 임시 테스트 코드 지원
                            referrer_user = User.objects.filter(role='admin').first()
                            logger.info(f"테스트 추천인 코드 사용: {referral_code}")
                        else:
                            logger.info(f"무효한 추천인 코드: {referral_code}")
                            # 추천인 코드가 무효한 경우 에러 반환
                            return Response({
                                'error': '추천인코드가 유효하지 않습니다'
                            }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(f"추천인 코드 검증 오류: {e}")
                    return Response({
                        'error': '추천인코드가 유효하지 않습니다'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # 카카오톡 판매회원 가입 허용 (109번 요구사항 반영)
        
        # 카카오톡 가입 시 닉네임 자동 생성
        if social_provider == 'kakao' and not nickname:
            nickname = generate_auto_nickname(role)
            logger.info(f"카카오톡 가입 자동 닉네임 생성: {nickname}")
        
        # 유효성 검사
        if not nickname or not phone_number or not password:
            return Response(
                {'error': '닉네임, 휴대폰 번호, 비밀번호는 필수 입력 항목입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # role 검증
        if role not in ['buyer', 'seller']:
            return Response(
                {'error': '올바르지 않은 회원 유형입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 일반 회원가입인 경우 username 중복 확인
        if not social_provider and username_field:
            if User.objects.filter(username=username_field).exists():
                return Response(
                    {'error': '이미 사용 중인 아이디입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 닉네임 중복 확인
        if User.objects.filter(nickname=nickname).exists():
            return Response(
                {'error': '이미 사용 중인 닉네임입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 휴대폰 번호 중복 확인
        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {'error': '이미 등록된 휴대폰 번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이메일 중복 확인 (이메일이 제공된 경우)
        if email:
            if User.objects.filter(email=email).exists():
                return Response(
                    {'error': '이미 사용 중인 이메일입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 판매자인 경우 추가 검증 (카카오톡 가입 시에는 나중에 입력 가능)
        if role == 'seller' and not social_provider:
            # 일반 가입인 경우에만 필수 필드 검증
            if not business_reg_number or not business_address or not representative_name:
                return Response(
                    {'error': '판매자는 사업자등록번호, 대표자명, 사업장 주소를 입력해야 합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 사업자등록번호 중복 체크 비활성화 - 동일 사업자번호로 여러 계정 생성 가능
            # if business_reg_number:
            #     # 하이픈 제거
            #     clean_business_number = business_reg_number.replace('-', '').strip()
            #     # 이미 등록된 사업자번호인지 확인 (올바른 필드명 사용)
            #     if User.objects.filter(business_number=clean_business_number).exists():
            #         return Response(
            #             {'error': '이미 등록된 사업자등록번호입니다. 동일한 사업자번호로는 하나의 계정만 생성할 수 있습니다.'},
            #             status=status.HTTP_400_BAD_REQUEST
            #         )
        
        with transaction.atomic():
            # 사용자 생성
            # 이메일이 제공된 경우 실제 이메일 사용, 아니면 빈 문자열
            # 이메일이 없는 경우 빈 문자열로 처리하여 DB에 NULL이 들어가도록 함
            user_email = email if email else ''
            
            # username 설정
            # 일반 회원가입인 경우 username_field 사용
            # 소셜 회원가입인 경우 nickname 사용
            if not social_provider and username_field:
                username_for_db = username_field  # 일반 회원가입은 아이디 사용
            else:
                # 소셜 회원가입은 닉네임을 username으로 사용
                # 만약 username이 이미 존재하면 숫자를 붙여서 유니크하게 만듦
                base_username = nickname
                username_for_db = base_username
                counter = 1
                while User.objects.filter(username=username_for_db).exists():
                    username_for_db = f"{base_username}_{counter}"
                    counter += 1
            
            # 휴대폰 인증 시 저장된 추가 정보 가져오기
            verified_name = request.session.get('verified_phone_signup_name', '')
            verified_birthdate = request.session.get('verified_phone_signup_birthdate', '')
            verified_gender = request.session.get('verified_phone_signup_gender', '')
            
            user = User.objects.create(
                username=username_for_db,
                email=user_email,
                phone_number=phone_number,
                nickname=nickname,  # 닉네임은 항상 사용자가 입력한 nickname 사용
                first_name=verified_name or nickname,  # 인증 시 입력한 이름 우선 사용, 없으면 닉네임 사용
                role=role,
                sns_type=social_provider if social_provider else 'email',
                sns_id=social_id if social_id else None,
                is_remote_sales_enabled=is_remote_sales_enabled if role == 'seller' else False,
                referred_by=referral_code if referral_code else None
            )
            
            # 추가 정보가 있으면 프로필에 저장
            if verified_birthdate or verified_gender:
                # 생년월일 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
                if verified_birthdate and len(verified_birthdate) == 8:
                    try:
                        from datetime import datetime
                        birth_date_obj = datetime.strptime(verified_birthdate, '%Y%m%d').date()
                        user.birth_date = birth_date_obj
                    except ValueError:
                        logger.error(f"생년월일 형식 오류: {verified_birthdate}")
                
                # 성별 저장
                if verified_gender:
                    # verified_gender가 '남' 또는 '여'로 오는 경우 변환
                    if verified_gender == '남':
                        user.gender = 'M'
                    elif verified_gender == '여':
                        user.gender = 'F'
                    else:
                        user.gender = verified_gender
                
                user.save()
                logger.info(f"휴대폰 인증 추가 정보 저장 완료: 이름={verified_name}, 생년월일={user.birth_date}, 성별={user.gender}")
            
            # 인증 세션 정보 삭제
            for key in ['verified_phone_signup', 'verified_phone_signup_at', 'verified_phone_signup_name', 
                       'verified_phone_signup_birthdate', 'verified_phone_signup_gender']:
                request.session.pop(key, None)
            
            # 비밀번호 설정
            user.set_password(password)
            
            # 지역 설정
            if address_region_id:
                try:
                    # address_region_id로 지역 찾기
                    region_obj = Region.objects.filter(code=address_region_id).first()
                    if region_obj:
                        user.address_region = region_obj
                        logger.info(f"지역 설정 완료: {region_obj.full_name}")
                except Exception as e:
                    logger.error(f"지역 설정 오류: {str(e)}")
            elif region:
                try:
                    # 구버전 호환성을 위한 처리
                    # "서울특별시 강남구" 형태로 전달된 지역 정보 파싱
                    region_parts = region.split()
                    if len(region_parts) >= 2:
                        province = region_parts[0]
                        city = region_parts[1]
                        
                        # Region 모델에서 해당 지역 찾기
                        # full_name에 시/도와 시/군/구가 모두 포함된 지역 검색
                        region_obj = Region.objects.filter(
                            Q(full_name__contains=province) & Q(full_name__contains=city),
                            level=1  # 시/군/구 레벨
                        ).first()
                        
                        if region_obj:
                            user.address_region = region_obj
                except Exception as e:
                    logger.error(f"지역 설정 오류: {str(e)}")
            
            # 판매자 전용 필드 설정
            if role == 'seller':
                # 사업자등록번호가 제공된 경우 검증 수행
                if business_reg_number:
                    clean_business_number = business_reg_number.replace('-', '').strip()
                    
                    # seller1~seller10은 테스트 계정으로 자동으로 사업자 인증 완료 처리
                    test_accounts = [f'seller{i}' for i in range(1, 11)]
                    if username_for_db in test_accounts:
                        user.business_number = clean_business_number
                        user.is_business_verified = True
                        logger.info(f"테스트 계정 {username_for_db} 자동 사업자 인증 완료")
                    else:
                        # 실제 사업자번호 검증 수행 (일반 가입 시)
                        if not social_provider:
                            try:
                                from .utils.business_verification_service import BusinessVerificationService
                                verification_service = BusinessVerificationService()
                                result = verification_service.verify_business_number(clean_business_number, business_name)
                                
                                # 검증 결과에 따라 사용자 정보 설정
                                user.business_number = clean_business_number
                                if result['success'] and result['status'] == 'valid':
                                    user.is_business_verified = True
                                    logger.info(f"회원가입 시 사업자번호 검증 완료: {clean_business_number}")
                                else:
                                    user.is_business_verified = False
                                    logger.info(f"회원가입 시 사업자번호 검증 실패: {clean_business_number}, 사유: {result.get('message', 'Unknown')}")
                            except Exception as e:
                                logger.error(f"회원가입 시 사업자번호 검증 오류: {e}")
                                user.business_number = clean_business_number
                                user.is_business_verified = False
                        else:
                            # 소셜 로그인의 경우 나중에 검증
                            user.business_number = clean_business_number
                            user.is_business_verified = False
                            logger.info(f"소셜 가입 사업자번호 저장 (나중에 검증 필요): {clean_business_number}")
                
                if representative_name:
                    user.representative_name = representative_name
                if business_address:
                    user.address_detail = business_address
                
                # 사업자등록증 이미지 업로드
                if business_reg_image:
                    try:
                        file_url = upload_file_to_s3(
                            business_reg_image,
                            f'business_reg/{user.id}_{business_reg_image.name}'
                        )
                        # 사업자등록증 URL을 저장할 필드가 없으므로 
                        # 추후 모델에 필드 추가 필요
                        logger.info(f"사업자등록증 업로드 완료: {file_url}")
                    except Exception as e:
                        logger.error(f"사업자등록증 업로드 실패: {str(e)}")
            
            # 프로필 이미지 업로드
            if profile_image:
                try:
                    file_url = upload_file_to_s3(
                        profile_image,
                        f'profiles/{user.id}_{profile_image.name}'
                    )
                    user.profile_image = file_url
                except Exception as e:
                    logger.error(f"프로필 이미지 업로드 실패: {str(e)}")
            
            user.save()
            
            # 판매회원 가입시 입찰권 자동 추가
            if role == 'seller':
                from .models import BidToken
                base_tokens = 10  # 기본 지급 토큰
                bonus_tokens = 0  # 추천인 보너스 토큰
                
                # 유효한 추천인 코드 사용 시 추가 10매 지급
                if referrer_user and referral_code:
                    # 파트너 코드 확인
                    from .models_partner import Partner
                    partner = Partner.objects.filter(
                        partner_code__iexact=referral_code,
                        is_active=True
                    ).first()
                    
                    if partner:
                        bonus_tokens = 10
                        logger.info(f"추천인 코드 보너스 적용: +{bonus_tokens}매 (파트너: {partner.partner_name})")
                
                total_tokens = base_tokens + bonus_tokens
                
                for i in range(total_tokens):
                    BidToken.objects.create(
                        seller=user,
                        token_type='single',
                        status='active'
                    )
                
                logger.info(f"판매회원 {user.username}에게 입찰권 {total_tokens}매 지급 완료 (기본: {base_tokens}매, 추천 보너스: {bonus_tokens}매)")
            
            # 추천인 기록 생성 (유효한 추천인 코드 사용 시)
            if referrer_user and referral_code:
                try:
                    from .models_partner import ReferralRecord, Partner
                    
                    # 추천 코드로 실제 파트너 정보 조회
                    partner = Partner.objects.filter(
                        partner_code__iexact=referral_code,
                        is_active=True
                    ).first()
                    
                    if partner:
                        referral_record = ReferralRecord.objects.create(
                            partner=partner,
                            referred_user=user,
                            subscription_status='active',
                            # 추후 실제 결제 시스템 연동 시 금액 업데이트
                            total_amount=0,
                            commission_amount=0
                        )
                        logger.info(f"추천 기록 생성 완료: {referral_record}")
                        
                        # 파트너 알림 생성
                        from .models_partner import PartnerNotification
                        PartnerNotification.objects.create(
                            partner=partner,
                            notification_type='signup',
                            title='신규 회원 가입',
                            message=f'{user.nickname}님이 추천 코드 {referral_code}를 통해 가입했습니다.',
                            referral_record=referral_record
                        )
                        logger.info(f"파트너 알림 생성 완료")
                        
                except Exception as e:
                    logger.error(f"추천 기록 생성 실패: {str(e)}")
            
            logger.info(f"회원가입 완료: nickname={nickname}, username={user.username}, email={user.email} (ID: {user.id}, Role: {role})")
            
            return Response(
                {
                    'message': '회원가입이 완료되었습니다.',
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role
                },
                status=status.HTTP_201_CREATED
            )
    
    except Exception as e:
        logger.error(f"회원가입 오류: {str(e)}")
        return Response(
            {'error': '회원가입 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def check_username(request):
    """
    아이디 중복 확인 API
    """
    try:
        username = request.data.get('username')
        
        if not username:
            return Response(
                {'error': '아이디를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 아이디 중복 확인
        is_available = not User.objects.filter(username=username).exists()
        
        return Response({
            'available': is_available,
            'username': username
        })
    
    except Exception as e:
        logger.error(f"아이디 중복 확인 오류: {str(e)}")
        return Response(
            {'error': '처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    """
    이메일 중복 확인 API
    """
    try:
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': '이메일을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이메일 중복 확인
        is_available = not User.objects.filter(email=email).exists()
        
        return Response({
            'available': is_available,
            'email': email
        })
    
    except Exception as e:
        logger.error(f"이메일 중복 확인 오류: {str(e)}")
        return Response(
            {'error': '처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Removed duplicate check_nickname function (kept the one at line 707)


@api_view(['POST'])
@permission_classes([AllowAny])
def find_username(request):
    """
    휴대폰 번호로 아이디(사용자명) 찾기
    """
    try:
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response(
                {'error': '휴대폰 번호를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 하이픈 제거
        phone_number = phone_number.replace('-', '')
        
        user = User.objects.filter(phone_number=phone_number).first()
        
        if not user:
            return Response(
                {'error': '해당 휴대폰 번호로 등록된 계정을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 아이디 마스킹 처리
        username = user.username
        if len(username) > 3:
            masked_username = username[:2] + '*' * (len(username) - 3) + username[-1]
        else:
            masked_username = username[0] + '*' * (len(username) - 1)
        
        return Response({
            'username': masked_username,
            'message': f'아이디는 {masked_username} 입니다.'
        })
    
    except Exception as e:
        logger.error(f"아이디 찾기 오류: {str(e)}")
        return Response(
            {'error': '아이디 찾기 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    비밀번호 재설정
    """
    try:
        username = request.data.get('username')
        phone_number = request.data.get('phone_number')
        new_password = request.data.get('new_password')
        
        if not username or not phone_number or not new_password:
            return Response(
                {'error': '모든 필드를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 하이픈 제거
        phone_number = phone_number.replace('-', '')
        
        # 사용자 확인
        user = User.objects.filter(
            username=username,
            phone_number=phone_number
        ).first()
        
        if not user:
            return Response(
                {'error': '일치하는 사용자 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 비밀번호 재설정
        user.set_password(new_password)
        user.save()
        
        logger.info(f"비밀번호 재설정 완료: {username}")
        
        return Response({
            'message': '비밀번호가 재설정되었습니다.'
        })
    
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: {str(e)}")
        return Response(
            {'error': '비밀번호 재설정 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    사용자 프로필 조회
    """
    try:
        user = request.user
        
        profile_data = {
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,  # nickname 필드 추가
            'email': user.email,
            'phone_number': user.phone_number,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'sns_type': user.sns_type,  # SNS 로그인 타입 추가
            'profile_image': user.profile_image,
            'business_reg_number': user.business_reg_number,
            'representative_name': user.representative_name, # 대표자명 필드 추가
            'is_business_verified': user.is_business_verified,
            'is_remote_sales_enabled': user.is_remote_sales_enabled,
            'remote_sales_verified': user.remote_sales_verified,
            'address_region': {
                'code': user.address_region.code,
                'name': user.address_region.name,
                'full_name': user.address_region.full_name,
                'level': user.address_region.level
            } if user.address_region else None,
            'address_detail': user.address_detail,
            'penalty_count': user.penalty_count,
            'penalty_expiry': user.penalty_expiry,
            'current_penalty_level': user.current_penalty_level,
            'created_at': user.date_joined,
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'gender': user.gender,
            'average_rating': user.average_rating,  # 평균 별점 추가
            'review_count': user.review_count,  # 리뷰 개수 추가
        }
        
        return Response(profile_data)
    
    except Exception as e:
        logger.error(f"프로필 조회 오류: {str(e)}")
        return Response(
            {'error': '프로필 조회 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """
    사용자 프로필 업데이트
    """
    try:
        user = request.user
        data = request.data
        files = request.FILES
        
        logger.info(f"프로필 업데이트 요청 - User: {user.id}, Data: {data}")
        
        # 업데이트 가능한 필드들
        if 'username' in data:
            # 닉네임(username) 중복 확인
            username = data['username']
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return Response(
                    {'error': '이미 사용 중인 닉네임입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.username = username
            user.nickname = username  # nickname 필드도 동기화
            
            # 닉네임 변경시 생성한 모든 공구의 creator_nickname 업데이트
            from .models import GroupBuy
            GroupBuy.objects.filter(creator=user).update(creator_nickname=username)
            logger.info(f"User {user.id} changed nickname, updated {GroupBuy.objects.filter(creator=user).count()} GroupBuy records")
        
        if 'phone_number' in data:
            # 휴대폰 번호 중복 확인
            phone_number = data['phone_number'].replace('-', '')
            if User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                return Response(
                    {'error': '이미 등록된 휴대폰 번호입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.phone_number = phone_number
        
        if 'first_name' in data:
            user.first_name = data['first_name']
        
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        if 'address_detail' in data:
            user.address_detail = data['address_detail']
        
        # 지역 업데이트
        if 'address_region_id' in data:
            try:
                region_code = data['address_region_id']
                if region_code:
                    region_obj = Region.objects.filter(code=region_code).first()
                    if region_obj:
                        user.address_region = region_obj
                else:
                    user.address_region = None
            except Exception as e:
                logger.error(f"지역 업데이트 오류: {str(e)}")
        
        # 사업자 정보 업데이트
        if 'business_number' in data and user.role == 'seller':
            new_business_number = data['business_number'].replace('-', '').strip()
            current_business_number = user.business_number or ''
            
            # 사업자번호가 변경된 경우만 검증 수행
            if new_business_number != current_business_number:
                try:
                    # 사업자번호 검증 수행
                    from .utils.business_verification_service import BusinessVerificationService
                    verification_service = BusinessVerificationService()
                    result = verification_service.verify_business_number(new_business_number)
                    
                    # 검증 결과에 따라 사용자 정보 업데이트
                    user.business_number = new_business_number
                    if result['success'] and result['status'] == 'valid':
                        user.is_business_verified = True
                        logger.info(f"마이페이지에서 사업자번호 검증 완료: {new_business_number}")
                    else:
                        user.is_business_verified = False
                        logger.info(f"마이페이지에서 사업자번호 검증 실패: {new_business_number}, 사유: {result.get('message', 'Unknown')}")
                        
                        # 검증 실패 시 응답에 오류 메시지 포함 (하지만 저장은 진행)
                        verification_error = result.get('message', '사업자번호 검증에 실패했습니다.')
                        
                except Exception as e:
                    logger.error(f"마이페이지 사업자번호 검증 오류: {e}")
                    user.business_number = new_business_number
                    user.is_business_verified = False
                    verification_error = '사업자번호 검증 중 오류가 발생했습니다.'
            else:
                # 사업자번호가 동일한 경우 그대로 저장
                user.business_number = new_business_number
        
        if 'representative_name' in data:
            user.representative_name = data['representative_name']
        
        if 'is_remote_sales' in data:
            # boolean 또는 문자열 처리
            value = data['is_remote_sales']
            if isinstance(value, bool):
                user.is_remote_sales = value
            else:
                user.is_remote_sales = str(value).lower() == 'true'
        
        # 프로필 이미지 업데이트
        if 'profile_image' in files:
            try:
                profile_image = files['profile_image']
                file_url = upload_file_to_s3(
                    profile_image,
                    f'profiles/{user.id}_{profile_image.name}'
                )
                user.profile_image = file_url
            except Exception as e:
                logger.error(f"프로필 이미지 업데이트 실패: {str(e)}")
        
        # 판매자 전용 필드
        if user.role == 'seller':
            if 'business_reg_number' in data:
                user.business_reg_number = data['business_reg_number']
            
            if 'is_remote_sales_enabled' in data:
                # boolean 또는 문자열 처리
                value = data['is_remote_sales_enabled']
                if isinstance(value, bool):
                    user.is_remote_sales_enabled = value
                else:
                    user.is_remote_sales_enabled = str(value).lower() == 'true'
        
        user.save()
        
        response_data = {
            'message': '프로필이 업데이트되었습니다.',
            'profile': {
                'username': user.username,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'profile_image': user.profile_image,
                'role': user.role,
                'is_business_verified': user.is_business_verified if user.role == 'seller' else None,
                'business_number': user.business_number if user.role == 'seller' else None
            }
        }
        
        # 사업자번호 검증 오류가 있는 경우 메시지 추가
        if 'verification_error' in locals():
            response_data['business_verification_error'] = verification_error
            response_data['message'] = '프로필이 업데이트되었지만 사업자번호 검증에 실패했습니다.'
        
        return Response(response_data)
    
    except Exception as e:
        import traceback
        logger.error(f"프로필 업데이트 오류: {str(e)}")
        logger.error(f"오류 발생 위치 - User ID: {user.id}, Data: {data}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            {'error': '프로필 업데이트 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def check_nickname(request):
    """닉네임 중복 확인"""
    nickname = request.data.get('nickname')
    current_user_id = request.data.get('current_user_id')  # 현재 사용자 ID (선택적)
    
    if not nickname:
        return Response(
            {'error': '닉네임을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 닉네임 중복 확인 쿼리
    query = User.objects.filter(username=nickname)
    
    # 현재 사용자가 있는 경우 (프로필 수정 시) 자기 자신은 제외
    if current_user_id:
        query = query.exclude(id=current_user_id)
    
    # 인증된 사용자의 경우 자동으로 자기 자신 제외
    if request.user and request.user.is_authenticated:
        query = query.exclude(id=request.user.id)
    
    exists = query.exists()
    
    return Response({
        'available': not exists,
        'message': '이미 사용중인 닉네임입니다.' if exists else '사용 가능한 닉네임입니다.'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_referral_code(request):
    """판매회원 추천인 코드 업데이트"""
    user = request.user
    referral_code = request.data.get('referral_code', '').strip()
    
    # 판매회원인지 확인
    if user.role != 'seller':
        return Response(
            {'error': '판매회원만 추천인 코드를 입력할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 이미 추천인 코드가 설정되어 있는지 확인
    if user.referred_by:
        return Response(
            {'error': '추천인 코드는 한 번만 입력할 수 있습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 추천인 코드가 입력되지 않은 경우
    if not referral_code:
        return Response(
            {'error': '추천인 코드를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 추천인 코드 검증
    from api.models_partner import Partner, ReferralRecord, PartnerNotification
    
    try:
        # 파트너 코드로 파트너 조회 (대소문자 구분 없이)
        partner = Partner.objects.filter(
            partner_code__iexact=referral_code,
            is_active=True
        ).first()
        
        if not partner:
            # 테스트 코드 확인
            if referral_code.upper() == 'PARTNER':
                # 임시 테스트 코드는 허용하지 않음
                return Response({
                    'error': '추천인코드가 유효하지 않습니다'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': '추천인코드가 유효하지 않습니다'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 추천인 코드 저장
        user.referred_by = referral_code
        user.save()
        
        # 추천 기록 생성
        referral_record = ReferralRecord.objects.create(
            partner=partner,
            referred_user=user,
            subscription_status='active',
            total_amount=0,
            commission_amount=0
        )
        
        # 파트너에게 알림 발송
        PartnerNotification.objects.create(
            partner=partner,
            notification_type='signup',
            title='신규 회원 가입',
            message=f'{user.nickname}님이 추천 코드 {referral_code}를 통해 등록했습니다.',
            referral_record=referral_record
        )
        
        # 추천인 코드 입력 보너스 입찰권 지급 (10개)
        from api.models import BidToken
        for i in range(10):
            BidToken.objects.create(
                seller=user,
                token_type='single',
                status='active'
            )
        
        logger.info(f"판매회원 {user.username}이 추천인 코드 {referral_code} 입력 완료 (보너스 입찰권 10개 지급)")
        
        # 추천인 이름 가져오기
        referrer_name = partner.user.nickname or partner.user.username
        
        return Response({
            'success': True,
            'message': '추천인 코드가 등록되었습니다. 보너스 입찰권 10개가 지급되었습니다.',
            'bonus_tokens': 10,
            'referrer_name': referrer_name
        })
        
    except Exception as e:
        logger.error(f"추천인 코드 업데이트 오류: {str(e)}")
        return Response({
            'error': '추천인 코드 처리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def find_username(request):
    """아이디 찾기 - 휴대폰 번호로 사용자 찾기"""
    phone_number = request.data.get('phone_number', '').replace('-', '')
    
    if not phone_number:
        return Response(
            {'error': '휴대폰 번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(phone_number=phone_number)
        
        # 카카오 계정 체크
        is_social = False
        provider = None
        
        # SocialAccount 모델 체크
        try:
            from allauth.socialaccount.models import SocialAccount
            social_account = SocialAccount.objects.filter(user=user).first()
            if social_account:
                is_social = True
                provider = social_account.provider
        except:
            pass
        
        # 카카오 계정인 경우
        if is_social and provider == 'kakao':
            return Response({
                'username': None,  # 아이디 표시 안 함
                'is_social': True,
                'provider': 'kakao',
                'message': '카카오톡 계정으로 가입하신 회원입니다.'
            })
        
        # 일반 계정인 경우
        return Response({
            'username': user.username,
            'is_social': is_social,
            'provider': provider,
            'message': '아이디를 찾았습니다.'
        })
    except User.DoesNotExist:
        return Response(
            {'error': '해당 휴대폰 번호로 등록된 사용자가 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def find_id_by_phone(request):
    """
    아이디 찾기 전용 API
    - 휴대폰 번호로 사용자 검색
    - SNS 계정 체크
    - SNS 계정인 경우 아이디 미제공
    """
    phone_number = request.data.get('phone_number', '').strip()
    
    if not phone_number:
        return Response({
            'success': False,
            'error': '휴대폰 번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 하이픈, 공백 제거
    phone_number = phone_number.replace('-', '').replace(' ', '')
    
    try:
        # 휴대폰 번호로 사용자 찾기
        user = User.objects.get(phone_number=phone_number)
        
        # SNS 계정 체크
        is_social = False
        provider = None
        
        # SocialAccount 모델 체크 - allauth 설치 여부와 관계없이 작동
        try:
            # Django 앱이 설치되어 있는지 확인
            from django.apps import apps
            if apps.is_installed('allauth.socialaccount'):
                from allauth.socialaccount.models import SocialAccount
                social_account = SocialAccount.objects.filter(user=user).first()
                if social_account:
                    is_social = True
                    provider = social_account.provider
                    logger.info(f"SNS 계정 감지: user_id={user.id}, provider={provider}")
            else:
                logger.info(f"allauth.socialaccount 앱이 설치되지 않음 - 일반 계정으로 처리")
        except ImportError:
            logger.warning(f"SocialAccount 모델을 가져올 수 없음 - 일반 계정으로 처리")
        except Exception as e:
            logger.error(f"SocialAccount 체크 오류: {str(e)}")
        
        # SNS 계정인 경우
        if is_social:
            provider_messages = {
                'kakao': '카카오톡 계정으로 가입하신 회원입니다.\n카카오톡 로그인을 이용해주세요.\n\n일반 로그인이 필요하신 경우 고객센터로 문의해주세요.',
                'google': '구글 계정으로 가입하신 회원입니다.\n구글 로그인을 이용해주세요.\n\n일반 로그인이 필요하신 경우 고객센터로 문의해주세요.',
                'naver': '네이버 계정으로 가입하신 회원입니다.\n네이버 로그인을 이용해주세요.\n\n일반 로그인이 필요하신 경우 고객센터로 문의해주세요.'
            }
            
            message = provider_messages.get(
                provider, 
                f'{provider} 계정으로 가입하신 회원입니다.\nSNS 로그인을 이용해주세요.'
            )
            
            return Response({
                'success': False,
                'is_social': True,
                'provider': provider,
                'message': message,
                'username': None  # SNS 계정은 아이디 미제공
            })
        
        # 일반 계정인 경우 - 아이디 마스킹 처리
        username = user.username
        if len(username) > 3:
            masked_username = username[:2] + '*' * (len(username) - 3) + username[-1]
        else:
            masked_username = username[0] + '*' * (len(username) - 1) if username else ''
        
        return Response({
            'success': True,
            'is_social': False,
            'provider': None,
            'username': masked_username,
            'message': f'회원님의 아이디는 {masked_username} 입니다.'
        })
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': '해당 휴대폰 번호로 등록된 계정을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"아이디 찾기 오류: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': '아이디 찾기 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """비밀번호 재설정"""
    username = request.data.get('username')
    phone_number = request.data.get('phone_number', '').replace('-', '')
    new_password = request.data.get('new_password')
    
    if not all([username, phone_number, new_password]):
        return Response(
            {'error': '모든 필드를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(username=username, phone_number=phone_number)
        user.password = make_password(new_password)
        user.save()
        
        return Response({
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        })
    except User.DoesNotExist:
        return Response(
            {'error': '사용자 정보를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_user(request):
    """
    회원 탈퇴 API
    """
    try:
        user = request.user
        password = request.data.get('password')
        reason = request.data.get('reason', '')
        
        # 비밀번호 확인 (이메일 회원가입 사용자만)
        if user.sns_type == 'email':
            if not password:
                return Response(
                    {'error': '비밀번호를 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not check_password(password, user.password):
                return Response(
                    {'error': '비밀번호가 일치하지 않습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 진행 중인 공구 확인 (참여자로 있는 경우)
        active_participations = Participation.objects.filter(
            user=user,
            groupbuy__status__in=['recruiting', 'bidding', 'final_selection', 'seller_confirmation']
        ).exists()
        
        if active_participations:
            return Response(
                {'error': '진행 중인 공구가 있어 탈퇴할 수 없습니다. 공구 종료 후 다시 시도해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 생성한 진행 중인 공구 확인
        active_created_groupbuys = GroupBuy.objects.filter(
            creator=user,
            status__in=['recruiting', 'bidding', 'final_selection', 'seller_confirmation']
        ).exists()
        
        if active_created_groupbuys:
            return Response(
                {'error': '진행 중인 생성 공구가 있어 탈퇴할 수 없습니다. 공구 종료 후 다시 시도해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 카카오 사용자인 경우 연결 끊기
        if user.sns_type == 'kakao' and user.sns_id:
            kakao_unlink_success = kakao_unlink(user.sns_id)
            if not kakao_unlink_success:
                logger.warning(f"카카오 연결 끊기 실패했지만 탈퇴는 진행합니다. User ID: {user.id}")
        
        # 탈퇴 사유 로깅
        logger.info(f"회원 탈퇴 - User ID: {user.id}, Username: {user.username}, SNS Type: {user.sns_type}, Reason: {reason}")
        
        # 사용자 삭제
        user.delete()
        
        return Response({
            'message': '회원 탈퇴가 완료되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"회원 탈퇴 오류: {str(e)}")
        return Response(
            {'error': '회원 탈퇴 처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    통합 사용자 프로필 API
    GET: 프로필 조회
    PATCH: 프로필 수정
    """
    if request.method == 'GET':
        # GET 요청 처리 - get_user_profile의 로직을 직접 사용
        try:
            user = request.user
            
            profile_data = {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'email': user.email,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'sns_type': user.sns_type,
                'profile_image': user.profile_image,
                'business_reg_number': user.business_reg_number,
                'is_business_verified': user.is_business_verified,
                'is_remote_sales_enabled': user.is_remote_sales_enabled,
                'remote_sales_verified': user.remote_sales_verified,
                'address_region': {
                    'code': user.address_region.code,
                    'name': user.address_region.name,
                    'full_name': user.address_region.full_name,
                    'level': user.address_region.level
                } if user.address_region else None,
                'address_detail': user.address_detail,
                'penalty_count': user.penalty_count,
                'penalty_expiry': user.penalty_expiry,
                'current_penalty_level': user.current_penalty_level,
                'created_at': user.date_joined,
                'business_number': user.business_number,
                'is_remote_sales': user.is_remote_sales,
                'birth_date': user.birth_date.isoformat() if user.birth_date else None,
                'gender': user.gender,
            }
            
            return Response(profile_data)
        
        except Exception as e:
            logger.error(f"프로필 조회 오류: {str(e)}")
            return Response(
                {'error': '프로필 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'PATCH':
        # PATCH 요청 처리 - update_user_profile의 로직을 직접 사용
        try:
            user = request.user
            data = request.data
            files = request.FILES
            
            # 업데이트 가능한 필드들
            if 'email' in data:
                # 이메일 중복 확인
                email = data['email']
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return Response(
                        {'error': '이미 사용 중인 이메일입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.email = email
            
            # username은 아이디이므로 변경 불가
            if 'username' in data:
                return Response(
                    {'error': '아이디(username)는 변경할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # nickname 변경 (표시 이름)
            if 'nickname' in data:
                nickname = data['nickname']
                if not nickname:
                    return Response(
                        {'error': '닉네임을 입력해주세요.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # 닉네임 중복 확인 (선택사항 - 닉네임은 중복 허용할 수도 있음)
                user.nickname = nickname
                
                # 닉네임 변경시 생성한 모든 공구의 creator_nickname 업데이트
                from .models import GroupBuy
                GroupBuy.objects.filter(creator=user).update(creator_nickname=nickname)
                logger.info(f"User {user.id} changed nickname to {nickname}, updated {GroupBuy.objects.filter(creator=user).count()} GroupBuy records")
            
            if 'phone_number' in data:
                # 휴대폰 번호 중복 확인
                phone_number = data['phone_number'].replace('-', '')
                if User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                    return Response(
                        {'error': '이미 등록된 휴대폰 번호입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.phone_number = phone_number
            
            if 'first_name' in data:
                user.first_name = data['first_name']
            
            if 'last_name' in data:
                user.last_name = data['last_name']
            
            if 'address_detail' in data:
                user.address_detail = data['address_detail']
            
            # 지역 업데이트
            if 'address_region_id' in data:
                try:
                    region_code = data['address_region_id']
                    if region_code:
                        region_obj = Region.objects.filter(code=region_code).first()
                        if region_obj:
                            user.address_region = region_obj
                    else:
                        user.address_region = None
                except Exception as e:
                    logger.error(f"지역 업데이트 오류: {str(e)}")
            
            # 사업자 정보 업데이트
            if 'business_number' in data:
                user.business_number = data['business_number']
            
            if 'is_remote_sales' in data:
                value = data['is_remote_sales']
                if isinstance(value, bool):
                    user.is_remote_sales = value
                else:
                    user.is_remote_sales = str(value).lower() == 'true'
            
            # 프로필 이미지 업데이트
            if 'profile_image' in files:
                try:
                    profile_image = files['profile_image']
                    file_url = upload_file_to_s3(
                        profile_image,
                        f'profiles/{user.id}_{profile_image.name}'
                    )
                    user.profile_image = file_url
                except Exception as e:
                    logger.error(f"프로필 이미지 업데이트 실패: {str(e)}")
            
            # 판매자 전용 필드
            if user.role == 'seller':
                if 'business_reg_number' in data:
                    user.business_reg_number = data['business_reg_number']
                
                if 'is_remote_sales_enabled' in data:
                    value = data['is_remote_sales_enabled']
                    if isinstance(value, bool):
                        user.is_remote_sales_enabled = value
                    else:
                        user.is_remote_sales_enabled = str(value).lower() == 'true'
            
            user.save()
            
            return Response({
                'message': '프로필이 업데이트되었습니다.',
                'profile': {
                    'username': user.username,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'first_name': user.first_name,
                    'profile_image': user.profile_image,
                    'role': user.role
                }
            })
        
        except Exception as e:
            logger.error(f"프로필 업데이트 오류: {str(e)}")
            return Response(
                {'error': '프로필 업데이트 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    else:
        return Response(
            {'error': '지원하지 않는 메서드입니다.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def send_password_reset_email(request):
    """
    이메일 기반 비밀번호 재설정 인증번호 발송
    """
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        
        if not username or not email:
            return Response(
                {'error': '아이디와 이메일을 모두 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 사용자 확인
        user = User.objects.filter(username=username, email=email).first()
        if not user:
            return Response(
                {'error': '입력한 정보와 일치하는 사용자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # IP 주소 가져오기
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # 발송 제한 확인
        can_send, error_message = EmailVerification.check_rate_limit(email, ip_address)
        if not can_send:
            return Response(
                {'error': error_message},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # 기존 대기 중인 인증 코드가 있다면 만료시키기
        EmailVerification.objects.filter(
            email=email,
            purpose='password_reset',
            status='pending'
        ).update(status='expired')
        
        # 새 인증 코드 생성
        verification = EmailVerification.objects.create(
            email=email,
            purpose='password_reset',
            user=user,
            ip_address=ip_address,
            additional_info={'username': username}
        )
        
        # Resend를 통해 이메일 발송
        success = ResendSender.send_password_reset_verification(
            recipient_email=email,
            username=user.username,
            verification_code=verification.verification_code
        )
        
        if success:
            logger.info(f"비밀번호 재설정 인증번호 발송 성공: {email} (User: {user.username})")
            return Response({
                'message': '인증번호가 이메일로 발송되었습니다.',
                'expires_in_minutes': 5
            })
        else:
            verification.status = 'failed'
            verification.save()
            return Response(
                {'error': '이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"비밀번호 재설정 이메일 발송 오류: {str(e)}")
        return Response(
            {'error': '처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_password_reset_email(request):
    """
    이메일 인증번호 확인
    """
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        verification_code = request.data.get('verification_code')
        
        if not username or not email or not verification_code:
            return Response(
                {'error': '모든 필드를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 사용자 확인
        user = User.objects.filter(username=username, email=email).first()
        if not user:
            return Response(
                {'error': '입력한 정보와 일치하는 사용자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 인증 코드 확인
        verification = EmailVerification.objects.filter(
            email=email,
            purpose='password_reset',
            status='pending'
        ).order_by('-created_at').first()
        
        if not verification:
            return Response(
                {'error': '유효한 인증 요청을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 인증 코드 검증
        is_valid, message = verification.verify(verification_code)
        
        if is_valid:
            # 세션에 인증 정보 저장 (비밀번호 재설정용)
            request.session['password_reset_verified'] = True
            request.session['password_reset_user_id'] = user.id
            request.session['password_reset_verified_at'] = timezone.now().isoformat()
            
            logger.info(f"비밀번호 재설정 이메일 인증 성공: {email} (User: {user.username})")
            return Response({
                'message': '인증이 완료되었습니다.',
                'verified': True
            })
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(f"비밀번호 재설정 이메일 인증 오류: {str(e)}")
        return Response(
            {'error': '처리 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_with_email(request):
    """
    이메일 인증 후 비밀번호 재설정
    """
    try:
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': '새 비밀번호를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 세션에서 인증 정보 확인
        if not request.session.get('password_reset_verified'):
            return Response(
                {'error': '인증이 완료되지 않았습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = request.session.get('password_reset_user_id')
        if not user_id:
            return Response(
                {'error': '사용자 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 인증 시간 확인 (10분 제한)
        verified_at_str = request.session.get('password_reset_verified_at')
        if verified_at_str:
            from django.utils.dateparse import parse_datetime
            verified_at = parse_datetime(verified_at_str)
            if timezone.now() - verified_at > timedelta(minutes=10):
                # 세션 정보 삭제
                for key in ['password_reset_verified', 'password_reset_user_id', 'password_reset_verified_at']:
                    request.session.pop(key, None)
                return Response(
                    {'error': '인증 시간이 만료되었습니다. 다시 인증해주세요.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # 사용자 가져오기
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {'error': '사용자를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 비밀번호 재설정
        user.set_password(new_password)
        user.save()
        
        # 세션 정보 삭제
        for key in ['password_reset_verified', 'password_reset_user_id', 'password_reset_verified_at']:
            request.session.pop(key, None)
        
        # IP 주소 가져오기
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # 비밀번호 변경 확인 이메일 발송
        ResendSender.send_password_changed_confirmation(
            recipient_email=user.email,
            username=user.username,
            changed_at=timezone.now(),
            ip_address=ip_address
        )
        
        logger.info(f"비밀번호 재설정 완료: {user.username} (ID: {user.id})")
        
        return Response({
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        })
    
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: {str(e)}")
        return Response(
            {'error': '비밀번호 변경 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_referral_status(request):
    """
    사용자의 추천인 코드 입력 상태 확인
    """
    try:
        user = request.user
        logger.info(f"추천인 상태 확인: 사용자 {user.username}, referred_by={user.referred_by}")
        
        # 추천인 정보 확인 - referred_by 필드 사용
        has_referral = bool(user.referred_by)
        referral_code = user.referred_by if has_referral else None
        referrer_name = None
        
        if has_referral and referral_code:
            # 추천인 코드로 파트너 찾기 (대소문자 구분 없이)
            from api.models_partner import Partner as PartnerModel
            partner = PartnerModel.objects.filter(partner_code__iexact=referral_code).first()
            logger.info(f"추천인 코드 {referral_code}로 파트너 검색 결과: {partner}")
            
            if partner:
                # 파트너의 사용자 정보에서 닉네임 또는 사용자명 가져오기
                referrer_name = partner.user.nickname or partner.user.username
                logger.info(f"추천인 이름: {referrer_name}")
            else:
                logger.warning(f"추천인 코드 {referral_code}에 해당하는 파트너를 찾을 수 없음")
        
        result = {
            'has_referral': has_referral,
            'referral_code': referral_code,
            'referrer_name': referrer_name,
            'is_seller': user.role == 'seller',
            'can_add_referral': user.role == 'seller' and not has_referral
        }
        
        logger.info(f"추천인 상태 확인 결과: {result}")
        return Response(result)
    
    except Exception as e:
        logger.error(f"추천인 상태 확인 오류: {str(e)}")
        return Response(
            {'error': '추천인 정보를 확인할 수 없습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_user_phone(request):
    """
    아이디와 휴대폰 번호 일치 확인
    비밀번호 찾기 1단계: 사용자 확인
    """
    try:
        username = request.data.get('username', '').strip()
        phone_number = request.data.get('phone_number', '').strip()
        
        logger.info(f"비밀번호 찾기 시도: username={username}, phone_number={phone_number[:3]}****")
        
        if not username or not phone_number:
            return Response({
                'success': False,
                'message': '아이디와 휴대폰 번호를 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 전화번호 형식 정규화
        phone_number = phone_number.replace('-', '').replace(' ', '')
        
        # 사용자 조회
        try:
            user = User.objects.get(username=username)
            logger.info(f"사용자 찾음: {user.username}, phone_number={user.phone_number}")
        except User.DoesNotExist:
            logger.warning(f"사용자를 찾을 수 없음: username={username}")
            return Response({
                'success': False,
                'message': '일치하는 사용자 정보가 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 휴대폰 번호가 없는 경우 처리
        if not user.phone_number:
            logger.warning(f"사용자 {username}의 휴대폰 번호가 등록되지 않음")
            return Response({
                'success': False,
                'message': '등록된 휴대폰 번호가 없습니다. 고객센터에 문의해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 휴대폰 번호 확인 (DB의 전화번호도 정규화하여 비교)
        user_phone_normalized = user.phone_number.replace('-', '').replace(' ', '') if user.phone_number else ''
        if user_phone_normalized != phone_number:
            logger.warning(f"휴대폰 번호 불일치: 입력={phone_number}, DB={user_phone_normalized}")
            return Response({
                'success': False,
                'message': '일치하는 사용자 정보가 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 카카오 계정 확인
        is_kakao = hasattr(user, 'kakao_id') and user.kakao_id
        is_social = hasattr(user, 'sns_type') and user.sns_type  # SNS 타입 확인
        provider = getattr(user, 'sns_type', None)  # provider 정보
        
        if is_kakao or provider == 'kakao':
            logger.info(f"카카오 계정 사용자: {username}")
            return Response({
                'success': False,
                'message': '카카오 계정의 경우 카카오 계정 찾기를 이용해주세요.',
                'is_social': True,
                'provider': 'kakao'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"비밀번호 찾기 사용자 확인 성공: username={username}")
        
        return Response({
            'success': True,
            'message': '사용자 확인이 완료되었습니다.',
            'user_id': user.id,
            'is_social': is_social,
            'provider': provider
        })
        
    except Exception as e:
        logger.error(f"사용자 휴대폰 확인 오류: username={username}, error={str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': '사용자 확인 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_phone(request):
    """
    휴대폰 인증 후 비밀번호 변경
    비밀번호 찾기 2단계: 비밀번호 재설정
    """
    user_id = None
    try:
        user_id = request.data.get('user_id')
        phone_number = request.data.get('phone_number', '').strip()
        verification_code = request.data.get('verification_code', '').strip()
        new_password = request.data.get('new_password', '').strip()
        
        logger.info(f"비밀번호 재설정 시도: user_id={user_id}, phone_number={phone_number[:3] if phone_number else ''}****")
        
        if not all([user_id, phone_number, verification_code, new_password]):
            return Response({
                'success': False,
                'message': '필수 정보를 모두 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 전화번호 형식 정규화
        phone_number = phone_number.replace('-', '').replace(' ', '')
        
        # 사용자 조회 (phone_number 비교 시 정규화)
        try:
            user = User.objects.get(id=user_id)
            
            # 카카오 계정 재확인 (보안 강화)
            if hasattr(user, 'kakao_id') and user.kakao_id:
                logger.warning(f"카카오 계정 비밀번호 변경 시도 차단: user_id={user_id}")
                return Response({
                    'success': False,
                    'message': '카카오 계정은 비밀번호를 변경할 수 없습니다.',
                    'is_social': True,
                    'provider': 'kakao'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 전화번호 정규화하여 비교
            user_phone_normalized = user.phone_number.replace('-', '').replace(' ', '') if user.phone_number else ''
            if user_phone_normalized != phone_number:
                logger.warning(f"전화번호 불일치: user_id={user_id}, 입력={phone_number}, DB={user_phone_normalized}")
                raise User.DoesNotExist
        except User.DoesNotExist:
            logger.warning(f"사용자 정보 불일치: user_id={user_id}, phone_number={phone_number}")
            return Response({
                'success': False,
                'message': '사용자 정보가 일치하지 않습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 휴대폰 인증 확인 (is_verified 조건 제거 - 코드 일치만 확인)
        verification = PhoneVerification.objects.filter(
            phone_number=phone_number,
            verification_code=verification_code,  # 필드명 수정: code -> verification_code
            status='pending',  # pending 상태인 인증만
            created_at__gte=timezone.now() - timedelta(minutes=30)  # 30분 이내 인증
        ).first()
        
        if not verification:
            logger.warning(f"인증 실패: phone={phone_number}, code={verification_code}")
            # 디버깅을 위해 더 상세한 정보 로깅
            all_verifications = PhoneVerification.objects.filter(
                phone_number=phone_number,
                created_at__gte=timezone.now() - timedelta(minutes=30)
            )
            for v in all_verifications:
                logger.info(f"존재하는 인증: verification_code={v.verification_code}, status={v.status}")
            
            return Response({
                'success': False,
                'message': '휴대폰 인증이 유효하지 않습니다. 다시 인증해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 인증 성공 시 verified로 변경
        verification.status = 'verified'
        verification.verified_at = timezone.now()
        verification.save()
        
        # 비밀번호 유효성 검사
        if len(new_password) < 8:
            return Response({
                'success': False,
                'message': '비밀번호는 8자 이상이어야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 비밀번호 변경
        user.password = make_password(new_password)
        user.save()
        
        # 인증 기록 삭제
        PhoneVerification.objects.filter(phone_number=phone_number).delete()
        
        logger.info(f"비밀번호 재설정 성공: user_id={user_id}")
        
        # 단순한 JSON 응답만 반환
        return Response({
            'success': True,
            'message': '비밀번호가 변경되었습니다. 다시 로그인해주세요.',
            'user_id': user_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: user_id={user_id}, error={str(e)}", exc_info=True)
        
        # 디버그 모드에서는 상세 오류 표시
        if settings.DEBUG:
            error_message = f"오류: {str(e)}"
        else:
            error_message = '비밀번호 변경 중 오류가 발생했습니다.'
        
        return Response({
            'success': False,
            'message': error_message,
            'error_type': type(e).__name__  # 오류 타입 추가
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
