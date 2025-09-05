#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_payment import Payment
from api.models import BidToken

def check_recent_payments():
    print("=== 최근 결제 10건 ===")
    payments = Payment.objects.order_by('-created_at')[:10]
    for p in payments:
        print(f"ID: {p.id}, 주문번호: {p.order_id}, 사용자: {p.user.username}, 상태: {p.status}, 금액: {p.amount}, 생성일: {p.created_at}")
    
    print("\n=== 최근 BidToken 10건 ===")
    tokens = BidToken.objects.order_by('-created_at')[:10]
    for t in tokens:
        print(f"ID: {t.id}, 판매자: {t.seller.username}, 타입: {t.token_type}, 상태: {t.status}, 생성일: {t.created_at}")
    
    print(f"\n=== 전체 통계 ===")
    print(f"총 결제 건수: {Payment.objects.count()}")
    print(f"완료된 결제: {Payment.objects.filter(status='completed').count()}")
    print(f"대기 중 결제: {Payment.objects.filter(status='pending').count()}")
    print(f"실패한 결제: {Payment.objects.filter(status='failed').count()}")
    print(f"총 토큰 수: {BidToken.objects.count()}")
    print(f"활성 토큰 수: {BidToken.objects.filter(status='active').count()}")

if __name__ == '__main__':
    check_recent_payments()