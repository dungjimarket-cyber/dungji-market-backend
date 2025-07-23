import logging
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, Region, GroupBuy, Participation
from .utils.s3_utils import upload_file_to_s3
from .serializers_jwt import CustomTokenObtainPairSerializer
import json

logger = logging.getLogger(__name__)

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
        profile_image = files.get('profile_image')
        
        # 판매자 전용 필드
        business_name = data.get('business_name', '')
        business_reg_number = data.get('business_reg_number', '')
        business_address = data.get('business_address', '')
        is_remote_sales_enabled = data.get('is_remote_sales_enabled', 'false').lower() == 'true'
        business_reg_image = files.get('business_reg_image')
        
        # 소셜 로그인 정보
        social_provider = data.get('social_provider', '')
        social_id = data.get('social_id', '')
        
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
        
        # 닉네임 중복 확인 (소셜 회원가입이거나 이메일이 없는 경우에만)
        if (not email or social_provider) and User.objects.filter(username=nickname).exists():
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
        
        # 이메일 회원가입인 경우 이메일 중복 확인
        if email and not social_provider:
            if User.objects.filter(email=email).exists():
                return Response(
                    {'error': '이미 사용 중인 이메일입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # username으로도 이메일이 사용될 예정이므로 username 중복 체크도 필요
            if User.objects.filter(username=email).exists():
                return Response(
                    {'error': '이미 사용 중인 이메일입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 판매자인 경우 추가 검증
        if role == 'seller':
            if not business_reg_number or not business_address:
                return Response(
                    {'error': '판매자는 사업자등록번호와 사업장 주소를 입력해야 합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        with transaction.atomic():
            # 사용자 생성
            # 이메일이 제공된 경우 실제 이메일 사용, 아니면 임시 이메일
            user_email = email if email else f'{nickname}@dungji.com'
            
            # 이메일 회원가입인 경우 username을 이메일로 설정 (로그인 시 이메일 사용)
            # 소셜 회원가입인 경우 username을 닉네임으로 설정
            if email and not social_provider:
                username_for_db = email  # 이메일 회원가입은 이메일을 username으로 사용
            else:
                username_for_db = nickname  # 소셜 회원가입은 닉네임을 username으로 사용
            
            user = User.objects.create(
                username=username_for_db,
                email=user_email,
                phone_number=phone_number,
                nickname=business_name if role == 'seller' and business_name else nickname,
                first_name=business_name if role == 'seller' and business_name else nickname,  # 임시로 유지
                role=role,
                sns_type=social_provider if social_provider else 'email',
                sns_id=social_id if social_id else None,
                is_remote_sales_enabled=is_remote_sales_enabled if role == 'seller' else False
            )
            
            # 비밀번호 설정
            user.set_password(password)
            
            # 지역 설정
            if region:
                try:
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
                user.business_reg_number = business_reg_number
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


@api_view(['POST'])
@permission_classes([AllowAny])
def check_nickname(request):
    """
    닉네임 중복 확인 API
    """
    try:
        nickname = request.data.get('nickname')
        
        if not nickname:
            return Response(
                {'error': '닉네임을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 닉네임 중복 확인
        is_available = not User.objects.filter(username=nickname).exists()
        
        return Response({
            'available': is_available,
            'nickname': nickname
        })
    
    except Exception as e:
        logger.error(f"닉네임 중복 확인 오류: {str(e)}")
        return Response(
            {'error': '닉네임 확인 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
        
        # 판매자 주소 업데이트
        if 'business_address_province' in data:
            user.business_address_province = data['business_address_province']
        
        if 'business_address_city' in data:
            user.business_address_city = data['business_address_city']
        
        if 'business_number' in data:
            user.business_number = data['business_number']
        
        if 'is_remote_sales' in data:
            user.is_remote_sales = data['is_remote_sales']
        
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
                user.is_remote_sales_enabled = data['is_remote_sales_enabled'].lower() == 'true'
        
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
        logger.error(f"프로필 업데이트 오류: {str(e)}")
        return Response(
            {'error': '프로필 업데이트 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def check_nickname(request):
    """닉네임 중복 확인"""
    nickname = request.data.get('nickname')
    
    if not nickname:
        return Response(
            {'error': '닉네임을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    exists = User.objects.filter(username=nickname).exists()
    
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
            groupbuy__status__in=['recruiting', 'bidding', 'voting', 'seller_confirmation']
        ).exists()
        
        if active_participations:
            return Response(
                {'error': '진행 중인 공구가 있어 탈퇴할 수 없습니다. 공구 종료 후 다시 시도해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 생성한 진행 중인 공구 확인
        active_created_groupbuys = GroupBuy.objects.filter(
            creator=user,
            status__in=['recruiting', 'bidding', 'voting', 'seller_confirmation']
        ).exists()
        
        if active_created_groupbuys:
            return Response(
                {'error': '진행 중인 생성 공구가 있어 탈퇴할 수 없습니다. 공구 종료 후 다시 시도해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 탈퇴 사유 로깅
        logger.info(f"회원 탈퇴 - User ID: {user.id}, Username: {user.username}, Reason: {reason}")
        
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
                    user.is_remote_sales_enabled = data['is_remote_sales_enabled'].lower() == 'true'
            
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
