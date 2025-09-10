"""
중고폰 샘플 데이터 생성 커맨드
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from used_phones.models import UsedPhone, UsedPhoneRegion
from api.models import Region

User = get_user_model()


class Command(BaseCommand):
    help = '테스트용 중고폰 샘플 데이터 10개 생성'

    def handle(self, *args, **kwargs):
        # 사용자 가져오기 (첫 번째 사용자를 판매자로 설정)
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('사용자가 없습니다. 먼저 사용자를 생성해주세요.'))
            return

        # 활성화된 지역 목록 가져오기 (시군구 레벨)
        regions = Region.objects.filter(is_active=True, level__in=[1, 2])
        if not regions:
            self.stdout.write(self.style.ERROR('지역 데이터가 없습니다.'))
            return

        # 샘플 데이터 정의
        phone_models = [
            ('apple', 'iPhone 15 Pro Max', 256, '1,200,000'),
            ('apple', 'iPhone 14 Pro', 128, '950,000'),
            ('apple', 'iPhone 13', 128, '750,000'),
            ('samsung', 'Galaxy S24 Ultra', 512, '1,350,000'),
            ('samsung', 'Galaxy S23', 256, '850,000'),
            ('samsung', 'Galaxy Z Flip5', 256, '980,000'),
            ('samsung', 'Galaxy Z Fold5', 512, '1,650,000'),
            ('apple', 'iPhone 12 Pro', 256, '650,000'),
            ('samsung', 'Galaxy S22', 128, '620,000'),
            ('xiaomi', 'Xiaomi 13 Pro', 256, '780,000'),
        ]

        colors = ['블랙', '화이트', '블루', '퍼플', '그린', '골드', '실버']
        conditions = ['A', 'B', 'C']
        battery_statuses = ['excellent', 'good', 'fair']
        
        descriptions = [
            '깨끗하게 사용한 제품입니다. 기스 거의 없어요.',
            '정상 작동하며 상태 양호합니다.',
            '액정 보호필름 부착 상태로 사용했습니다.',
            '케이스 착용하여 깨끗하게 관리했습니다.',
            '배터리 성능 좋고 모든 기능 정상입니다.',
            '업무용으로만 사용한 제품입니다.',
            '서브폰으로 가끔 사용했습니다.',
            '최근에 구매한 제품입니다.',
            '박스 및 구성품 모두 있습니다.',
            '급처로 저렴하게 판매합니다.',
        ]

        meeting_places = [
            '지하철역 앞',
            '스타벅스',
            '편의점 앞',
            '아파트 정문',
            '대학교 정문',
            '시청 앞',
            '버스정류장',
            '은행 앞',
        ]

        created_count = 0

        for i in range(10):
            # 랜덤 데이터 선택
            brand, model, storage, price_str = phone_models[i]
            price = int(price_str.replace(',', ''))
            color = random.choice(colors)
            condition = random.choice(conditions)
            battery_status = random.choice(battery_statuses)
            description = random.choice(descriptions)
            meeting_place = random.choice(meeting_places)
            
            # 메인 지역 선택
            main_region = random.choice(regions)
            
            # 가격 제안 허용 여부
            accept_offers = random.choice([True, False])
            min_offer_price = price - random.randint(50000, 150000) if accept_offers else None
            
            # 구성품 랜덤 설정
            body_only = random.choice([True, False])
            has_box = False if body_only else random.choice([True, False])
            has_charger = False if body_only else random.choice([True, False])
            has_earphones = False if body_only else random.choice([True, False])

            try:
                # 중고폰 생성
                phone = UsedPhone.objects.create(
                    seller=user,
                    brand=brand,
                    model=model,
                    storage=storage,
                    color=color,
                    price=price,
                    min_offer_price=min_offer_price,
                    accept_offers=accept_offers,
                    condition_grade=condition,
                    condition_description=f"{condition}급 상태입니다. {description}",
                    battery_status=battery_status,
                    body_only=body_only,
                    has_box=has_box,
                    has_charger=has_charger,
                    has_earphones=has_earphones,
                    description=description,
                    region=main_region,
                    meeting_place=meeting_place,
                    status='active',
                    view_count=random.randint(0, 100),
                    favorite_count=random.randint(0, 20),
                    offer_count=random.randint(0, 5),
                )
                
                # 랜덤하게 1~3개의 추가 지역 설정
                additional_regions_count = random.randint(0, 2)
                if additional_regions_count > 0:
                    # 메인 지역과 다른 지역들 선택
                    available_regions = list(regions.exclude(id=main_region.id))
                    selected_regions = random.sample(
                        available_regions, 
                        min(additional_regions_count, len(available_regions))
                    )
                    
                    # 메인 지역 추가
                    UsedPhoneRegion.objects.create(
                        used_phone=phone,
                        region=main_region
                    )
                    
                    # 추가 지역들 추가
                    for region in selected_regions:
                        UsedPhoneRegion.objects.create(
                            used_phone=phone,
                            region=region
                        )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{created_count}. {model} ({color}, {condition}급) - '
                        f'{price:,}원 - {main_region.full_name}'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'생성 실패: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n총 {created_count}개의 중고폰 샘플 데이터가 생성되었습니다.')
        )