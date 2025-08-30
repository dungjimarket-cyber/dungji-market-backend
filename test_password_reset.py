#!/usr/bin/env python
"""
비밀번호 재설정 API 테스트 스크립트
"""

import requests
import json

# API 엔드포인트 설정
BASE_URL = "https://api.dungjimarket.com"  # 또는 로컬 테스트: "http://localhost:8000"

def test_verify_user_phone():
    """사용자 확인 API 테스트"""
    print("\n=== 사용자 확인 API 테스트 ===")
    
    # 테스트 데이터
    test_data = {
        "username": "testuser",  # 실제 존재하는 사용자명으로 변경
        "phone_number": "01012345678"  # 실제 존재하는 휴대폰 번호로 변경
    }
    
    # API 호출
    url = f"{BASE_URL}/api/auth/verify-user-phone/"
    response = requests.post(url, json=test_data)
    
    print(f"URL: {url}")
    print(f"요청 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print(f"응답 상태 코드: {response.status_code}")
    print(f"응답 내용: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        user_id = response.json().get('user_id')
        print(f"✅ 성공! user_id: {user_id}")
        return user_id
    else:
        print(f"❌ 실패!")
        return None

def test_reset_password_phone(user_id):
    """비밀번호 재설정 API 테스트"""
    print("\n=== 비밀번호 재설정 API 테스트 ===")
    
    # 테스트 데이터
    test_data = {
        "user_id": user_id,
        "phone_number": "01012345678",  # 위와 동일한 번호
        "verification_code": "123456",  # 실제 발송된 인증 코드
        "new_password": "newPassword123!"
    }
    
    # API 호출
    url = f"{BASE_URL}/api/auth/reset-password-phone/"
    response = requests.post(url, json=test_data)
    
    print(f"URL: {url}")
    print(f"요청 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print(f"응답 상태 코드: {response.status_code}")
    print(f"응답 내용: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print(f"✅ 비밀번호 재설정 성공!")
    else:
        print(f"❌ 비밀번호 재설정 실패!")

def test_error_cases():
    """오류 케이스 테스트"""
    print("\n=== 오류 케이스 테스트 ===")
    
    # 1. 잘못된 사용자명
    print("\n1. 잘못된 사용자명 테스트:")
    url = f"{BASE_URL}/api/auth/verify-user-phone/"
    response = requests.post(url, json={
        "username": "nonexistentuser",
        "phone_number": "01012345678"
    })
    print(f"응답: {response.status_code} - {response.json()}")
    
    # 2. 빈 데이터
    print("\n2. 빈 데이터 테스트:")
    response = requests.post(url, json={})
    print(f"응답: {response.status_code} - {response.json()}")
    
    # 3. 잘못된 전화번호 형식
    print("\n3. 잘못된 전화번호 형식 테스트:")
    response = requests.post(url, json={
        "username": "testuser",
        "phone_number": "123"
    })
    print(f"응답: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    print("=" * 50)
    print("비밀번호 재설정 API 테스트 시작")
    print("=" * 50)
    
    # 사용자 확인 테스트
    user_id = test_verify_user_phone()
    
    # user_id가 있으면 비밀번호 재설정 테스트
    # 주의: 실제 인증 코드가 필요하므로 수동으로 인증 후 테스트
    # if user_id:
    #     test_reset_password_phone(user_id)
    
    # 오류 케이스 테스트
    test_error_cases()
    
    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)