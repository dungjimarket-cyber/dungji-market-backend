#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import GroupBuy, Bid, Participation

# 공구 168번 확인
try:
    gb = GroupBuy.objects.get(id=168)
    print(f'GroupBuy {gb.id}:')
    print(f'  - status: {gb.status}')
    print(f'  - title: {gb.title}')
    print(f'  - current_participants: {gb.current_participants}')
    
    # 선택된 입찰 확인
    selected_bids = Bid.objects.filter(groupbuy=gb, status='selected')
    print(f'\nSelected bids: {selected_bids.count()}')
    for bid in selected_bids:
        print(f'  - Bid {bid.id}:')
        print(f'    - seller: {bid.seller.username}')
        print(f'    - final_decision: {bid.final_decision}')
        print(f'    - amount: {bid.amount}')
    
    # 참여자 최종선택 상태 확인
    participations = Participation.objects.filter(groupbuy=gb)
    print(f'\nParticipations: {participations.count()}')
    for p in participations:
        print(f'  - User {p.user.username}: final_decision={p.final_decision}')
        
except GroupBuy.DoesNotExist:
    print("GroupBuy 168 not found")