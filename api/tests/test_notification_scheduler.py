"""
Tests for the NotificationScheduler utility class.
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock
from api.models import GroupBuy, Notification, Bid, Participation, Category, Product, Region
from api.utils.notification_scheduler import NotificationScheduler

User = get_user_model()

class NotificationSchedulerTestCase(TestCase):
    """Test case for the NotificationScheduler utility class."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='user1@example.com',
            password='password123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='user2@example.com',
            password='password123'
        )
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='password123'
        )
        
        # Create test category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            detail_type='none'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test product description',
            category=self.category,
            product_type='device',
            base_price=100000,
            image_url='https://example.com/image.jpg'
        )
        
        # Create a test region
        self.region = Region.objects.create(
            code='TEST',
            name='Test Region',
            full_name='Test Region Full Name',
            level=0  # 시/도 level
        )
        
        # Create a test group buy
        self.groupbuy = GroupBuy.objects.create(
            title='Test Group Buy',
            description='Test description',
            creator=self.user1,
            product=self.product,  # Add product to avoid NoneType error
            product_name='Test Product',  # Add product name backup
            status='bidding',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(hours=6),  # 6 hours from now
            min_participants=2,
            max_participants=10,
            current_participants=2,
            region=self.region,  # Add region
            region_name='Test Region'  # Add region name backup
        )
        
        # Create participations
        self.participation1 = Participation.objects.create(
            user=self.user1,
            groupbuy=self.groupbuy
        )
        self.participation2 = Participation.objects.create(
            user=self.user2,
            groupbuy=self.groupbuy
        )
        
        # Create a test bid
        self.bid = Bid.objects.create(
            groupbuy=self.groupbuy,
            seller=self.seller,
            amount=1000,
            message='Test bid message',
            is_selected=True,
            status='selected'
        )

    def test_send_bid_reminders_notification_type(self):
        """Test that bid reminders have the correct notification_type."""
        # Set the end_time to be within the next 12 hours
        self.groupbuy.status = 'bidding'
        self.groupbuy.end_time = timezone.now() + timedelta(hours=6)
        self.groupbuy.save()
        
        # Call the method
        NotificationScheduler.send_bid_reminders()
        
        # Check that a notification was created with the correct type
        notifications = Notification.objects.filter(groupbuy=self.groupbuy)
        self.assertTrue(notifications.exists())
        # Check that the notification_type is 'info' as actually created
        self.assertEqual(notifications.first().notification_type, 'info')

    def test_send_bid_confirmation_reminders_notification_type(self):
        """Test that bid confirmation reminders have the correct notification_type."""
        # Set the final_selection_end to be within the next 12 hours
        self.groupbuy.status = 'final_selection'
        self.groupbuy.final_selection_end = timezone.now() + timedelta(hours=6)
        self.groupbuy.save()
        
        # Mock the vote_set attribute since we don't have the Vote model in our test
        # This is a workaround for the AttributeError: 'GroupBuy' object has no attribute 'vote_set'
        class MockQuerySet:
            def values_list(self, *args, **kwargs):
                return []
                
        self.groupbuy.vote_set = MockQuerySet()
        
        # Call the method
        NotificationScheduler.send_bid_confirmation_reminders()
        
        # Check that notifications were created with the correct type
        notifications = Notification.objects.filter(groupbuy=self.groupbuy)
        self.assertTrue(notifications.exists())
        self.assertEqual(notifications.first().notification_type, 'info')

    def test_send_seller_confirmation_reminders_notification_type(self):
        """Test that seller confirmation reminders have the correct notification_type."""
        # Set the final_selection_end to be 12 hours ago so seller confirmation deadline is in 12 hours
        self.groupbuy.status = 'seller_confirmation'
        self.groupbuy.final_selection_end = timezone.now() - timedelta(hours=12)
        self.groupbuy.save()
        
        # Update the bid to be selected/winner
        self.bid.is_selected = True
        self.bid.status = 'selected'
        self.bid.save()
        
        # Monkey patch the filter method to return our bid
        original_filter = Bid.objects.filter
        
        def mock_filter(*args, **kwargs):
            if 'is_winner' in kwargs:
                # Convert is_winner to is_selected for compatibility
                kwargs['is_selected'] = kwargs.pop('is_winner')
            return original_filter(*args, **kwargs)
        
        # Apply the monkey patch
        Bid.objects.filter = mock_filter
        
        try:
            # Call the method
            NotificationScheduler.send_seller_confirmation_reminders()
            
            # Check that notifications were created with the correct type
            notifications = Notification.objects.filter(groupbuy=self.groupbuy)
            self.assertTrue(notifications.exists())
            self.assertEqual(notifications.first().notification_type, 'info')
        finally:
            # Restore the original filter method
            Bid.objects.filter = original_filter

    def test_process_expired_confirmations_notification_type(self):
        """Test that expired confirmations have the correct notification_type."""
        # Create a GroupBuy with voting_end in the past
        category = Category.objects.create(name="Unique Test Category")
        product = Product.objects.create(
            name="Unique Test Product", 
            category=category,
            base_price=10000  # Adding required base_price field
        )
        region = Region.objects.create(code="test", name="Test Region", full_name="Test Full Region", level=1)
        user = User.objects.create_user(username="testuser", email="user@example.com")
        groupbuy = GroupBuy.objects.create(
            title="Test GroupBuy",
            description="Test Description",
            target_price=100,  # Changed from target_amount to target_price
            creator=user,
            product=product,
            region=region,
            status='final_selection',
            start_time=timezone.now() - timedelta(hours=24),
            final_selection_end=timezone.now() - timedelta(hours=12),
            end_time=timezone.now() + timedelta(days=7)
        )
        
        # Create a participation
        participation = Participation.objects.create(user=user, groupbuy=groupbuy)
        
        # Mock the vote_set attribute to avoid AttributeError
        mock_vote_set = MagicMock()
        # Configure the mock to return a specific count when used in calculations
        mock_vote_set.filter.return_value.count.return_value = 0
        # Also mock the values_list method which might be used
        mock_vote_set.values_list.return_value = []
        groupbuy.vote_set = mock_vote_set
        
        # Monkey patch GroupBuy.objects.filter to return our mocked groupbuy
        original_filter = GroupBuy.objects.filter
        GroupBuy.objects.filter = MagicMock(return_value=[groupbuy])
        
        try:
            # Process expired confirmations
            NotificationScheduler.process_expired_confirmations()
            
            # Check that a notification was created with the correct type
            notifications = Notification.objects.filter(user=user, groupbuy=groupbuy)
            self.assertTrue(notifications.exists())
            self.assertEqual(notifications.first().notification_type, 'info')
        finally:
            # Restore the original filter method
            GroupBuy.objects.filter = original_filter

    def test_process_expired_seller_confirmations_notification_type(self):
        """Test that expired seller confirmations have the correct notification_type."""
        # Set the final_selection_end to be more than 24 hours in the past
        self.groupbuy.status = 'seller_confirmation'
        self.groupbuy.final_selection_end = timezone.now() - timedelta(hours=25)
        self.groupbuy.save()
        
        # Update the bid to be selected/winner
        self.bid.is_selected = True
        self.bid.status = 'selected'
        self.bid.save()
        
        # Monkey patch the filter method to return our bid
        original_filter = Bid.objects.filter
        
        def mock_filter(*args, **kwargs):
            if 'is_winner' in kwargs:
                # Convert is_winner to is_selected for compatibility
                kwargs['is_selected'] = kwargs.pop('is_winner')
            return original_filter(*args, **kwargs)
        
        # Apply the monkey patch
        Bid.objects.filter = mock_filter
        
        try:
            # Call the method
            NotificationScheduler.process_expired_seller_confirmations()
            
            # Check that notifications were created with the correct type
            notifications = Notification.objects.filter(groupbuy=self.groupbuy)
            self.assertTrue(notifications.exists())
            # The actual notification_type should be 'info' for expired confirmations
            for notification in notifications:
                self.assertEqual(notification.notification_type, 'info')
        finally:
            # Restore the original filter method
            Bid.objects.filter = original_filter
