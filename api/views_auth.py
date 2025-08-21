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
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, Region, GroupBuy, Participation
from .models_verification import EmailVerification
from .utils.s3_utils import upload_file_to_s3
from .utils.resend_sender import ResendSender
from .serializers_jwt import CustomTokenObtainPairSerializer
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
        # multipart/form-data로 전송된 데이터 처리
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
        
        # 추천인 코드 검증 (입력된 경우만)
        referrer_user = None
        if referral_code:
            # TODO: 실제 둥지파트너스 시스템 구축 시 추천인 코드 검증 로직 구현
            # 현재는 테스트용으로 'PARTNER' 코드만 유효하다고 가정
            if referral_code.upper() == 'PARTNER':
                # 임시로 admin 사용자를 추천인으로 설정 (실제로는 파트너 시스템에서 조회)
                try:
                    referrer_user = User.objects.filter(role='admin').first()
                    logger.info(f"유효한 추천인 코드 사용: {referral_code}")
                except User.DoesNotExist:
                    logger.warning(f"추천인을 찾을 수 없음: {referral_code}")
            else:
                logger.info(f"무효한 추천인 코드: {referral_code}")
        
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
        
        with transaction.atomic():
            # 사용자 생성
            # 이메일이 제공된 경우 실제 이메일 사용, 아니면 임시 이메일
            user_email = email if email else f'{nickname}@dungji.com'
            
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
                nickname=business_name if role == 'seller' and business_name else nickname,
                first_name=verified_name or (business_name if role == 'seller' and business_name else nickname),  # 인증 시 입력한 이름 우선 사용
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
                # 사업자등록번호 하이픈 제거 후 저장 (값이 있는 경우만)
                if business_reg_number:
                    user.business_number = business_reg_number.replace('-', '')
                if representative_name:
                    user.representative_name = representative_name
                if business_address:
                    user.address_detail = business_address
                
                # seller1~seller10은 테스트 계정으로 자동으로 사업자 인증 완료 처리
                test_accounts = [f'seller{i}' for i in range(1, 11)]
                if username_for_db in test_accounts:
                    user.is_business_verified = True
                    logger.info(f"테스트 계정 {username_for_db} 자동 사업자 인증 완료")
                
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
                if referrer_user and referral_code.upper() == 'PARTNER':
                    bonus_tokens = 10
                    logger.info(f"추천인 코드 보너스 적용: +{bonus_tokens}매")
                
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
                    
                    # 파트너 정보 조회 (임시로 첫 번째 파트너 사용)
                    partner = Partner.objects.first()
                    
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
        if 'business_number' in data:
            user.business_number = data['business_number']
        
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
        
        return Response({
            'message': '프로필이 업데이트되었습니다.',
            'profile': {
                'username': user.username,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'profile_image': user.profile_image,
                'role': user.role
            }
        })
    
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
        return Response({
            'username': user.username,
            'message': '아이디를 찾았습니다.'
        })
    except User.DoesNotExist:
        return Response(
            {'error': '해당 휴대폰 번호로 등록된 사용자가 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )


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
