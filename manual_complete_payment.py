#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_payment import Payment
from api.models import BidToken, BidTokenPurchase, User
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

def manually_complete_payment(payment_id):
    """
    pending 상태의 결제를 수동으로 완료 처리하고 토큰 발급
    """
    try:
        with transaction.atomic():
            payment = Payment.objects.get(id=payment_id)
            user = payment.user
            
            print(f"결제 정보:")
            print(f"  ID: {payment.id}")
            print(f"  사용자: {user.username}")
            print(f"  상태: {payment.status}")
            print(f"  금액: {payment.amount}")
            
            if payment.status != 'pending':
                print(f"  오류: 결제 상태가 pending이 아닙니다 ({payment.status})")
                return False
            
            # 결제 완료 처리
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.tid = f"MANUAL_{payment.id}_{int(datetime.now().timestamp())}"
            payment.save()
            
            print(f"  ✓ 결제 완료 처리됨")
            
            # 토큰 발급 로직 (views_inicis.py의 로직 참고)
            amount = int(payment.amount)
            
            # 단품 토큰 (1990원당 1개)
            if amount >= 1990:
                token_count = amount // 1990
                
                for i in range(token_count):
                    BidToken.objects.create(
                        seller=user,
                        token_type='single',
                        status='active'
                    )
                
                print(f"  ✓ {token_count}개의 단품 토큰 발급됨")
                
                # BidTokenPurchase 기록 생성
                BidTokenPurchase.objects.create(
                    seller=user,
                    token_type='single',
                    quantity=token_count,
                    total_price=amount,
                    payment_status='completed',
                    payment_date=timezone.now(),
                    order_id=payment.order_id
                )
                
                print(f"  ✓ BidTokenPurchase 기록 생성됨")
            
            # 현재 토큰 수 확인
            current_tokens = BidToken.objects.filter(
                seller=user,
                token_type='single',
                status='active'
            ).count()
            
            print(f"  ✓ 현재 활성 토큰 수: {current_tokens}개")
            
            return True
            
    except Payment.DoesNotExist:
        print(f"결제 ID {payment_id}를 찾을 수 없습니다.")
        return False
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return False

if __name__ == '__main__':
    # seller9의 최근 pending 결제 완료 처리
    payment_id = 159  # 가장 최근 pending 결제
    print(f"=== 결제 ID {payment_id} 수동 완료 처리 ===")
    success = manually_complete_payment(payment_id)
    
    if success:
        print("\n=== 처리 후 상태 확인 ===")
        payment = Payment.objects.get(id=payment_id)
        user = payment.user
        
        tokens = BidToken.objects.filter(
            seller=user,
            token_type='single',
            status='active'
        ).count()
        
        print(f"seller9의 현재 활성 토큰 수: {tokens}개")
    else:
        print("결제 처리에 실패했습니다.")