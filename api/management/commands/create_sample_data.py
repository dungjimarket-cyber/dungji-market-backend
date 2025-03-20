# api/management/commands/create_sample_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import User, Category, Product, GroupBuy, Participation

class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        # === 1. 유저 10명 생성 ===
        users = []
        for i in range(1, 11):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@test.com",
                password="test1234",
                first_name=f"유저{i}"
            )
            users.append(user)

        print("생성된 사용자:", [u.username for u in users])

        # === 2. 카테고리 & 상품(휴대폰) 10개 생성 ===
        phone_category, _ = Category.objects.get_or_create(
            name="휴대폰",
            slug="phone-category"
        )

        product_names = [
            "Samsung Galaxy S24",
            "Samsung Galaxy Z Flip5",
            "iPhone 15 Pro",
            "iPhone 15",
            "LG V60 ThinQ",
            "Xiaomi Mi 13",
            "Google Pixel 8",
            "OnePlus 11",
            "Motorola Edge 40",
            "Sony Xperia 1 V"
        ]

        products = []
        for idx, name in enumerate(product_names, start=1):
            prod = Product.objects.create(
                name=name,
                slug=f"phone-{idx}",
                description=f"{name}의 상세 설명입니다...",
                category=phone_category,
                product_type="device",
                base_price=100000 * idx,  # 임의 가격
                image_url=f"http://example.com/phone{idx}.jpg"
            )
            products.append(prod)

        print("생성된 상품:", [p.name for p in products])

        # === 3. 공구 10개 생성 ===
        groupbuys = []
        now = timezone.now()

        for i in range(1, 6):  # 진행 중 (recruiting)
            gb = GroupBuy.objects.create(
                product=products[i-1],
                creator=users[i-1],
                min_participants=2,
                max_participants=5,
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(hours=24),
                status="recruiting",
                current_participants=0
            )
            groupbuys.append(gb)

        for i in range(6, 11):  # 완료 or 취소
            gb = GroupBuy.objects.create(
                product=products[i-1],
                creator=users[i-1],
                min_participants=2,
                max_participants=5,
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=1),
                status="completed" if i % 2 == 0 else "cancelled",
                current_participants=0
            )
            groupbuys.append(gb)

        print("생성된 공구:", [(gb.id, gb.product.name, gb.status) for gb in groupbuys])

        # === 4. 임의로 각 공구에 참가자(Participation) 넣기 ===
        recruiting_groupbuys = groupbuys[:5]
        user_index = 0

        for gb in recruiting_groupbuys:
            number_of_participants = 2
            for _ in range(number_of_participants):
                user_index += 1
                if user_index >= len(users):
                    user_index = 0
                p = Participation.objects.create(
                    user=users[user_index],
                    groupbuy=gb
                )
            gb.current_participants = number_of_participants
            gb.save()

        print("진행중 공구에 몇몇 유저를 참여시켰습니다.")