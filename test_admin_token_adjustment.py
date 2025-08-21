#!/usr/bin/env python
"""
Django Admin 토큰 조정 API 테스트
"""
import os
import sys
import django
import requests
import json

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from api.models import BidToken

User = get_user_model()

def test_token_adjustment():
    """토큰 조정 API 테스트"""
    
    # 테스트 클라이언트 생성
    client = Client()
    
    # 관리자 계정으로 로그인
    admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
    if not admin_user:
        print("관리자 계정이 없습니다. 생성 중...")
        admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='admin123'
        )
    
    # 로그인
    client.force_login(admin_user)
    print(f"관리자로 로그인: {admin_user.username}")
    
    # 테스트용 판매자 계정 가져오기
    seller = User.objects.filter(role='seller').first()
    if not seller:
        print("판매자 계정이 없습니다.")
        return
    
    print(f"테스트 판매자: {seller.username} (ID: {seller.id})")
    
    # 현재 토큰 수 확인
    current_tokens = BidToken.objects.filter(
        seller=seller,
        status='active',
        token_type='single'
    ).count()
    print(f"현재 활성 토큰 수: {current_tokens}개")
    
    # API 엔드포인트
    url = f'/api/admin/user/{seller.id}/adjust-tokens/'
    
    # 토큰 추가 테스트
    print("\n=== 토큰 추가 테스트 ===")
    response = client.post(
        url,
        data=json.dumps({
            'adjustment_type': 'add',
            'quantity': 5,
            'reason': '테스트 추가'
        }),
        content_type='application/json',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"응답 상태: {response.status_code}")
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"응답 데이터: {data}")
    else:
        print(f"응답 내용: {response.content.decode()}")
    
    # 업데이트된 토큰 수 확인
    updated_tokens = BidToken.objects.filter(
        seller=seller,
        status='active',
        token_type='single'
    ).count()
    print(f"업데이트된 토큰 수: {updated_tokens}개")
    
    # 토큰 차감 테스트
    print("\n=== 토큰 차감 테스트 ===")
    response = client.post(
        url,
        data=json.dumps({
            'adjustment_type': 'subtract',
            'quantity': 2,
            'reason': '테스트 차감'
        }),
        content_type='application/json',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    print(f"응답 상태: {response.status_code}")
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"응답 데이터: {data}")
    else:
        print(f"응답 내용: {response.content.decode()}")
    
    # 최종 토큰 수 확인
    final_tokens = BidToken.objects.filter(
        seller=seller,
        status='active',
        token_type='single'
    ).count()
    print(f"최종 토큰 수: {final_tokens}개")
    
    print("\n=== 테스트 완료 ===")

if __name__ == '__main__':
    test_token_adjustment()