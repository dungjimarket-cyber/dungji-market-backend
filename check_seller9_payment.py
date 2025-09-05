#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_payment import Payment
from api.models import BidToken, User

def check_seller9_payment():
    try:
        seller9 = User.objects.get(username='seller9')
        print(f"=== seller9 (ID: {seller9.id}) 결제 상황 ===")
        
        # 최근 결제 기록
        recent_payment = Payment.objects.filter(user=seller9).order_by('-created_at').first()
        if recent_payment:
            print(f"\n최근 결제:")
            print(f"  ID: {recent_payment.id}")
            print(f"  주문번호: {recent_payment.order_id}")
            print(f"  상태: {recent_payment.status}")
            print(f"  금액: {recent_payment.amount}")
            print(f"  생성일: {recent_payment.created_at}")
            print(f"  완료일: {recent_payment.completed_at}")
            print(f"  TID: {recent_payment.tid}")
            print(f"  결제 데이터: {recent_payment.payment_data}")
        
        # seller9의 토큰 현황
        single_tokens = BidToken.objects.filter(
            seller=seller9,
            token_type='single',
            status='active'
        ).count()
        
        subscription_tokens = BidToken.objects.filter(
            seller=seller9,
            token_type='unlimited',
            status='active'
        ).count()
        
        print(f"\n토큰 현황:")
        print(f"  단품 토큰: {single_tokens}개")
        print(f"  구독 토큰: {subscription_tokens}개")
        
        # 완료된 결제 대비 토큰 수
        completed_payments = Payment.objects.filter(
            user=seller9,
            status='completed'
        ).count()
        
        print(f"\n결제 통계:")
        print(f"  완료된 결제: {completed_payments}건")
        print(f"  대기 중 결제: {Payment.objects.filter(user=seller9, status='pending').count()}건")
        
    except User.DoesNotExist:
        print("seller9 사용자를 찾을 수 없습니다.")

if __name__ == '__main__':
    check_seller9_payment()