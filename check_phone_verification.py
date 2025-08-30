#!/usr/bin/env python
"""
PhoneVerification 테이블 상태 확인 스크립트
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_verification import PhoneVerification
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

def check_verifications():
    """최근 인증 요청 확인"""
    print("\n=== 최근 30분 이내 인증 요청 ===")
    
    recent_time = timezone.now() - timedelta(minutes=30)
    verifications = PhoneVerification.objects.filter(
        created_at__gte=recent_time
    ).order_by('-created_at')
    
    print(f"총 {verifications.count()}개 발견\n")
    
    for v in verifications:
        print(f"ID: {v.id}")
        print(f"  전화번호: {v.phone_number}")
        print(f"  인증코드: {v.code}")
        print(f"  상태: {v.status}")
        print(f"  is_verified: {v.is_verified}")
        print(f"  purpose: {v.purpose}")
        print(f"  생성시간: {v.created_at}")
        print(f"  만료까지: {(v.created_at + timedelta(minutes=30) - timezone.now()).total_seconds() / 60:.1f}분")
        print("-" * 40)

def check_user_phone(username):
    """특정 사용자의 전화번호 확인"""
    print(f"\n=== 사용자 '{username}' 정보 ===")
    
    try:
        user = User.objects.get(username=username)
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Phone: {user.phone_number}")
        print(f"Phone Verified: {getattr(user, 'phone_verified', 'N/A')}")
        
        # 해당 전화번호의 최근 인증 확인
        if user.phone_number:
            recent_verifications = PhoneVerification.objects.filter(
                phone_number=user.phone_number.replace('-', '').replace(' ', ''),
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).order_by('-created_at')[:5]
            
            if recent_verifications:
                print(f"\n최근 인증 요청:")
                for v in recent_verifications:
                    print(f"  - {v.created_at}: code={v.code}, status={v.status}")
    except User.DoesNotExist:
        print(f"사용자 '{username}'를 찾을 수 없습니다.")

def test_verification_logic(phone_number, code):
    """인증 로직 테스트"""
    print(f"\n=== 인증 로직 테스트 ===")
    print(f"전화번호: {phone_number}")
    print(f"인증코드: {code}")
    
    # 정규화
    phone_normalized = phone_number.replace('-', '').replace(' ', '')
    
    # pending 상태 조회
    verification = PhoneVerification.objects.filter(
        phone_number=phone_normalized,
        code=code,
        status='pending',
        created_at__gte=timezone.now() - timedelta(minutes=30)
    ).first()
    
    if verification:
        print("✅ pending 상태 인증 발견!")
        print(f"  ID: {verification.id}")
        print(f"  생성시간: {verification.created_at}")
    else:
        print("❌ pending 상태 인증을 찾을 수 없음")
        
        # 다른 상태 확인
        all_verifications = PhoneVerification.objects.filter(
            phone_number=phone_normalized,
            created_at__gte=timezone.now() - timedelta(minutes=30)
        )
        
        for v in all_verifications:
            print(f"  존재하는 인증: code={v.code}, status={v.status}, is_verified={v.is_verified}")

if __name__ == "__main__":
    print("=" * 60)
    print("PhoneVerification 상태 확인")
    print("=" * 60)
    
    # 최근 인증 확인
    check_verifications()
    
    # 특정 사용자 확인 (필요시 username 변경)
    # check_user_phone("testuser")
    
    # 인증 로직 테스트 (실제 값으로 변경)
    # test_verification_logic("010-1234-5678", "123456")
    
    print("\n" + "=" * 60)
    print("확인 완료")
    print("=" * 60)