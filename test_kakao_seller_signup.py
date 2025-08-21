#!/usr/bin/env python
"""
카카오 판매회원 가입 테스트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
django.setup()

from django.contrib.auth import get_user_model
from api.views_social import get_kakao_auth_url
import json
from urllib.parse import unquote

User = get_user_model()

def test_kakao_seller_signup():
    """카카오 판매회원 가입 URL 생성 테스트"""
    
    print("=== 카카오 판매회원 가입 URL 테스트 ===\n")
    
    # 1. 일반 회원 가입 URL
    print("1. 일반회원 가입 URL:")
    buyer_url = get_kakao_auth_url(
        next_url='https://dungjimarket.com/signup/complete',
        redirect_uri='https://dungjimarket.com/api/auth/callback/kakao',
        role='buyer'
    )
    print(f"URL: {buyer_url}\n")
    
    # state 파라미터 확인
    buyer_state = buyer_url.split('state=')[1].split('&')[0] if 'state=' in buyer_url else ''
    if buyer_state:
        decoded_state = json.loads(unquote(buyer_state))
        print(f"State 데이터: {decoded_state}")
        print(f"- next_url: {decoded_state.get('next_url')}")
        print(f"- role: {decoded_state.get('role')}\n")
    
    # 2. 판매회원 가입 URL
    print("2. 판매회원 가입 URL:")
    seller_url = get_kakao_auth_url(
        next_url='https://dungjimarket.com/signup/complete',
        redirect_uri='https://dungjimarket.com/api/auth/callback/kakao',
        role='seller'
    )
    print(f"URL: {seller_url}\n")
    
    # state 파라미터 확인
    seller_state = seller_url.split('state=')[1].split('&')[0] if 'state=' in seller_url else ''
    if seller_state:
        decoded_state = json.loads(unquote(seller_state))
        print(f"State 데이터: {decoded_state}")
        print(f"- next_url: {decoded_state.get('next_url')}")
        print(f"- role: {decoded_state.get('role')}\n")
    
    # 3. 기존 사용자 확인
    print("3. 기존 카카오 사용자 확인:")
    kakao_users = User.objects.filter(sns_type='kakao')
    for user in kakao_users[:5]:  # 최대 5명만 표시
        print(f"- {user.username} (role: {user.role}, email: {user.email})")
    
    if kakao_users.count() > 5:
        print(f"  ... 외 {kakao_users.count() - 5}명")
    
    print(f"\n총 카카오 사용자 수: {kakao_users.count()}명")
    print(f"- 구매자: {kakao_users.filter(role='buyer').count()}명")
    print(f"- 판매자: {kakao_users.filter(role='seller').count()}명")
    
    print("\n=== 테스트 완료 ===")

if __name__ == '__main__':
    test_kakao_seller_signup()