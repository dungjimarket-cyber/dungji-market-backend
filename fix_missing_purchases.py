#!/usr/bin/env python
"""
누락된 BidTokenPurchase 레코드를 보완하는 스크립트
결제 완료된 Payment 레코드를 기반으로 BidTokenPurchase 레코드를 생성합니다.
"""

import os
import sys
import django

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_payment import Payment
from api.models import BidToken, BidTokenPurchase
from datetime import datetime

def fix_missing_purchases():
    """누락된 BidTokenPurchase 레코드를 생성합니다."""
    
    print("=== 누락된 BidTokenPurchase 레코드 보완 시작 ===\n")
    
    # 결제 완료된 모든 Payment 조회
    completed_payments = Payment.objects.filter(status='completed').order_by('completed_at')
    
    print(f"결제 완료된 Payment 레코드: {completed_payments.count()}개")
    print(f"기존 BidTokenPurchase 레코드: {BidTokenPurchase.objects.count()}개\n")
    
    created_count = 0
    skipped_count = 0
    
    for payment in completed_payments:
        try:
            # 이미 해당 Payment에 대한 BidTokenPurchase가 있는지 확인
            # order_id, 금액, 날짜를 기반으로 중복 체크
            existing_purchase = BidTokenPurchase.objects.filter(
                seller=payment.user,
                total_price=payment.amount,
                payment_date__date=payment.completed_at.date() if payment.completed_at else payment.created_at.date()
            ).first()
            
            if existing_purchase:
                skipped_count += 1
                continue
                
            # 상품명에서 토큰 타입 및 수량 파악
            product_name = payment.product_name or ''
            is_subscription = '구독' in product_name or 'unlimited' in product_name.lower() or '무제한' in product_name
            
            if is_subscription:
                token_type = 'unlimited'
                quantity = 1
            else:
                token_type = 'single'
                # 금액 기준으로 수량 계산 (1,990원 = 1개)
                quantity = int(payment.amount // 1990)
                
            # Order ID 생성 (기존 payment_data에서 가져오거나 새로 생성)
            order_id = None
            if payment.payment_data and 'orderId' in payment.payment_data:
                order_id = payment.payment_data['orderId']
            else:
                order_id = f"LEGACY_PAYMENT_{payment.id}_{int(payment.completed_at.timestamp()) if payment.completed_at else int(payment.created_at.timestamp())}"
            
            # BidTokenPurchase 레코드 생성
            BidTokenPurchase.objects.create(
                seller=payment.user,
                token_type=token_type,
                quantity=quantity,
                total_price=payment.amount,
                payment_status='completed',
                purchase_date=payment.created_at,
                payment_date=payment.completed_at or payment.created_at,
                order_id=order_id,
                payment_key=payment.tid
            )
            
            created_count += 1
            print(f"✅ 생성 완료: Payment ID {payment.id} -> {token_type} {quantity}개 (사용자: {payment.user.username})")
            
        except Exception as e:
            print(f"❌ 오류 발생 (Payment ID {payment.id}): {str(e)}")
            continue
    
    print(f"\n=== 보완 작업 완료 ===")
    print(f"새로 생성된 BidTokenPurchase: {created_count}개")
    print(f"건너뛴 레코드 (이미 존재): {skipped_count}개")
    print(f"전체 BidTokenPurchase 레코드: {BidTokenPurchase.objects.count()}개")

if __name__ == "__main__":
    fix_missing_purchases()