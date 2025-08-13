#!/usr/bin/env python3
"""
Django Admin API 테스트 스크립트
판매회원 관리 API 엔드포인트 테스트
"""

import requests
import json
from datetime import datetime

# API 기본 정보
BASE_URL = "http://localhost:8000/api"

# 테스트용 관리자 토큰 (실제 사용 시 관리자 로그인 후 받은 토큰으로 교체)
ADMIN_TOKEN = "YOUR_ADMIN_TOKEN_HERE"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}


def test_sellers_with_details():
    """판매회원 목록 조회 (상세 정보 포함)"""
    print("\n=== 판매회원 목록 조회 ===")
    response = requests.get(f"{BASE_URL}/admin/sellers_with_details/", headers=headers)
    
    if response.status_code == 200:
        sellers = response.json()
        print(f"총 {len(sellers)}명의 판매회원 조회됨")
        for seller in sellers[:3]:  # 첫 3명만 출력
            print(f"- ID: {seller['id']}, 닉네임: {seller.get('nickname', 'N/A')}, "
                  f"입찰권: {seller.get('bid_tokens_count', 0)}개, "
                  f"구독권: {'활성' if seller.get('has_subscription') else '없음'}")
    else:
        print(f"오류: {response.status_code} - {response.text}")
    
    return response.json() if response.status_code == 200 else []


def test_seller_detail(seller_id):
    """특정 판매회원 상세 정보 조회"""
    print(f"\n=== 판매회원 상세 조회 (ID: {seller_id}) ===")
    response = requests.get(f"{BASE_URL}/admin/seller_detail/{seller_id}/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        seller = data['seller']
        tokens = data['tokens']
        print(f"회원 정보:")
        print(f"  - 사용자명: {seller['username']}")
        print(f"  - 닉네임: {seller.get('nickname', 'N/A')}")
        print(f"  - 이메일: {seller['email']}")
        print(f"  - 사업자 인증: {'완료' if seller['is_business_verified'] else '미인증'}")
        print(f"입찰권 정보:")
        print(f"  - 입찰권: {tokens['single_tokens_count']}개")
        print(f"  - 구독권: {'활성' if tokens['has_subscription'] else '없음'}")
        if tokens['has_subscription']:
            print(f"  - 만료일: {tokens['subscription_expires_at']}")
        print(f"사용 이력: {len(data['usage_history'])}건")
        print(f"구매 내역: {len(data['purchase_history'])}건")
        print(f"조정 이력: {len(data['adjustment_logs'])}건")
    else:
        print(f"오류: {response.status_code} - {response.text}")
    
    return response.json() if response.status_code == 200 else None


def test_adjust_bid_tokens(seller_id, adjustment_type='add', quantity=5):
    """입찰권 추가/차감 테스트"""
    print(f"\n=== 입찰권 조정 (ID: {seller_id}) ===")
    print(f"조정 유형: {adjustment_type}, 수량: {quantity}개")
    
    data = {
        "adjustment_type": adjustment_type,
        "quantity": quantity,
        "reason": f"테스트 {'추가' if adjustment_type == 'add' else '차감'} - {datetime.now()}"
    }
    
    response = requests.post(
        f"{BASE_URL}/admin/adjust_bid_tokens/{seller_id}/",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"성공: {result['message']}")
        print(f"현재 입찰권 수: {result['current_tokens_count']}개")
    else:
        print(f"오류: {response.status_code} - {response.text}")
    
    return response.json() if response.status_code == 200 else None


def test_grant_subscription(seller_id, duration_days=7):
    """구독권 부여 테스트"""
    print(f"\n=== 구독권 부여 (ID: {seller_id}) ===")
    print(f"기간: {duration_days}일")
    
    data = {
        "duration_days": duration_days,
        "reason": f"테스트 구독권 부여 - {datetime.now()}"
    }
    
    response = requests.post(
        f"{BASE_URL}/admin/grant_subscription/{seller_id}/",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"성공: {result['message']}")
        print(f"만료일: {result['expires_at']}")
    else:
        print(f"오류: {response.status_code} - {response.text}")
    
    return response.json() if response.status_code == 200 else None


def main():
    """메인 테스트 실행"""
    print("=" * 50)
    print("Django Admin API 테스트 시작")
    print("=" * 50)
    
    # 1. 판매회원 목록 조회
    sellers = test_sellers_with_details()
    
    if sellers and len(sellers) > 0:
        # 첫 번째 판매회원으로 테스트
        test_seller_id = sellers[0]['id']
        
        # 2. 상세 정보 조회
        test_seller_detail(test_seller_id)
        
        # 3. 입찰권 추가
        test_adjust_bid_tokens(test_seller_id, 'add', 5)
        
        # 4. 입찰권 차감
        test_adjust_bid_tokens(test_seller_id, 'subtract', 2)
        
        # 5. 구독권 부여
        test_grant_subscription(test_seller_id, 7)
        
        # 6. 변경 후 상세 정보 재조회
        print("\n=== 변경 후 최종 상태 확인 ===")
        test_seller_detail(test_seller_id)
    else:
        print("테스트할 판매회원이 없습니다.")
    
    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)


if __name__ == "__main__":
    print("""
    주의: 이 스크립트를 실행하기 전에:
    1. Django 서버가 실행 중이어야 합니다 (python manage.py runserver)
    2. ADMIN_TOKEN을 실제 관리자 토큰으로 교체하세요
    3. 관리자 토큰은 관리자 계정으로 로그인 후 받을 수 있습니다
    
    관리자 토큰 받는 방법:
    curl -X POST http://localhost:8000/api/auth/login/ \\
         -H "Content-Type: application/json" \\
         -d '{"email": "admin@example.com", "password": "your_password"}'
    """)
    
    # 실제 테스트 실행 시 주석 해제
    # main()