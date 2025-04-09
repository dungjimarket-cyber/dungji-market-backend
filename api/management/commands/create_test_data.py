from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from api.models import Category, Product, GroupBuy
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test data for the application'

    def handle(self, *args, **options):
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        GroupBuy.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        
        # Create categories
        self.stdout.write('Creating categories...')
        categories = [
            Category(name='휴대폰'),
            Category(name='태블릿'),
            Category(name='노트북'),
            Category(name='스마트워치'),
            Category(name='이어폰'),
        ]
        
        Category.objects.bulk_create(categories)
        
        # Get categories from DB to use their IDs
        categories = Category.objects.all()
        
        # Create products
        self.stdout.write('Creating products...')
        products = [
            Product(
                name='Samsung Galaxy S25',
                slug=slugify('Samsung Galaxy S25'),
                description='Samsung Galaxy S25의 상세 설명입니다...',
                base_price=900000,
                image_url='https://image.shop.kt.com/upload/product/WL00073193/1736847043089.png',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='SKT',
                registration_type='MNP',
                plan_info='5G 프리미엄 요금제',
                contract_info='24개월 약정',
                total_support_amount=500000,
                release_date=date(2024, 3, 15)
            ),
            Product(
                name='Samsung Galaxy Z Flip6',
                slug=slugify('Samsung Galaxy Z Flip6'),
                description='Samsung Galaxy Z Flip6의 상세 설명입니다...',
                base_price=200000,
                image_url='https://img.danawa.com/prod_img/500000/956/914/img/58914956_1.jpg',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='KT',
                registration_type='MNP',
                plan_info='5G 슬림 요금제',
                contract_info='36개월 약정',
                total_support_amount=300000,
                release_date=date(2024, 2, 10)
            ),
            Product(
                name='iPhone 16 Pro',
                slug=slugify('iPhone 16 Pro'),
                description='iPhone 16 Pro의 상세 설명입니다...',
                base_price=300000,
                image_url='https://img.danawa.com/prod_img/500000/552/222/img/65222552_1.jpg?shrink=500:500&_v=20250326173350',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='LGU+',
                registration_type='New',
                plan_info='5G 시그니처 요금제',
                contract_info='24개월 약정',
                total_support_amount=400000,
                release_date=date(2024, 1, 20)
            ),
            Product(
                name='iPhone 16',
                slug=slugify('iPhone 16'),
                description='iPhone 16의 상세 설명입니다...',
                base_price=400000,
                image_url='https://img.danawa.com/prod_img/500000/074/051/img/66051074_1.jpg?shrink=500:500&_v=20250217150523',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='SKT',
                registration_type='MNP',
                plan_info='5G 베이직 요금제',
                contract_info='24개월 약정',
                total_support_amount=350000,
                release_date=date(2024, 1, 15)
            ),
            Product(
                name='LG V60 ThinQ',
                slug=slugify('LG V60 ThinQ'),
                description='LG V60 ThinQ의 상세 설명입니다...',
                base_price=500000,
                image_url='https://img.danawa.com/prod_img/500000/206/786/img/78786206_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='MVNO',
                registration_type='MNP',
                plan_info='데이터 10GB 요금제',
                contract_info='12개월 약정',
                total_support_amount=150000,
                release_date=date(2023, 11, 15)
            ),
            Product(
                name='Xiaomi Mi 13',
                slug=slugify('Xiaomi Mi 13'),
                description='Xiaomi Mi 13의 상세 설명입니다...',
                base_price=600000,
                image_url='https://img.danawa.com/prod_img/500000/013/856/img/42856013_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='SKT',
                registration_type='MNP',
                plan_info='5G 라이트 요금제',
                contract_info='24개월 약정',
                total_support_amount=250000,
                release_date=date(2023, 10, 5)
            ),
            Product(
                name='Google Pixel 8',
                slug=slugify('Google Pixel 8'),
                description='Google Pixel 8의 상세 설명입니다...',
                base_price=700000,
                image_url='https://img.danawa.com/prod_img/500000/281/584/img/28584281_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='KT',
                registration_type='New',
                plan_info='5G 스페셜 요금제',
                contract_info='24개월 약정',
                total_support_amount=350000,
                release_date=date(2023, 9, 15)
            ),
            Product(
                name='OnePlus 11',
                slug=slugify('OnePlus 11'),
                description='OnePlus 11의 상세 설명입니다...',
                base_price=800000,
                image_url='https://img.danawa.com/prod_img/500000/005/675/img/18675005_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='LGU+',
                registration_type='MNP',
                plan_info='5G 프리미엄 요금제',
                contract_info='36개월 약정',
                total_support_amount=400000,
                release_date=date(2023, 8, 20)
            ),
            Product(
                name='Motorola Edge 40',
                slug=slugify('Motorola Edge 40'),
                description='Motorola Edge 40의 상세 설명입니다...',
                base_price=900000,
                image_url='https://img.danawa.com/prod_img/500000/577/694/img/69694577_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='SKT',
                registration_type='MNP',
                plan_info='5G 스탠다드 요금제',
                contract_info='24개월 약정',
                total_support_amount=300000,
                release_date=date(2023, 7, 10)
            ),
            Product(
                name='Sony Xperia 1 V',
                slug=slugify('Sony Xperia 1 V'),
                description='Sony Xperia 1 V의 상세 설명입니다...',
                base_price=1000000,
                image_url='https://img.danawa.com/prod_img/500000/272/458/img/55458272_1.jpg?shrink=500:500',
                category=categories[0],  # 휴대폰
                category_name='휴대폰',
                product_type='device',
                is_available=True,
                carrier='LGU+',
                registration_type='New',
                plan_info='5G 프리미엄 요금제',
                contract_info='24개월 약정',
                total_support_amount=450000,
                release_date=date(2023, 6, 5)
            ),
        ]
        
        Product.objects.bulk_create(products)

        # 기존 데이터 삭제 확장 (사용자 관련 데이터도 삭제)
        self.stdout.write('Clearing user related data...')
        # 모든 테스트 사용자 삭제 (이메일 패턴으로)
        User.objects.filter(username__iregex=r'(test|user\d+|organizer)@example\.com').delete()
        
        # Create test users
        self.stdout.write('Creating test users...')
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        # 테스트 사용자 생성 (10명)
        users = []
        for i in range(1, 11):
            user = User.objects.create_user(
                username=f'user{i}@example.com',
                email=f'user{i}@example.com',
                password='testpassword123',
                first_name=f'유저{i}',
                role='buyer'
            )
            user.phone_number = f'010-1234-{i:04d}'
            user.save()
            users.append(user)
        
        # 추가로 테스트 계정 생성
        test_user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpassword123',
            first_name='테스트 사용자',
            role='buyer'
        )
        test_user.phone_number = '010-1234-5678'
        test_user.save()
        
        organizer = User.objects.create_user(
            username='organizer@example.com',
            email='organizer@example.com',
            password='testpassword123',
            first_name='공동구매 주최자',
            role='organizer'
        )
        organizer.phone_number = '010-9876-5432'
        organizer.save()
        
        # Create group buys
        products = Product.objects.all()
        
        # 사용자가 제공한 이전 데이터와 유사한 공동구매 생성
        group_buys_data = [
            {
                'title': 'Samsung Galaxy S24',
                'product_index': 0,  # Samsung Galaxy S25
                'creator_index': 0,
                'status': 'recruiting',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=1),
                'end_time': now + timedelta(days=1),
                'current_participants': 2
            },
            {
                'title': 'Samsung Galaxy Z Flip5',
                'product_index': 1,  # Samsung Galaxy Z Flip6
                'creator_index': 1,
                'status': 'recruiting',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now + timedelta(days=40),
                'current_participants': 2
            },
            {
                'title': 'iPhone 15 Pro',
                'product_index': 2,  # iPhone 16 Pro
                'creator_index': 2,
                'status': 'recruiting',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now + timedelta(days=40),
                'current_participants': 2
            },
            {
                'title': 'iPhone 15',
                'product_index': 3,  # iPhone 16
                'creator_index': 3,
                'status': 'recruiting',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now + timedelta(days=40),
                'current_participants': 2
            },
            {
                'title': 'LG V60 ThinQ',
                'product_index': 4,  # LG V60 ThinQ
                'creator_index': 4,
                'status': 'recruiting',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now + timedelta(days=40),
                'current_participants': 2
            },
            {
                'title': 'Xiaomi Mi 13',
                'product_index': 5,  # Xiaomi Mi 13
                'creator_index': 5,
                'status': 'completed',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now - timedelta(days=1),
                'current_participants': 0
            },
            {
                'title': 'Google Pixel 8',
                'product_index': 6,  # Google Pixel 8
                'creator_index': 6,
                'status': 'cancelled',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now - timedelta(days=1),
                'current_participants': 0
            },
            {
                'title': 'OnePlus 11',
                'product_index': 7,  # OnePlus 11
                'creator_index': 7,
                'status': 'completed',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now - timedelta(days=1),
                'current_participants': 0
            },
            {
                'title': 'Motorola Edge 40',
                'product_index': 8,  # Motorola Edge 40
                'creator_index': 8,
                'status': 'cancelled',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now - timedelta(days=1),
                'current_participants': 0
            },
            {
                'title': 'Sony Xperia 1 V',
                'product_index': 9,  # Sony Xperia 1 V
                'creator_index': 9,
                'status': 'completed',
                'min_participants': 2,
                'max_participants': 5,
                'start_time': now - timedelta(days=50),
                'end_time': now - timedelta(days=1),
                'current_participants': 0
            },
        ]
        
        # Create group buys
        self.stdout.write('Creating group buys...')
        
        for i, data in enumerate(group_buys_data):
            product = products[data['product_index']]
            creator = users[data['creator_index']]
            
            GroupBuy.objects.create(
                title=data['title'],
                description=f"{product.name}의 공동구매입니다.",
                product=product,
                product_name=product.name,
                creator=creator,
                status=data['status'],
                min_participants=data['min_participants'],
                max_participants=data['max_participants'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                current_participants=data['current_participants']
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully created test data'))
