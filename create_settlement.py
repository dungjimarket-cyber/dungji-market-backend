#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import GroupBuy, Bid, Settlement
from django.utils import timezone

# 공구 168번에 대한 Settlement 생성
try:
    # 입찰 정보 확인
    bid = Bid.objects.get(
        groupbuy_id=168,
        status='selected',
        final_decision='confirmed'
    )
    
    print(f"Found bid: {bid.id} by seller {bid.seller.username}")
    
    # Settlement이 이미 있는지 확인
    existing_settlement = Settlement.objects.filter(bid=bid).first()
    if existing_settlement:
        print(f"Settlement already exists: {existing_settlement.id} with status {existing_settlement.payment_status}")
    else:
        # Settlement 생성
        settlement = Settlement.objects.create(
            seller=bid.seller,
            groupbuy=bid.groupbuy,
            bid=bid,
            total_amount=bid.amount * bid.groupbuy.current_participants,
            fee_amount=0,
            net_amount=bid.amount * bid.groupbuy.current_participants,
            settlement_date=timezone.now(),
            payment_status='pending'  # 아직 거래 완료되지 않음
        )
        print(f"Created settlement: {settlement.id}")
        
except Bid.DoesNotExist:
    print("No selected bid found for GroupBuy 168")
except Exception as e:
    print(f"Error: {e}")