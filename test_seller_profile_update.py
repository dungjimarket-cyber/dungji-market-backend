#!/usr/bin/env python
"""
판매회원 프로필 업데이트 API 테스트
"""
import os
import sys
import django
import json

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from api.models import Region

User = get_user_model()

def test_seller_profile_update():
    """판매회원 프로필 업데이트 테스트"""
    
    # 테스트 클라이언트 생성
    client = APIClient()
    
    # 테스트용 판매자 계정 생성 또는 가져오기
    seller_email = 'test_seller@example.com'
    password = 'testpass123'
    
    try:
        seller = User.objects.get(username='test_seller')
        print(f"기존 판매자 계정 사용: {seller.email}")
        # 이메일 업데이트 (테스트를 위해)
        seller.email = seller_email
        seller.save()
    except User.DoesNotExist:
        # 지역 생성
        region = Region.objects.get_or_create(
            code='1100000000',
            defaults={
                'name': '서울특별시',
                'full_name': '서울특별시',
                'level': 0
            }
        )[0]
        
        seller = User.objects.create_user(
            username='test_seller',
            email=seller_email,
            password=password,
            role='seller',
            address_region=region
        )
        print(f"새 판매자 계정 생성: {seller.email}")
    
    # 로그인
    login_response = client.post('/api/auth/login/', {
        'username': seller.username,
        'password': password
    })
    
    if login_response.status_code != 200:
        print(f"로그인 실패: 상태 코드 {login_response.status_code}")
        print(f"응답 내용: {login_response.content.decode()}")
        return
    
    login_data = json.loads(login_response.content)
    token = login_data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    print("로그인 성공")
    
    # 1. 현재 프로필 조회
    print("\n=== 현재 프로필 조회 ===")
    profile_response = client.get('/api/users/me/seller-profile/')
    if profile_response.status_code == 200:
        profile_data = json.loads(profile_response.content)
        print(f"현재 이메일: {profile_data.get('email')}")
        print(f"현재 대표자명: {profile_data.get('representativeName', '없음')}")
        print(f"현재 사업자등록번호: {profile_data.get('businessNumber', '없음')}")
        print(f"사업자번호 인증 상태: {profile_data.get('businessVerified', False)}")
    else:
        print(f"프로필 조회 실패: {profile_response.content.decode()}")
    
    # 2. 프로필 업데이트 테스트 (이메일, 대표자명)
    print("\n=== 프로필 업데이트 (이메일, 대표자명) ===")
    update_data = {
        'email': 'updated_seller@example.com',
        'representative_name': '홍길동',
        'nickname': 'test_seller_nick'
    }
    
    update_response = client.patch('/api/users/me/seller-profile/', update_data)
    if update_response.status_code == 200:
        update_result = json.loads(update_response.content)
        print("업데이트 성공!")
        print(f"새 이메일: {update_result.get('email')}")
        print(f"새 대표자명: {update_result.get('representativeName')}")
    else:
        print(f"업데이트 실패: {update_response.content.decode()}")
    
    # 3. 사업자등록번호 업데이트 테스트 (유효하지 않은 번호)
    print("\n=== 사업자등록번호 업데이트 (유효하지 않은 번호) ===")
    invalid_business_data = {
        'business_number': '1234567890'  # 유효하지 않은 번호
    }
    
    invalid_response = client.patch('/api/users/me/seller-profile/', invalid_business_data)
    if invalid_response.status_code == 400:
        print(f"예상대로 실패: {invalid_response.content.decode()}")
    else:
        print(f"예상치 못한 응답: {invalid_response.status_code} - {invalid_response.content.decode()}")
    
    # 4. 사업자등록번호 업데이트 테스트 (유효한 번호 - 실제 테스트용 번호)
    print("\n=== 사업자등록번호 업데이트 (테스트용 유효 번호) ===")
    # 국세청 테스트용 사업자번호 사용 (실제 환경에서는 실제 번호 필요)
    valid_business_data = {
        'business_number': '000-00-00000'  # 테스트용 번호 (실제 API에서는 유효한 번호 필요)
    }
    
    valid_response = client.patch('/api/users/me/seller-profile/', valid_business_data)
    print(f"응답 상태: {valid_response.status_code}")
    if valid_response.status_code == 200:
        valid_result = json.loads(valid_response.content)
        print("사업자등록번호 업데이트 성공!")
        print(f"사업자번호: {valid_result.get('businessNumber')}")
        print(f"인증 상태: {valid_result.get('businessVerified')}")
    else:
        print(f"업데이트 결과: {valid_response.content.decode()}")
    
    # 5. 인증된 사업자번호 수정 시도 테스트
    if seller.is_business_verified:
        print("\n=== 인증된 사업자번호 수정 시도 ===")
        modify_business_data = {
            'business_number': '111-11-11111'
        }
        
        modify_response = client.patch('/api/users/me/seller-profile/', modify_business_data)
        if modify_response.status_code == 400:
            print(f"예상대로 수정 불가: {modify_response.content.decode()}")
        else:
            print(f"예상치 못한 응답: {modify_response.status_code}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == '__main__':
    test_seller_profile_update()