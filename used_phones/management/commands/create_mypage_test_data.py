"""
Management command to create test data for MyPage functionality
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from used_phones.models import UsedPhone, UsedPhoneImage, UsedPhoneOffer
from api.models_unified_simple import UnifiedFavorite
from api.models import Region
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for MyPage functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before creating new data',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Creating test data for MyPage...'))
        
        if options['clear']:
            self.clear_test_data()
        
        # Create test users
        seller1 = self.create_test_user('seller1', 'seller')
        seller2 = self.create_test_user('seller2', 'seller')
        buyer1 = self.create_test_user('buyer1', 'buyer')
        buyer2 = self.create_test_user('buyer2', 'buyer')
        
        # Get or create regions
        seoul_gangnam = self.get_or_create_region('서울특별시', '강남구')
        seoul_songpa = self.get_or_create_region('서울특별시', '송파구')
        
        # Create phones for sellers
        phone1 = self.create_phone(seller1, 'iPhone 14 Pro', seoul_gangnam, 'active')
        phone2 = self.create_phone(seller1, 'Galaxy S23 Ultra', seoul_songpa, 'active')
        phone3 = self.create_phone(seller1, 'iPhone 13', seoul_gangnam, 'trading')
        phone4 = self.create_phone(seller1, 'Galaxy Z Flip 5', seoul_gangnam, 'sold')
        
        phone5 = self.create_phone(seller2, 'iPhone 15 Pro Max', seoul_songpa, 'active')
        phone6 = self.create_phone(seller2, 'Xiaomi 13 Pro', seoul_gangnam, 'active')
        
        # Create offers
        self.create_offer(phone1, buyer1, 850000, 'pending')
        self.create_offer(phone1, buyer2, 880000, 'pending')
        self.create_offer(phone2, buyer1, 950000, 'rejected')
        self.create_offer(phone3, buyer1, 650000, 'accepted')
        self.create_offer(phone5, buyer1, 1200000, 'pending')
        self.create_offer(phone5, buyer2, 1150000, 'pending')
        
        # Create favorites
        self.create_favorite(phone1, buyer1)
        self.create_favorite(phone2, buyer1)
        self.create_favorite(phone5, buyer1)
        self.create_favorite(phone1, buyer2)
        self.create_favorite(phone6, buyer2)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Test data created successfully!'))
        self.stdout.write('\nTest accounts:')
        self.stdout.write('  - seller1 / testpass123 (판매자)')
        self.stdout.write('  - seller2 / testpass123 (판매자)')
        self.stdout.write('  - buyer1 / testpass123 (구매자)')
        self.stdout.write('  - buyer2 / testpass123 (구매자)')
    
    def clear_test_data(self):
        """Clear existing test data"""
        self.stdout.write('Clearing existing test data...')
        
        # Delete test users and their related data
        test_usernames = ['seller1', 'seller2', 'buyer1', 'buyer2']
        User.objects.filter(username__in=test_usernames).delete()
        
        self.stdout.write(self.style.SUCCESS('Test data cleared'))
    
    def create_test_user(self, username, role):
        """Create a test user"""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'role': role,
                'nickname': f'테스트{username}',
                'phone_number': f'010{random.randint(10000000, 99999999)}',
                'phone_verified': True,
                'phone_verified_at': timezone.now(),
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'  Created user: {username} ({role})')
        else:
            self.stdout.write(f'  User exists: {username}')
        
        return user
    
    def get_or_create_region(self, province, city):
        """Get or create a region"""
        # Try to find the region
        region = Region.objects.filter(
            name=city,
            parent__name=province
        ).first()
        
        if not region:
            # Create parent region if not exists
            parent, _ = Region.objects.get_or_create(
                name=province,
                defaults={
                    'code': f'{province[:2]}00',
                    'level': 0,
                    'full_name': province
                }
            )
            
            # Create child region
            region, _ = Region.objects.get_or_create(
                name=city,
                parent=parent,
                defaults={
                    'code': f'{province[:2]}{city[:2]}',
                    'level': 1,
                    'full_name': f'{province} {city}'
                }
            )
        
        return region
    
    def create_phone(self, seller, model_name, region, status='active'):
        """Create a test phone"""
        brand_map = {
            'iPhone': 'apple',
            'Galaxy': 'samsung',
            'Xiaomi': 'xiaomi',
        }
        
        brand = 'apple'
        for key, value in brand_map.items():
            if key in model_name:
                brand = value
                break
        
        phone = UsedPhone.objects.create(
            seller=seller,
            brand=brand,
            model=model_name,
            storage=random.choice([128, 256, 512]),
            color=random.choice(['블랙', '화이트', '블루', '그린']),
            price=random.randint(500000, 1500000),
            min_offer_price=random.randint(400000, 1200000),
            accept_offers=True,
            condition_grade=random.choice(['S', 'A', 'B']),
            condition_description='테스트용 상품입니다.',
            battery_status=random.choice(['excellent', 'good', 'fair']),
            body_only=False,
            has_box=True,
            has_charger=True,
            has_earphones=random.choice([True, False]),
            description=f'{model_name} 판매합니다. 상태 좋습니다.',
            region=region,
            region_name=region.full_name,
            meeting_place='지하철역 앞',
            status=status,
            view_count=random.randint(10, 500),
            favorite_count=random.randint(0, 20),
            offer_count=random.randint(0, 10),
        )
        
        # Set sold_at for sold items
        if status == 'sold':
            phone.sold_at = timezone.now() - timedelta(days=random.randint(1, 30))
            phone.save()
        
        self.stdout.write(f'  Created phone: {model_name} ({status})')
        
        return phone
    
    def create_offer(self, phone, buyer, amount, status='pending'):
        """Create a test offer"""
        offer = UsedPhoneOffer.objects.create(
            phone=phone,
            buyer=buyer,
            amount=amount,
            message=f'{buyer.username}입니다. 상태 좋으면 바로 구매하겠습니다.',
            status=status,
        )
        
        if status == 'accepted':
            offer.seller_message = '네, 연락드리겠습니다.'
            offer.save()
        elif status == 'rejected':
            offer.seller_message = '죄송합니다. 다른 분과 거래 예정입니다.'
            offer.save()
        
        self.stdout.write(f'  Created offer: {phone.model} <- {buyer.username} ({status})')
        
        return offer
    
    def create_favorite(self, phone, user):
        """Create a test favorite"""
        favorite, created = UnifiedFavorite.objects.get_or_create(
            user=user,
            item_type='phone',
            item_id=phone.id
        )
        
        if created:
            self.stdout.write(f'  Created favorite: {phone.model} <- {user.username}')
        
        return favorite