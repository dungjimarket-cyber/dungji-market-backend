#!/usr/bin/env python
"""
비밀번호 재설정 API 디버그 테스트
"""

import requests
import json

BASE_URL = "https://api.dungjimarket.com"

def test_reset_password():
    """비밀번호 재설정 API 테스트"""
    print("\n=== 비밀번호 재설정 API 디버그 테스트 ===")
    
    # 테스트 데이터 (실제 값으로 변경 필요)
    test_data = {
        "user_id": 1,  # verify-user-phone에서 받은 실제 user_id
        "phone_number": "01012345678",  # 실제 전화번호
        "verification_code": "123456",  # 실제 인증 코드
        "new_password": "newPassword123!"
    }
    
    print(f"요청 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    # API 호출
    url = f"{BASE_URL}/api/auth/reset-password-phone/"
    
    try:
        response = requests.post(url, json=test_data)
        
        print(f"\n응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"응답 내용: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
        except:
            print(f"응답 텍스트: {response.text}")
            
        if response.status_code == 500:
            print("\n⚠️ 500 에러 발생!")
            print("가능한 원인:")
            print("1. user_id가 숫자가 아닌 문자열로 전송됨")
            print("2. PhoneVerification 모델 조회 오류")
            print("3. 비밀번호 저장 중 오류")
            print("4. 데이터베이스 연결 문제")
            
    except Exception as e:
        print(f"요청 실패: {str(e)}")

def test_data_types():
    """다양한 데이터 타입으로 테스트"""
    print("\n=== 데이터 타입 테스트 ===")
    
    test_cases = [
        {
            "name": "user_id as string",
            "data": {
                "user_id": "1",  # 문자열
                "phone_number": "01012345678",
                "verification_code": "123456",
                "new_password": "newPassword123!"
            }
        },
        {
            "name": "user_id as number",
            "data": {
                "user_id": 1,  # 숫자
                "phone_number": "01012345678",
                "verification_code": "123456",
                "new_password": "newPassword123!"
            }
        },
        {
            "name": "phone with hyphen",
            "data": {
                "user_id": 1,
                "phone_number": "010-1234-5678",  # 하이픈 포함
                "verification_code": "123456",
                "new_password": "newPassword123!"
            }
        }
    ]
    
    url = f"{BASE_URL}/api/auth/reset-password-phone/"
    
    for test_case in test_cases:
        print(f"\n테스트: {test_case['name']}")
        response = requests.post(url, json=test_case['data'])
        print(f"응답: {response.status_code}")
        if response.status_code != 200:
            try:
                print(f"에러: {response.json()}")
            except:
                print(f"에러 텍스트: {response.text[:200]}")

if __name__ == "__main__":
    print("=" * 60)
    print("비밀번호 재설정 API 디버그")
    print("=" * 60)
    
    # 기본 테스트
    test_reset_password()
    
    # 데이터 타입 테스트
    # test_data_types()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)