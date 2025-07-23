#!/usr/bin/env python
"""
투표 시스템 테스트 스크립트
이 스크립트는 투표 시나리오를 시뮬레이션합니다.
"""

import os
import sys
import django

# Django 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import User, GroupBuy, Bid, BidVote, Participation
from django.utils import timezone
from datetime import timedelta


def test_voting_flow():
    print("=" * 60)
    print("투표 시스템 테스트 시작")
    print("=" * 60)
    
    # 1. 테스트 데이터 확인
    groupbuy = GroupBuy.objects.filter(title__contains='갤럭시 S24 Ultra 공동구매').last()
    if not groupbuy:
        print("❌ 테스트 공구를 찾을 수 없습니다. setup_voting_test 명령을 먼저 실행하세요.")
        return
    
    print(f"\n✅ 공구 정보:")
    print(f"   - ID: {groupbuy.id}")
    print(f"   - 제목: {groupbuy.title}")
    print(f"   - 상태: {groupbuy.status}")
    print(f"   - 투표 종료: {groupbuy.voting_end}")
    
    # 2. 참여자 정보
    participants = Participation.objects.filter(groupbuy=groupbuy)
    print(f"\n✅ 참여자 ({participants.count()}명):")
    for p in participants:
        print(f"   - {p.user.username}")
    
    # 3. 입찰 정보
    bids = Bid.objects.filter(groupbuy=groupbuy).order_by('amount')
    print(f"\n✅ 입찰 내역 ({bids.count()}건):")
    for bid in bids:
        print(f"   - {bid.seller.username}: {bid.amount:,}원")
    
    # 4. 투표 시뮬레이션
    print("\n📊 투표 시뮬레이션 시작...")
    
    # testuser1, testuser2는 최저가(testseller1)에 투표
    # testuser3, testuser4, testuser5는 중간가(testseller2)에 투표
    votes_data = [
        ('testuser1', 'testseller1'),
        ('testuser2', 'testseller1'),
        ('testuser3', 'testseller2'),
        ('testuser4', 'testseller2'),
        ('testuser5', 'testseller2'),
    ]
    
    for username, seller_username in votes_data:
        user = User.objects.get(username=username)
        bid = Bid.objects.get(groupbuy=groupbuy, seller__username=seller_username)
        
        # 기존 투표 확인
        if BidVote.objects.filter(participant=user, groupbuy=groupbuy).exists():
            print(f"   ⚠️  {username}는 이미 투표했습니다.")
            continue
        
        # 투표 생성
        vote = BidVote.objects.create(
            participant=user,
            groupbuy=groupbuy,
            bid=bid
        )
        print(f"   ✅ {username} → {seller_username} ({bid.amount:,}원)에 투표")
    
    # 5. 투표 결과 집계
    print("\n📊 투표 결과:")
    for bid in bids:
        vote_count = BidVote.objects.filter(bid=bid).count()
        print(f"   - {bid.seller.username}: {vote_count}표 ({bid.amount:,}원)")
    
    # 6. 투표 종료 시뮬레이션 (실제로는 자동화된 프로세스)
    print("\n🏁 투표 종료 시뮬레이션...")
    
    # 가장 많은 표를 받은 입찰 찾기
    winning_bid = None
    max_votes = 0
    
    for bid in bids:
        vote_count = BidVote.objects.filter(bid=bid).count()
        if vote_count > max_votes:
            max_votes = vote_count
            winning_bid = bid
    
    if winning_bid:
        # 낙찰 처리
        winning_bid.is_selected = True
        winning_bid.save()
        
        # 공구 상태 변경
        groupbuy.status = 'seller_confirmation'
        groupbuy.save()
        
        print(f"\n🎉 낙찰 결과:")
        print(f"   - 낙찰자: {winning_bid.seller.username}")
        print(f"   - 낙찰가: {winning_bid.amount:,}원")
        print(f"   - 득표수: {max_votes}표")
        print(f"   - 공구 상태: {groupbuy.status}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_voting_flow()