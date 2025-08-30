#!/usr/bin/env python
"""
관리자 API 테스트 스크립트
"""

import requests
import json
import sys

# API 엔드포인트 설정
BASE_URL = "https://api.dungjimarket.com"  # 운영 서버
# BASE_URL = "http://localhost:8000"  # 로컬 테스트

def login_admin():
    """관리자 로그인하여 JWT 토큰 획득"""
    print("\n=== 관리자 로그인 테스트 ===")
    
    # 관리자 계정 정보 (실제 관리자 계정으로 변경 필요)
    login_data = {
        "username": "admin",  # 실제 관리자 아이디로 변경
        "password": "admin_password"  # 실제 관리자 비밀번호로 변경
    }
    
    url = f"{BASE_URL}/api/auth/login/"
    response = requests.post(url, json=login_data)
    
    print(f"URL: {url}")
    print(f"응답 상태: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('access')
        refresh_token = data.get('refresh')
        user_role = data.get('user', {}).get('role')
        
        print(f"✅ 로그인 성공!")
        print(f"사용자 역할: {user_role}")
        print(f"Access Token: {access_token[:20]}...")
        
        return access_token, user_role
    else:
        print(f"❌ 로그인 실패: {response.text}")
        return None, None

def test_admin_endpoints(token):
    """관리자 API 엔드포인트 테스트"""
    if not token:
        print("토큰이 없어 테스트를 진행할 수 없습니다.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n=== 관리자 API 엔드포인트 테스트 ===")
    
    # 1. 관리자 ViewSet 기본 엔드포인트
    print("\n1. Admin ViewSet 테스트:")
    response = requests.get(f"{BASE_URL}/api/admin/", headers=headers)
    print(f"GET /api/admin/: {response.status_code}")
    if response.status_code == 200:
        print(f"응답: {response.json()}")
    else:
        print(f"오류: {response.text}")
    
    # 2. 사용자 검색 API
    print("\n2. 사용자 검색 API 테스트:")
    search_params = {"query": "test"}
    response = requests.get(
        f"{BASE_URL}/api/admin/users/search/", 
        headers=headers,
        params=search_params
    )
    print(f"GET /api/admin/users/search/: {response.status_code}")
    if response.status_code == 200:
        print(f"검색 결과: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:500]}")
    else:
        print(f"오류: {response.text}")
    
    # 3. 입찰권 조정 API
    print("\n3. 입찰권 조정 API 테스트:")
    adjust_data = {
        "user_id": 1,  # 테스트용 사용자 ID
        "adjustment_type": "add",
        "amount": 5,
        "reason": "테스트 입찰권 추가"
    }
    response = requests.post(
        f"{BASE_URL}/api/admin/bid-tokens/adjust/",
        headers=headers,
        json=adjust_data
    )
    print(f"POST /api/admin/bid-tokens/adjust/: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"응답: {response.json()}")
    else:
        print(f"오류: {response.text}")

def test_permission_denied():
    """일반 사용자로 관리자 API 접근 테스트"""
    print("\n=== 권한 거부 테스트 ===")
    
    # 일반 사용자 로그인
    login_data = {
        "username": "testuser",  # 일반 사용자 계정
        "password": "testpassword"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login/", json=login_data)
    
    if response.status_code == 200:
        token = response.json().get('access')
        headers = {"Authorization": f"Bearer {token}"}
        
        # 관리자 API 접근 시도
        response = requests.get(f"{BASE_URL}/api/admin/", headers=headers)
        print(f"일반 사용자의 관리자 API 접근: {response.status_code}")
        
        if response.status_code == 403:
            print("✅ 정상적으로 접근이 거부되었습니다.")
        else:
            print(f"⚠️ 예상치 못한 응답: {response.text}")
    else:
        print("일반 사용자 로그인 실패 - 권한 테스트 생략")

def check_cors_headers():
    """CORS 헤더 확인"""
    print("\n=== CORS 설정 확인 ===")
    
    # OPTIONS 요청으로 CORS 확인
    headers = {
        "Origin": "https://dungjimarket.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"
    }
    
    response = requests.options(f"{BASE_URL}/api/admin/", headers=headers)
    
    print("CORS 관련 응답 헤더:")
    cors_headers = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Credentials"
    ]
    
    for header in cors_headers:
        value = response.headers.get(header)
        if value:
            print(f"  {header}: {value}")
    
    if response.headers.get("Access-Control-Allow-Origin"):
        print("✅ CORS 설정이 활성화되어 있습니다.")
    else:
        print("⚠️ CORS 설정을 확인해주세요.")

if __name__ == "__main__":
    print("=" * 60)
    print("관리자 API 테스트 시작")
    print("=" * 60)
    
    # CORS 확인
    check_cors_headers()
    
    # 관리자 로그인
    token, role = login_admin()
    
    if token and role == 'admin':
        # 관리자 API 테스트
        test_admin_endpoints(token)
    elif token:
        print(f"\n⚠️ 사용자 역할이 'admin'이 아닙니다: {role}")
        print("관리자 권한이 필요합니다.")
    
    # 권한 거부 테스트
    # test_permission_denied()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    
    print("\n💡 문제 해결 체크리스트:")
    print("1. 사용자의 role 필드가 'admin'으로 설정되어 있는지 확인")
    print("2. JWT 토큰에 role 정보가 포함되어 있는지 확인") 
    print("3. CORS 설정이 올바른지 확인")
    print("4. 서버가 최신 코드로 배포되었는지 확인")