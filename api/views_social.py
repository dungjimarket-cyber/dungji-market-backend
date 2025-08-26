from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging
import os
import requests
import json

logger = logging.getLogger(__name__)

# 소셜 로그인 설정 - .env 파일에서 가져옴
KAKAO_CLIENT_ID = os.environ.get('KAKAO_CLIENT_ID', '')
if not KAKAO_CLIENT_ID:
    logger.error("KAKAO_CLIENT_ID 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    KAKAO_CLIENT_ID = 'a197177aee0ddaf6b827a6225aa48653'  # 이 키는 프론트엔드 .env.local에서 삽입

# 환경별 리다이렉트 URI 설정
REDIRECT_URIS = {
    'development': 'http://localhost:3000/api/auth/callback/kakao',
    'production': 'https://dungjimarket.com/api/auth/callback/kakao',
    'staging': 'https://staging.dungjimarket.com/api/auth/callback/kakao',
}

# 현재 환경에 맞는 리다이렉트 URI 선택
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')
DEFAULT_REDIRECT_URI = REDIRECT_URIS.get(ENVIRONMENT, REDIRECT_URIS['development'])

# 환경별 설정 로깅
logger.info(f"현재 환경: {ENVIRONMENT}")
logger.info(f"기본 리다이렉트 URI: {DEFAULT_REDIRECT_URI}")

logger.info(f"KAKAO_CLIENT_ID: {KAKAO_CLIENT_ID}")

@api_view(['POST'])
@permission_classes([AllowAny])
def check_kakao_user_exists(request):
    """
    카카오 사용자가 이미 가입되어 있는지 확인하는 API
    """
    try:
        # 카카오 액세스 토큰으로 사용자 정보 가져오기
        access_token = request.data.get('access_token')
        if not access_token:
            return Response({
                'error': 'access_token이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 카카오 API로 사용자 정보 요청
        kakao_response = requests.get(
            'https://kapi.kakao.com/v2/user/me',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
            }
        )
        
        if kakao_response.status_code != 200:
            return Response({
                'error': '카카오 사용자 정보를 가져올 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        kakao_data = kakao_response.json()
        kakao_id = str(kakao_data.get('id'))
        
        # 기존 사용자 확인
        from .models import User
        try:
            existing_user = User.objects.get(social_id=kakao_id, social_provider='kakao')
            return Response({
                'exists': True,
                'user_id': existing_user.id,
                'role': existing_user.role
            })
        except User.DoesNotExist:
            return Response({
                'exists': False,
                'kakao_id': kakao_id
            })
            
    except Exception as e:
        logger.error(f"카카오 사용자 존재 확인 중 오류: {str(e)}")
        return Response({
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_kakao_auth_url(next_url, redirect_uri=None, role=None, request=None):
    """
    카카오 인증 URL 생성 함수
    
    Args:
        next_url: 인증 후 배경 애플리케이션으로 리디렉션할 URL
        redirect_uri: 클라이언트에서 제공한 리디렉트 URI (부영시 기본값 사용)
        role: 가입 유형 ('buyer' 또는 'seller')
        request: HTTP request 객체 (추천인 코드 추출용)
    """
    # state에 next_url, role, referral_code 정보를 함께 저장 (JSON 형식)
    import json
    from urllib.parse import quote
    
    # request에서 referral_code 가져오기
    referral_code = request.GET.get('referral_code', '') if request else ''
    
    state_data = {
        'next_url': next_url,
        'role': role or 'buyer',  # 기본값은 buyer
        'referral_code': referral_code  # 추천인 코드 추가
    }
    state = quote(json.dumps(state_data))
    
    # 클라이언트가 제공한 redirect_uri 사용 또는 기본값 사용
    actual_redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI
    
    
    # 카카오 로그인 URL 생성 - 추가 스코프 포함
    # profile_nickname: 닉네임
    # profile_image: 프로필 사진
    # account_email: 이메일
    # phone_number: 전화번호
    scope = "profile_nickname,profile_image,account_email,phone_number"
    kakao_auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}&redirect_uri={actual_redirect_uri}&response_type=code&state={state}&scope={scope}"
    
    logger.info(f"카카오 인증 URL: {kakao_auth_url}")
    logger.info(f"사용된 리디렉트 URI: {actual_redirect_uri}")
    return kakao_auth_url

@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def kakao_login(request):
    """
    카카오 로그인 시작 - 카카오 인증 서버로 리다이렉트
    """
    next_url = request.GET.get('next', '')
    # 클라이언트가 제공한 리디렉트 URI 사용
    redirect_uri = request.GET.get('redirect_uri', None)
    # 가입 유형 받기 (seller 또는 buyer)
    role = request.GET.get('role', 'buyer')
    # 추천인 코드 받기
    referral_code = request.GET.get('referral_code', '')
    
    logger.info(f"카카오 로그인 시작: next_url={next_url}, redirect_uri={redirect_uri}, role={role}, referral_code={referral_code}")
    
    # get_kakao_auth_url에 request 전달
    kakao_auth_url = get_kakao_auth_url(next_url, redirect_uri, role, request=request)
    return redirect(kakao_auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def kakao_callback(request):
    """
    카카오 인증 후 콜백 처리
    """
    code = request.GET.get('code')
    state = request.GET.get('state', '')  # 이전에 저장한 state (JSON 형식)
    
    logger.info(f"카카오 콜백 도착: code={code}, state={state}")
    
    # state 파싱하여 next_url, role, referral_code 추출
    import json
    from urllib.parse import unquote
    
    try:
        state_data = json.loads(unquote(state))
        next_url = state_data.get('next_url', '')
        role = state_data.get('role', 'buyer')
        referral_code = state_data.get('referral_code', '')
    except (json.JSONDecodeError, TypeError):
        # 이전 버전 호환성을 위해 state를 그대로 next_url로 사용
        next_url = state
        role = 'buyer'
        referral_code = ''
    
    logger.info(f"파싱된 state 정보: next_url={next_url}, role={role}, referral_code={referral_code}")
    
    if not code:
        logger.error("인증 코드가 없습니다.")
        return HttpResponse("인증 코드가 없습니다.", status=400)
    
    # 클라이언트가 제공한 리디렉트 URI 가져오기
    redirect_uri = request.GET.get('redirect_uri', DEFAULT_REDIRECT_URI)
    
    # 의심 스러운 URI 검사 및 기록
    logger.info(f"콜백을 위한 리디렉트 URI: {redirect_uri}")
    
    # 현재 카카오 개발자 콘솔에 등록된 리디렉트 URI로 확인된 것들
    # 환경 기반 URI 설정
    REGISTERED_REDIRECT_URIS = [
        # 프로덕션 URI
        'https://dungjimarket.com/api/auth/callback/kakao',
        'https://www.dungjimarket.com/api/auth/callback/kakao',
        # 개발 환경 URI
        'http://localhost:3000/api/auth/callback/kakao',
        # 스테이징 URI (있는 경우)
        'https://staging.dungjimarket.com/api/auth/callback/kakao',
    ]
    
    # 현재 환경 설정에 따른 기본 URI 추가
    if DEFAULT_REDIRECT_URI not in REGISTERED_REDIRECT_URIS:
        REGISTERED_REDIRECT_URIS.append(DEFAULT_REDIRECT_URI)
        logger.info(f"기본 리다이렉트 URI 추가: {DEFAULT_REDIRECT_URI}")
    
    # 공식 URI + 사용자 제공 URI를 모두 추가
    possible_uris = REGISTERED_REDIRECT_URIS[:]
    
    # 사용자가 제공한 URI가 등록된 것이 아니면 추가
    if redirect_uri not in possible_uris:
        possible_uris.append(redirect_uri)
        logger.info(f"사용자 제공 URI 추가: {redirect_uri}")
        
    # www 버전도 추가 고려
    www_domain_uri = None
    non_www_domain_uri = None
    
    if redirect_uri.startswith('https://dungjimarket.com'):
        www_domain_uri = redirect_uri.replace('https://dungjimarket.com', 'https://www.dungjimarket.com')
        possible_uris.append(www_domain_uri)
        logger.info(f"www 버전 URI 추가: {www_domain_uri}")
    elif redirect_uri.startswith('https://www.dungjimarket.com'):
        non_www_domain_uri = redirect_uri.replace('https://www.dungjimarket.com', 'https://dungjimarket.com')
        possible_uris.append(non_www_domain_uri)
        logger.info(f"non-www 버전 URI 추가: {non_www_domain_uri}")
    
    # 토큰 요청 실패 시 대체 URI로 재시도
    token_url = "https://kauth.kakao.com/oauth/token"
    token_response = None
    token_json = None
    
    for uri in possible_uris:
        data = {
            'grant_type': 'authorization_code',
            'client_id': KAKAO_CLIENT_ID,
            'redirect_uri': uri,
            'code': code,
        }
        
        logger.info(f"Kakao token request: redirect_uri={uri}")
        logger.info(f"Kakao token request data: {data}")
        
        try:
            token_response = requests.post(token_url, data=data)
            token_json = token_response.json()
            
            if 'access_token' in token_json:
                logger.info(f"카카오 토큰 요청 성공 with {uri}")
                break
            else:
                logger.error(f"카카오 토큰 요청 실패 with {uri}: {token_json}")
        except Exception as e:
            logger.error(f"카카오 토큰 요청 예외 with {uri}: {str(e)}")
    
    # 모든 URI로 시도해도 실패한 경우
    if not token_json or 'access_token' not in token_json:
        logger.error(f"모든 리디렉트 URI로 카카오 토큰 요청 실패")
        return HttpResponse("카카오 인증 토큰 획득 실패", status=400)
    
    # 인증 성공 후 처리    
    access_token = token_json['access_token']
    
    # 사용자 정보 요청
    user_info_response = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_info = user_info_response.json()
    
    logger.info(f"카카오 사용자 정보: {user_info}")
    
    # 필요한 정보 추출 (추가된 스코프 포함)
    kakao_id = user_info.get('id')
    kakao_account = user_info.get('kakao_account', {})
    profile = kakao_account.get('profile', {})
    
    # 기본 정보
    email = kakao_account.get('email', f'{kakao_id}@kakao.user')
    nickname = profile.get('nickname', '')
    profile_image = profile.get('profile_image_url', '')
    
    # 추가 정보
    phone_number = kakao_account.get('phone_number', '')  # 전화번호 추가
    # 전화번호 포맷 변환 (+82 10-1234-5678 -> 01012345678)
    if phone_number:
        phone_number = phone_number.replace('+82 ', '0').replace('-', '')
        logger.info(f"카카오 전화번호 변환: {kakao_account.get('phone_number')} -> {phone_number}")
    
    # 기존 SNS 로그인 엔드포인트로 POST 요청 생성
    sns_login_data = {
        'sns_id': str(kakao_id),
        'sns_type': 'kakao',
        'email': email,
        'name': nickname,
        'profile_image': profile_image,
        'phone_number': phone_number,  # 전화번호 추가
        'role': role,  # 가입 유형 전달
        'referral_code': referral_code  # 추천인 코드 전달
    }
    
    # 내부 API 호출 - 직접 create_sns_user 함수 호출 또는 여기서 사용자 생성/로그인 로직 구현
    from api.views import create_sns_user
    from django.http import HttpRequest
    from django.contrib.auth import get_user_model
    from rest_framework.parsers import JSONParser
    from io import BytesIO
    
    # JSON 데이터로 변환
    json_data = json.dumps(sns_login_data).encode('utf-8')
    
    # 가상 요청 객체 생성
    mock_request = HttpRequest()
    mock_request.META = request.META
    mock_request._body = json_data
    mock_request.method = 'POST'
    
    try:
        # POST 데이터 파싱
        stream = BytesIO(json_data)
        data = JSONParser().parse(stream)
        mock_request.data = data
        
        # SNS 로그인 함수 호출
        response = create_sns_user(mock_request)
        
        # 응답 내용 확인
        if response.status_code == 201 or response.status_code == 200:
            # JWT 토큰 획득
            jwt_data = response.data.get('jwt', {})
            access_token = jwt_data.get('access', '')
            refresh_token = jwt_data.get('refresh', '')
            
            # 신규 사용자 여부 확인
            is_new_user = response.data.get('is_new_user', False)
            
            # 원래 요청된 next URL로 리다이렉트 (토큰 포함)
            redirect_url = next_url  # state가 아닌 파싱된 next_url 사용
            
            # 쿼리 파라미터 구분자 설정
            separator = '&' if '?' in redirect_url else '?'
            complete_url = f"{redirect_url}{separator}access_token={access_token}&refresh_token={refresh_token}"
            
            # 신규 사용자인 경우 플래그 추가
            if is_new_user:
                complete_url += "&is_new_user=true"
            
            logger.info(f"로그인 성공. 리다이렉트: {complete_url}, 신규 사용자: {is_new_user}")
            return redirect(complete_url)
        else:
            logger.error(f"SNS 로그인 처리 실패: {response.data}")
            error_message = response.data.get('error', '소셜 로그인 중 오류가 발생했습니다.')
            return HttpResponse(error_message, status=response.status_code)
            
    except Exception as e:
        logger.exception(f"카카오 로그인 처리 중 오류: {str(e)}")
        return HttpResponse("소셜 로그인 처리 중 오류가 발생했습니다.", status=500)

@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def social_login_dispatch(request, provider):
    """
    소셜 로그인 요청을 알맞은 서비스 로그인 함수로 보내는 디스패처
    
    URL 경로에서 provider 매개변수를 받습니다.
    """
    next_url = request.GET.get('next', '')
    redirect_uri = request.GET.get('redirect_uri', None)
    role = request.GET.get('role', 'buyer')  # 가입 유형 받기
    referral_code = request.GET.get('referral_code', '')  # 추천인 코드 받기
    
    logger.info(f"소셜 로그인 요청: provider={provider}, next={next_url}, role={role}, referral_code={referral_code}")
    
    if provider == 'kakao':
        # 카카오 로그인 URL로 리다이렉트 (클라이언트에서 제공한 redirect_uri와 role 사용)
        logger.info(f"카카오 로그인 시작: next_url={next_url}, redirect_uri={redirect_uri}, role={role}, referral_code={referral_code}")
        kakao_auth_url = get_kakao_auth_url(next_url, redirect_uri, role, request)
        return redirect(kakao_auth_url)
    # elif provider == 'google':
    #     return google_login(request)
    # elif provider == 'naver':
    #     return naver_login(request)
    else:
        return Response(
            {"error": f"지원하지 않는 소셜 로그인 제공자: {provider}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
