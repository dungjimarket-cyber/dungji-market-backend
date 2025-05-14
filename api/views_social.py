from django.shortcuts import redirect
from django.conf import settings
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
    KAKAO_CLIENT_ID = '48a8af8c364ef5e225460c2086473554'  # 이 키는 프론트엔드 .env.local에서 삽입

# 카카오 개발자 콘솔에 등록된 리다이렉트 URI
KAKAO_REDIRECT_URI = os.environ.get('KAKAO_REDIRECT_URI', 'http://localhost:3000/api/auth/callback/kakao')

logger.info(f"KAKAO_CLIENT_ID: {KAKAO_CLIENT_ID}")
logger.info(f"KAKAO_REDIRECT_URI: {KAKAO_REDIRECT_URI}")

def get_kakao_auth_url(next_url):
    """
    카카오 인증 URL 생성 함수
    """
    # state에 next_url 포함시켜 저장
    state = next_url
    
    # 카카오 로그인 URL 생성
    kakao_auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code&state={state}"
    
    logger.info(f"카카오 인증 URL: {kakao_auth_url}")
    return kakao_auth_url

@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def kakao_login(request):
    """
    카카오 로그인 시작 - 카카오 인증 서버로 리다이렉트
    """
    next_url = request.GET.get('next', '')
    logger.info(f"카카오 로그인 시작: next_url={next_url}")
    
    kakao_auth_url = get_kakao_auth_url(next_url)
    return redirect(kakao_auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def kakao_callback(request):
    """
    카카오 인증 후 콜백 처리
    """
    code = request.GET.get('code')
    state = request.GET.get('state', '')  # 이전에 저장한 next_url
    
    logger.info(f"카카오 콜백 도착: code={code}, state={state}")
    
    if not code:
        logger.error("인증 코드가 없습니다.")
        return HttpResponse("인증 코드가 없습니다.", status=400)
    
    # 토큰 요청
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        'grant_type': 'authorization_code',
        'client_id': KAKAO_CLIENT_ID,
        'redirect_uri': KAKAO_REDIRECT_URI,  # 카카오 개발자 콘솔에 등록된 URI와 정확히 일치해야 함
        'code': code,
    }
    
    logger.info(f"Kakao token request: redirect_uri={KAKAO_REDIRECT_URI}")
    logger.info(f"Kakao token request data: {data}")
    
    try:
        token_response = requests.post(token_url, data=data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            logger.error(f"카카오 토큰 요청 실패: {token_json}")
            return HttpResponse("카카오 로그인 중 오류가 발생했습니다.", status=400)
            
        access_token = token_json['access_token']
        
        # 사용자 정보 요청
        user_info_response = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_info = user_info_response.json()
        
        logger.info(f"카카오 사용자 정보: {user_info}")
        
        # 필요한 정보 추출
        kakao_id = user_info.get('id')
        kakao_account = user_info.get('kakao_account', {})
        profile = kakao_account.get('profile', {})
        
        email = kakao_account.get('email', f'{kakao_id}@kakao.user')
        nickname = profile.get('nickname', '')
        profile_image = profile.get('profile_image_url', '')
        
        # 기존 SNS 로그인 엔드포인트로 POST 요청 생성
        sns_login_data = {
            'sns_id': str(kakao_id),
            'sns_type': 'kakao',
            'email': email,
            'name': nickname,
            'profile_image': profile_image
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
            
            # 원래 요청된 next URL로 리다이렉트 (토큰 포함)
            redirect_url = state
            
            # 쿼리 파라미터 구분자 설정
            separator = '&' if '?' in redirect_url else '?'
            complete_url = f"{redirect_url}{separator}access_token={access_token}&refresh_token={refresh_token}"
            
            logger.info(f"로그인 성공. 리다이렉트: {complete_url}")
            return redirect(complete_url)
        else:
            logger.error(f"SNS 로그인 처리 실패: {response.data}")
            error_message = response.data.get('error', '소셜 로그인 중 오류가 발생했습니다.')
            return HttpResponse(error_message, status=response.status_code)
            
    except Exception as e:
        logger.exception(f"카카오 로그인 처리 중 오류: {str(e)}")
        return HttpResponse("소셜 로그인 처리 중 오류가 발생했습니다.", status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def social_login_dispatch(request, provider):
    """
    소셜 로그인 요청을 알맞은 서비스 로그인 함수로 보내는 디스패처
    
    URL 경로에서 provider 매개변수를 받습니다.
    """
    next_url = request.GET.get('next', '')
    
    logger.info(f"소셜 로그인 요청: provider={provider}, next={next_url}")
    
    if provider == 'kakao':
        # 카카오 로그인 URL로 리다이렉트
        logger.info(f"카카오 로그인 시작: next_url={next_url}")
        kakao_auth_url = get_kakao_auth_url(next_url)
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
