from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import User, Product, Category, GroupBuy, Participation, Bid, BidToken
from django.db import transaction
import random


class Command(BaseCommand):
    help = '투표 테스트를 위한 데이터 설정'

    def handle(self, *args, **options):
        with transaction.atomic():
            # 1. 테스트 사용자 생성
            users = []
            for i in range(5):
                user, created = User.objects.get_or_create(
                    username=f'testuser{i+1}',
                    defaults={
                        'email': f'testuser{i+1}@test.com',
                        'role': 'buyer',
                        'phone_number': f'010-1234-{5000+i}'
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                users.append(user)
                self.stdout.write(f"사용자 생성/확인: {user.username}")
            
            # 2. 테스트 판매자 생성
            sellers = []
            for i in range(3):
                seller, created = User.objects.get_or_create(
                    username=f'testseller{i+1}',
                    defaults={
                        'email': f'testseller{i+1}@test.com',
                        'role': 'seller',
                        'phone_number': f'010-9876-{5000+i}',
                        'business_reg_number': f'123-45-{67890+i}'
                    }
                )
                if created:
                    seller.set_password('password123')
                    seller.save()
                
                # 판매자에게 입찰권 부여
                for _ in range(5):
                    BidToken.objects.create(
                        seller=seller,
                        token_type='single'
                    )
                
                sellers.append(seller)
                self.stdout.write(f"판매자 생성/확인: {seller.username}")
            
            # 3. 카테고리 확인 및 상품 생성
            category = Category.objects.get(id=1)  # 휴대폰 카테고리
            product, created = Product.objects.get_or_create(
                name='갤럭시 S24 Ultra',
                defaults={
                    'category': category,
                    'description': '최신 플래그십 스마트폰',
                    'base_price': 1500000,
                    'product_type': 'device'
                }
            )
            self.stdout.write(f"상품 생성/확인: {product.name}")
            
            # 4. 공구 생성 (종료 시간이 지난 상태)
            groupbuy = GroupBuy.objects.create(
                title='[서울] 갤럭시 S24 Ultra 공동구매',
                description='갤럭시 S24 Ultra를 함께 구매해요!',
                product=product,
                creator=users[0],
                creator_nickname='참새1',
                min_participants=3,
                max_participants=10,
                start_time=timezone.now() - timedelta(days=2),
                end_time=timezone.now() - timedelta(hours=1),  # 1시간 전에 종료
                voting_end=timezone.now() + timedelta(hours=11),  # 11시간 후 투표 종료
                status='voting',  # 투표 상태로 설정
                current_participants=5
            )
            self.stdout.write(f"공구 생성: {groupbuy.title} (상태: {groupbuy.status})")
            
            # 5. 참여자 추가
            for user in users:
                Participation.objects.create(
                    user=user,
                    groupbuy=groupbuy,
                    nickname=user.username
                )
                self.stdout.write(f"참여자 추가: {user.username}")
            
            # 6. 판매자 입찰 추가
            bid_amounts = [1350000, 1380000, 1400000]  # 서로 다른 입찰 금액
            for i, seller in enumerate(sellers):
                bid = Bid.objects.create(
                    seller=seller,
                    groupbuy=groupbuy,
                    bid_type='price',
                    amount=bid_amounts[i],
                    message=f'{seller.username}의 특별 할인 제안입니다!'
                )
                self.stdout.write(f"입찰 추가: {seller.username} - {bid.amount:,}원")
            
            self.stdout.write(self.style.SUCCESS(f"""
투표 테스트 데이터 설정 완료!

공구 정보:
- ID: {groupbuy.id}
- 제목: {groupbuy.title}
- 상태: {groupbuy.status}
- 투표 종료 시간: {groupbuy.voting_end}
- 참여자: {', '.join([u.username for u in users])}
- 입찰 판매자: {', '.join([s.username for s in sellers])}

테스트 방법:
1. 참여자 계정으로 로그인 (testuser1~5, 비밀번호: password123)
2. 공구 상세 페이지 접속: /groupbuys/{groupbuy.id}
3. 원하는 판매자의 입찰 선택 후 투표
4. 다른 참여자 계정으로도 투표 진행
5. 투표 결과 확인

주의: 실제 운영 환경에서는 cron job이나 celery beat로 상태 자동 전환을 처리해야 합니다.
"""))