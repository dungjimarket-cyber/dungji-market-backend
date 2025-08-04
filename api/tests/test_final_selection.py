from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from api.models import GroupBuy, Product, Category, Participation, Bid
# BidVote 모델은 voting 제거로 삭제됨

User = get_user_model()


class FinalSelectionTestCase(TestCase):
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
        self.seller2 = User.objects.create_user(
            username='seller2',
            email='seller2@test.com',
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
        
        # 공구 생성 (final_selection_buyers 상태)
        self.groupbuy = GroupBuy.objects.create(
            title='Test GroupBuy',
            description='Test Description',
            product=self.product,
            creator=self.buyer1,
            min_participants=2,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(hours=1),
            final_selection_end=timezone.now() + timedelta(hours=11),
            status='final_selection_buyers'
        )
        
        # 참여자 생성
        self.participation1 = Participation.objects.create(
            user=self.buyer1,
            groupbuy=self.groupbuy,
            is_leader=True
        )
        self.participation2 = Participation.objects.create(
            user=self.buyer2,
            groupbuy=self.groupbuy,
            is_leader=False
        )
        
        # 입찰 및 낙찰자 생성
        self.bid1 = Bid.objects.create(
            groupbuy=self.groupbuy,
            seller=self.seller1,
            amount=95000,
            status='selected'  # is_selected 대신 status='selected' 사용
        )
        self.bid2 = Bid.objects.create(
            groupbuy=self.groupbuy,
            seller=self.seller2,
            amount=98000,
            status='pending'
        )
        
        # 현재 참여자 수 업데이트
        self.groupbuy.current_participants = 2
        self.groupbuy.save()

    def test_buyer_final_decision_confirmed(self):
        """구매자 구매확정 테스트"""
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # DB 확인
        self.participation1.refresh_from_db()
        self.assertEqual(self.participation1.final_decision, 'confirmed')
        self.assertIsNotNone(self.participation1.final_decision_at)

    def test_buyer_final_decision_cancelled(self):
        """구매자 구매포기 테스트"""
        self.client.force_authenticate(user=self.buyer2)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'cancelled'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # DB 확인
        self.participation2.refresh_from_db()
        self.assertEqual(self.participation2.final_decision, 'cancelled')

    def test_seller_final_decision_confirmed(self):
        """판매자 판매확정 테스트"""
        # 구매자들이 모두 확정한 후 판매자 단계로 전환
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        self.participation2.final_decision = 'confirmed'
        self.participation2.save()
        
        self.groupbuy.status = 'final_selection_seller'
        self.groupbuy.seller_selection_end = timezone.now() + timedelta(hours=5)
        self.groupbuy.save()
        
        self.client.force_authenticate(user=self.seller1)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/seller-decision/',
            {'decision': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # DB 확인
        self.bid1.refresh_from_db()
        self.assertEqual(self.bid1.final_decision, 'confirmed')

    def test_seller_final_decision_cancelled_penalty(self):
        """판매자 판매포기 시 패널티 테스트"""
        # 구매자들이 모두 확정한 후 판매자 단계로 전환
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        self.participation2.final_decision = 'confirmed'
        self.participation2.save()
        
        self.groupbuy.status = 'final_selection_seller'
        self.groupbuy.seller_selection_end = timezone.now() + timedelta(hours=5)
        self.groupbuy.save()
        
        self.client.force_authenticate(user=self.seller1)
        
        initial_penalty = self.seller1.penalty_count
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/seller-decision/',
            {'decision': 'cancelled'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 패널티 확인
        self.seller1.refresh_from_db()
        self.assertEqual(self.seller1.penalty_count, initial_penalty + 1)

    def test_final_selection_expired(self):
        """최종선택 시간 만료 테스트"""
        # 최종선택 시간을 과거로 설정
        self.groupbuy.final_selection_end = timezone.now() - timedelta(minutes=1)
        self.groupbuy.save()
        
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('기간이 종료', response.data['error'])

    def test_duplicate_final_decision(self):
        """중복 최종선택 방지 테스트"""
        # 먼저 결정
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'cancelled'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('이미', response.data['error'])

    def test_non_participant_cannot_decide(self):
        """참여하지 않은 사용자는 최종선택 불가"""
        non_participant = User.objects.create_user(
            username='non_participant',
            email='non@test.com',
            password='testpass',
            role='buyer'
        )
        
        self.client.force_authenticate(user=non_participant)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_winning_seller_cannot_decide(self):
        """낙찰되지 않은 판매자는 최종선택 불가"""
        # 구매자들이 모두 확정한 후 판매자 단계로 전환
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        self.participation2.final_decision = 'confirmed'
        self.participation2.save()
        
        self.groupbuy.status = 'final_selection_seller'
        self.groupbuy.seller_selection_end = timezone.now() + timedelta(hours=5)
        self.groupbuy.save()
        
        self.client.force_authenticate(user=self.seller2)
        
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/seller-decision/',
            {'decision': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_final_decision_status(self):
        """최종선택 상태 조회 테스트"""
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get(
            f'/api/groupbuys/{self.groupbuy.id}/decision-status/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'buyer')
        self.assertEqual(response.data['decision'], 'pending')
        self.assertIsNotNone(response.data['deadline'])

    def test_contact_info_access_buyer(self):
        """구매자의 판매자 연락처 접근 테스트"""
        # 구매확정 먼저
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get(
            f'/api/groupbuys/{self.groupbuy.id}/contact-info/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'seller')

    def test_contact_info_denied_without_confirmation(self):
        """확정하지 않은 경우 연락처 접근 불가"""
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get(
            f'/api/groupbuys/{self.groupbuy.id}/contact-info/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mypage_pending_selection_buyer(self):
        """구매자 마이페이지 최종선택 대기중 목록"""
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get('/api/groupbuys/pending_selection/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.groupbuy.id)

    def test_mypage_pending_selection_seller(self):
        """판매자 마이페이지 최종선택 대기중 목록"""
        # 구매자 전원이 선택을 완료한 후 판매자 선택 단계로 이동
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        self.participation2.final_decision = 'confirmed'
        self.participation2.save()
        
        # 공구 상태를 final_selection_seller로 변경
        self.groupbuy.status = 'final_selection_seller'
        self.groupbuy.seller_selection_end = timezone.now() + timedelta(hours=5)
        self.groupbuy.save()
        
        self.client.force_authenticate(user=self.seller1)
        
        response = self.client.get('/api/groupbuys/pending_selection/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.groupbuy.id)

    def test_mypage_purchase_confirmed(self):
        """구매확정 목록 테스트"""
        # 구매확정 처리
        self.participation1.final_decision = 'confirmed'
        self.participation1.save()
        
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get('/api/groupbuys/purchase_confirmed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_mypage_seller_confirmed(self):
        """판매자 판매확정 목록 테스트"""
        # 판매확정 처리
        self.bid1.final_decision = 'confirmed'
        self.bid1.save()
        
        self.client.force_authenticate(user=self.seller1)
        
        response = self.client.get('/api/groupbuys/seller_confirmed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_joined_groupbuys_excludes_final_selection(self):
        """참여중인 공구 목록에서 final_selection 상태 제외"""
        # recruiting 상태의 다른 공구 생성
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
        
        Participation.objects.create(
            user=self.buyer1,
            groupbuy=recruiting_groupbuy,
            is_leader=False
        )
        
        self.client.force_authenticate(user=self.buyer1)
        
        response = self.client.get('/api/groupbuys/joined_groupbuys/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # final_selection 상태인 self.groupbuy는 제외되고, recruiting 상태만 포함
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], recruiting_groupbuy.id)


class CronJobTestCase(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass',
            role='buyer'
        )
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='testpass',
            role='seller'
        )
        
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            base_price=100000
        )

    def test_cron_final_selection_timeout(self):
        """최종선택 시간 초과 시 cron job 처리 테스트"""
        from django.core.management import call_command
        
        # 최종선택 시간이 만료된 공구 생성
        groupbuy = GroupBuy.objects.create(
            title='Expired Final Selection',
            description='Test Description',
            product=self.product,
            creator=self.buyer,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(hours=1),
            final_selection_end=timezone.now() - timedelta(minutes=1),
            status='final_selection_buyers',
            current_participants=1
        )
        
        # 참여자와 낙찰자 생성
        Participation.objects.create(
            user=self.buyer,
            groupbuy=groupbuy,
            is_leader=True
        )
        
        Bid.objects.create(
            groupbuy=groupbuy,
            seller=self.seller,
            amount=95000,
            status='selected'
        )
        
        # cron job 실행
        call_command('update_groupbuy_status')
        
        # 상태 확인
        groupbuy.refresh_from_db()
        self.assertEqual(groupbuy.status, 'cancelled')

    def test_cron_all_confirmed_completion(self):
        """모든 참여자가 확정한 경우 완료 처리 테스트"""
        from django.core.management import call_command
        
        groupbuy = GroupBuy.objects.create(
            title='All Confirmed',
            description='Test Description',
            product=self.product,
            creator=self.buyer,
            min_participants=1,
            max_participants=10,
            start_time=timezone.now() - timedelta(hours=25),
            end_time=timezone.now() - timedelta(hours=1),
            final_selection_end=timezone.now() + timedelta(hours=1),
            status='final_selection_buyers',
            current_participants=1
        )
        
        # 구매확정된 참여자
        participation = Participation.objects.create(
            user=self.buyer,
            groupbuy=groupbuy,
            is_leader=True,
            final_decision='confirmed'
        )
        
        # 판매확정된 낙찰자
        bid = Bid.objects.create(
            groupbuy=groupbuy,
            seller=self.seller,
            amount=95000,
            status='selected',
            final_decision='confirmed'
        )
        
        # cron job 실행 전에는 final_selection_buyers 상태
        self.assertEqual(groupbuy.status, 'final_selection_buyers')
        
        # 수동으로 완료 확인 로직 호출 
        # check_all_decisions_completed는 더 이상 필요하지 않음 - utils.py에서 자동 처리됨
        from api.utils import update_groupbuys_status
        update_groupbuys_status([groupbuy])
        
        # 상태 확인
        groupbuy.refresh_from_db()
        self.assertEqual(groupbuy.status, 'completed')
        
    def test_mutual_confirmation_flow(self):
        """구매자와 판매자가 모두 확정하는 플로우 테스트"""
        # 구매자 확정
        self.client.force_authenticate(user=self.buyer1)
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'confirmed'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 판매자 확정
        self.client.force_authenticate(user=self.seller1)
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/seller-decision/',
            {'decision': 'confirmed'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 모든 구매자가 확정했는지 확인 (buyer2도 확정해야 함)
        self.client.force_authenticate(user=self.buyer2)
        response = self.client.post(
            f'/api/groupbuys/{self.groupbuy.id}/buyer-decision/',
            {'decision': 'confirmed'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 상호 확정 확인 로직 실행
        from api.views_final_selection import check_all_decisions_completed
        check_all_decisions_completed(self.groupbuy)
        
        # 공구 상태가 completed로 변경되었는지 확인
        self.groupbuy.refresh_from_db()
        self.assertEqual(self.groupbuy.status, 'completed')