"""
v3.0 테스트 데이터 생성 스크립트
- bidding 상태 없이 recruiting에서 바로 final_selection으로 전환
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import (
    User, Product, GroupBuy, Bid, Participation, 
    Category, Region, GroupBuyRegion
)
from django.db import transaction
import random

class Command(BaseCommand):
    help = 'v3.0 테스트 데이터 생성'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('===================================='))
        self.stdout.write(self.style.WARNING('v3.0 테스트 데이터 생성 시작'))
        self.stdout.write(self.style.WARNING('===================================='))
        
        try:
            with transaction.atomic():
                now = timezone.now()
                
                # 1. 사용자 확인 또는 생성
                buyer, _ = User.objects.get_or_create(
                    username='test_buyer_v3',
                    defaults={
                        'email': 'buyer_v3@test.com',
                        'nickname': '구매자V3',
                        'role': 'buyer',
                        'is_active': True
                    }
                )
                
                seller, _ = User.objects.get_or_create(
                    username='test_seller_v3',
                    defaults={
                        'email': 'seller_v3@test.com',
                        'nickname': '판매자V3',
                        'role': 'seller',
                        'is_active': True,
                        'is_business_verified': True
                    }
                )
                
                # 2. 카테고리와 지역 확인
                category = Category.objects.filter(name='전자제품').first()
                if not category:
                    category = Category.objects.create(
                        name='전자제품',
                        slug='electronics',
                        detail_type='electronics'
                    )
                
                region = Region.objects.filter(name='서울').first()
                if not region:
                    region = Region.objects.create(
                        name='서울',
                        code='11',
                        level=0  # 0: 시/도 레벨
                    )
                
                # 3. 상품 생성
                product = Product.objects.create(
                    name='Galaxy S24 Ultra (v3.0 테스트)',
                    category=category,
                    base_price=1500000,
                    description='v3.0 테스트용 상품'
                )
                
                self.stdout.write(f"✅ 테스트 상품 생성: {product.name}")
                
                # 4. 다양한 상태의 공구 생성
                
                # 4-1. recruiting 상태 (아직 진행중)
                gb_recruiting = GroupBuy.objects.create(
                    title='[v3.0] 모집중 공구 - 입찰 가능',
                    description='v3.0 테스트: recruiting 상태에서 입찰 가능',
                    product=product,
                    creator=buyer,
                    min_participants=2,
                    max_participants=10,
                    start_time=now - timedelta(hours=1),
                    end_time=now + timedelta(hours=2),  # 2시간 후 종료
                    status='recruiting',  # v3.0: bidding 없이 바로 recruiting
                    region_type='local'
                )
                GroupBuyRegion.objects.create(groupbuy=gb_recruiting, region=region)
                
                # 참여자 추가
                Participation.objects.create(
                    user=buyer,
                    groupbuy=gb_recruiting,
                    joined_at=now
                )
                gb_recruiting.current_participants = 1
                gb_recruiting.save()
                
                # 판매자 입찰 추가
                Bid.objects.create(
                    seller=seller,
                    groupbuy=gb_recruiting,
                    amount=50000,
                    status='pending'
                )
                
                self.stdout.write(f"✅ recruiting 공구 생성: {gb_recruiting.title}")
                
                # 4-2. final_selection_buyers 상태
                gb_final_buyers = GroupBuy.objects.create(
                    title='[v3.0] 구매자 최종선택중',
                    description='v3.0 테스트: 구매자 최종선택 진행중',
                    product=product,
                    creator=buyer,
                    min_participants=3,
                    max_participants=10,
                    start_time=now - timedelta(hours=5),
                    end_time=now - timedelta(hours=1),  # 1시간 전 종료
                    final_selection_end=now + timedelta(hours=11),  # 11시간 후 최종선택 종료
                    status='final_selection_buyers',
                    region_type='local'
                )
                GroupBuyRegion.objects.create(groupbuy=gb_final_buyers, region=region)
                
                # 참여자 추가
                for i in range(3):
                    user, _ = User.objects.get_or_create(
                        username=f'buyer_fb_{i}',
                        defaults={
                            'email': f'buyer_fb_{i}@test.com',
                            'nickname': f'구매자FB{i}',
                            'role': 'buyer'
                        }
                    )
                    Participation.objects.create(
                        user=user,
                        groupbuy=gb_final_buyers,
                        joined_at=now - timedelta(hours=2)
                    )
                gb_final_buyers.current_participants = 3
                gb_final_buyers.save()
                
                # 낙찰된 입찰
                winning_bid = Bid.objects.create(
                    seller=seller,
                    groupbuy=gb_final_buyers,
                    amount=70000,
                    status='selected',
                    is_selected=True
                )
                
                self.stdout.write(f"✅ final_selection_buyers 공구 생성: {gb_final_buyers.title}")
                
                # 4-3. final_selection_seller 상태
                gb_final_seller = GroupBuy.objects.create(
                    title='[v3.0] 판매자 최종선택중',
                    description='v3.0 테스트: 판매자 최종선택 진행중',
                    product=product,
                    creator=buyer,
                    min_participants=2,
                    max_participants=5,
                    start_time=now - timedelta(hours=20),
                    end_time=now - timedelta(hours=14),  # 14시간 전 종료
                    final_selection_end=now - timedelta(hours=2),  # 2시간 전 구매자 선택 종료
                    seller_selection_end=now + timedelta(hours=4),  # 4시간 후 판매자 선택 종료
                    status='final_selection_seller',
                    region_type='local'
                )
                GroupBuyRegion.objects.create(groupbuy=gb_final_seller, region=region)
                
                # 구매확정한 참여자들
                for i in range(2):
                    user, _ = User.objects.get_or_create(
                        username=f'buyer_fs_{i}',
                        defaults={
                            'email': f'buyer_fs_{i}@test.com',
                            'nickname': f'구매자FS{i}',
                            'role': 'buyer'
                        }
                    )
                    Participation.objects.create(
                        user=user,
                        groupbuy=gb_final_seller,
                        joined_at=now - timedelta(hours=15),
                        final_decision='confirmed',
                        final_decision_at=now - timedelta(hours=3)
                    )
                gb_final_seller.current_participants = 2
                gb_final_seller.save()
                
                # 낙찰된 입찰
                Bid.objects.create(
                    seller=seller,
                    groupbuy=gb_final_seller,
                    amount=60000,
                    status='selected',
                    is_selected=True
                )
                
                self.stdout.write(f"✅ final_selection_seller 공구 생성: {gb_final_seller.title}")
                
                # 5. 통계 출력
                self.stdout.write("\n📊 생성된 v3.0 테스트 데이터:")
                self.stdout.write(f"  - recruiting 공구: 1개")
                self.stdout.write(f"  - final_selection_buyers 공구: 1개")
                self.stdout.write(f"  - final_selection_seller 공구: 1개")
                self.stdout.write(f"  - 총 입찰: 3개")
                self.stdout.write(f"  - 총 참여: 6명")
                
                self.stdout.write(self.style.SUCCESS('\n✅ v3.0 테스트 데이터 생성 완료!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 테스트 데이터 생성 중 오류: {str(e)}'))
            raise