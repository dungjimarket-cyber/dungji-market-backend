from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from api.models import GroupBuy, Product, Category, Participation, Bid

User = get_user_model()


class BiddingStatusTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # 테스트 사용자 생성
        self.buyer1 = User.objects.create_user(
            username='buyer1',
            email='buyer1@test.com',
            password='testpass',
            role='buyer'
        )
        self.buyer2 = User.objects.create_user(
            username='buyer2',
            email='buyer2@test.com',
            password='testpass',
            role='buyer'
        )
        self.seller1 = User.objects.create_user(
            username='seller1',
            email='seller1@test.com',
            password='testpass',
            role='seller'
        )
        
        # 테스트 상품 및 공구 생성
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            base_price=100000
        )

    def test_status_transition_recruiting_to_bidding(self):
        """시작 시간이 되면 recruiting에서 bidding으로 상태 전환"""
        from api.utils import update_groupbuys_status
        
        # recruiting 상태의 공구 생성 (시작 시간이 과거)
        groupbuy = GroupBuy.objects.create(
            title='Test GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now() - timedelta(minutes=1),  # 시작 시간이 1분 전
            end_time=timezone.now() + timedelta(hours=24),
            status='recruiting'
        )
        
        # 초기 상태 확인
        self.assertEqual(groupbuy.status, 'recruiting')
        
        # 상태 업데이트 실행
        update_groupbuys_status([groupbuy])
        
        # status가 bidding으로 변경되었는지 확인
        groupbuy.refresh_from_db()
        self.assertEqual(groupbuy.status, 'bidding')

    def test_can_join_during_bidding(self):
        """bidding 상태에서도 참여 가능"""
        # bidding 상태의 공구 생성
        groupbuy = GroupBuy.objects.create(
            title='Bidding GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=24),
            status='bidding',
            current_participants=1
        )
        
        # 생성자 참여
        Participation.objects.create(
            user=self.buyer1,
            groupbuy=groupbuy,
            is_leader=True
        )
        
        # 다른 사용자가 참여 시도
        self.client.force_authenticate(user=self.buyer2)
        
        response = self.client.post(f'/api/groupbuys/{groupbuy.id}/join/')
        
        # 참여 성공해야 함
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 참여자 수 확인
        groupbuy.refresh_from_db()
        self.assertEqual(groupbuy.current_participants, 2)

    def test_bidding_to_final_selection_transition(self):
        """공구 마감 시 bidding에서 final_selection으로 전환"""
        from django.core.management import call_command
        
        # 마감된 bidding 상태의 공구 생성
        groupbuy = GroupBuy.objects.create(
            title='Expired Bidding GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(minutes=1),  # 1분 전 마감
            status='bidding',
            current_participants=1
        )
        
        # 입찰 생성
        Bid.objects.create(
            groupbuy=groupbuy,
            seller=self.seller1,
            amount=95000
        )
        
        # cron job 실행
        call_command('update_groupbuy_status')
        
        # final_selection_buyers 상태로 변경되었는지 확인
        groupbuy.refresh_from_db()
        self.assertEqual(groupbuy.status, 'final_selection_buyers')
        self.assertIsNotNone(groupbuy.final_selection_end)

    def test_cannot_join_after_deadline(self):
        """공구 마감 후에는 참여 불가"""
        # 마감된 공구 생성
        groupbuy = GroupBuy.objects.create(
            title='Expired GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(minutes=1),  # 1분 전 마감
            status='bidding'
        )
        
        self.client.force_authenticate(user=self.buyer2)
        
        response = self.client.post(f'/api/groupbuys/{groupbuy.id}/join/')
        
        # 참여 실패해야 함
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('참여할 수 없는', response.data['error'])

    def test_mypage_joined_groupbuys_includes_bidding(self):
        """마이페이지 참여중인 공구에 bidding 상태 포함"""
        # 각 공구마다 다른 제품 생성
        product2 = Product.objects.create(
            name='Test Product 2',
            category=self.category,
            base_price=100000
        )
        product3 = Product.objects.create(
            name='Test Product 3',
            category=self.category,
            base_price=100000
        )
        
        # recruiting 상태 공구
        recruiting_groupbuy = GroupBuy.objects.create(
            title='Recruiting GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=24),
            status='recruiting'
        )
        
        # bidding 상태 공구
        bidding_groupbuy = GroupBuy.objects.create(
            title='Bidding GroupBuy',
            description='Test Description',
            product=product2,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=24),
            status='bidding'
        )
        
        # final_selection 상태 공구 (포함되지 않아야 함)
        final_selection_groupbuy = GroupBuy.objects.create(
            title='Final Selection GroupBuy',
            description='Test Description',
            product=product3,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(hours=1),
            final_selection_end=timezone.now() + timedelta(hours=11),
            status='final_selection_buyers'
        )
        
        # buyer2가 모든 공구에 참여
        for groupbuy in [recruiting_groupbuy, bidding_groupbuy, final_selection_groupbuy]:
            Participation.objects.create(
                user=self.buyer2,
                groupbuy=groupbuy,
                is_leader=False
            )
        
        self.client.force_authenticate(user=self.buyer2)
        
        response = self.client.get('/api/groupbuys/joined_groupbuys/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # recruiting과 bidding 상태만 포함되어야 함
        returned_ids = [gb['id'] for gb in response.data]
        self.assertIn(recruiting_groupbuy.id, returned_ids)
        self.assertIn(bidding_groupbuy.id, returned_ids)
        self.assertNotIn(final_selection_groupbuy.id, returned_ids)
        self.assertEqual(len(response.data), 2)

    def test_status_display_consistency(self):
        """상태 표시의 일관성 확인"""
        # 다양한 상태의 공구 생성 (새로운 상태값 사용)
        products = []
        for i in range(5):
            products.append(Product.objects.create(
                name=f'Product {i}',
                category=self.category,
                base_price=100000
            ))
        
        # recruiting 상태 공구 (미래 시작)
        recruiting_gb = GroupBuy.objects.create(
            title='GroupBuy recruiting',
            description='Test Description',
            product=products[0],
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=25),
            status='recruiting'
        )
        
        # bidding 상태 공구 (진행중)
        bidding_gb = GroupBuy.objects.create(
            title='GroupBuy bidding',
            description='Test Description',
            product=products[1],
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=23),
            status='bidding'
        )
        
        # final_selection_buyers 상태 공구
        buyers_gb = GroupBuy.objects.create(
            title='GroupBuy buyers',
            description='Test Description',
            product=products[2],
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(hours=1),
            final_selection_end=timezone.now() + timedelta(hours=11),
            status='final_selection_buyers'
        )
        # 입찰 추가
        Bid.objects.create(groupbuy=buyers_gb, seller=self.seller1, amount=90000, status='selected')
        
        # final_selection_seller 상태 공구
        seller_gb = GroupBuy.objects.create(
            title='GroupBuy seller',
            description='Test Description',
            product=products[3],
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=26),
            end_time=timezone.now() - timedelta(hours=2),
            final_selection_end=timezone.now() - timedelta(hours=1),
            seller_selection_end=timezone.now() + timedelta(hours=5),
            status='final_selection_seller'
        )
        # 입찰과 참여자 추가
        Bid.objects.create(groupbuy=seller_gb, seller=self.seller1, amount=90000, status='selected')
        Participation.objects.create(user=self.buyer1, groupbuy=seller_gb, final_decision='confirmed')
        
        # completed 상태 공구
        completed_gb = GroupBuy.objects.create(
            title='GroupBuy completed',
            description='Test Description',
            product=products[4],
            creator=self.buyer1,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=48),
            end_time=timezone.now() - timedelta(hours=24),
            status='completed'
        )
        
        self.client.force_authenticate(user=self.buyer1)
        
        # 전체 공구 목록 조회
        response = self.client.get('/api/groupbuys/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 각 상태가 올바르게 반환되는지 확인
        returned_statuses = [gb['status'] for gb in response.data]
        expected_statuses = ['recruiting', 'bidding', 'final_selection_buyers', 'final_selection_seller', 'completed']
        for status_name in expected_statuses:
            self.assertIn(status_name, returned_statuses)