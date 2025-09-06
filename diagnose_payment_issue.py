#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_payment import Payment
from api.models import User

def diagnose_payment_issues():
    """결제 시스템 문제 진단"""
    print("=== 결제 시스템 진단 시작 ===\n")
    
    # 1. 실패한 order_id들 확인
    failed_order_ids = [
        'BT_1757064601318_109_1757064601318',
        'BT_1757065297608_109_1757065297607'
    ]
    
    print("1. 실패한 order_id 확인:")
    for order_id in failed_order_ids:
        try:
            payment = Payment.objects.get(order_id=order_id)
            print(f"  ✓ {order_id}: 존재함 (상태: {payment.status})")
        except Payment.DoesNotExist:
            print(f"  ✗ {order_id}: 데이터베이스에 없음")
    
    # 2. seller9의 최근 결제 상황
    print(f"\n2. seller9 최근 결제 상황:")
    try:
        seller9 = User.objects.get(username='seller9')
        recent_payments = Payment.objects.filter(user=seller9).order_by('-created_at')[:5]
        
        print(f"  최근 5개 결제:")
        for p in recent_payments:
            print(f"    ID: {p.id}, 주문번호: {p.order_id}, 상태: {p.status}, 생성일: {p.created_at}")
            
    except User.DoesNotExist:
        print("  seller9 사용자를 찾을 수 없습니다.")
    
    # 3. 전체 결제 통계
    print(f"\n3. 전체 결제 통계:")
    print(f"  총 결제 건수: {Payment.objects.count()}")
    print(f"  완료된 결제: {Payment.objects.filter(status='completed').count()}")
    print(f"  대기 중 결제: {Payment.objects.filter(status='pending').count()}")
    print(f"  입금 대기 결제: {Payment.objects.filter(status='waiting_deposit').count()}")
    print(f"  실패한 결제: {Payment.objects.filter(status='failed').count()}")
    
    # 4. 최근 1시간 내 결제 시도
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_attempts = Payment.objects.filter(created_at__gte=one_hour_ago).order_by('-created_at')
    
    print(f"\n4. 최근 1시간 결제 시도 ({recent_attempts.count()}건):")
    for p in recent_attempts:
        print(f"  {p.order_id} - {p.user.username} - {p.status} - {p.created_at}")
    
    # 5. order_id 패턴 분석
    print(f"\n5. 최근 order_id 패턴 분석:")
    recent_all = Payment.objects.order_by('-created_at')[:10]
    for p in recent_all:
        # order_id에서 타임스탬프 추출
        if 'BT_' in p.order_id:
            parts = p.order_id.split('_')
            if len(parts) >= 2:
                timestamp_part = parts[1]
                print(f"  {p.order_id} -> 타임스탬프: {timestamp_part}")

if __name__ == '__main__':
    diagnose_payment_issues()