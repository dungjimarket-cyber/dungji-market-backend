"""
중고폰 샘플 데이터 자동 생성 마이그레이션
"""
import random
from django.db import migrations


def create_sample_phones(apps, schema_editor):
    """샘플 중고폰 데이터 생성"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    UsedPhoneRegion = apps.get_model('used_phones', 'UsedPhoneRegion')
    Region = apps.get_model('api', 'Region')
    User = apps.get_model('api', 'User')  # Custom User model
    
    # 사용자 가져오기
    user = User.objects.first()
    if not user:
        print('사용자가 없어 샘플 데이터를 생성하지 않습니다.')
        return
    
    # 활성화된 지역 목록 가져오기
    regions = list(Region.objects.filter(is_active=True, level__in=[1, 2]))
    if not regions:
        print('지역 데이터가 없어 샘플 데이터를 생성하지 않습니다.')
        return
    
    # 이미 샘플 데이터가 있는지 확인
    if UsedPhone.objects.filter(model__contains='iPhone').exists():
        print('이미 샘플 데이터가 존재합니다.')
        return
    
    # 샘플 데이터 정의
    phone_models = [
        ('apple', 'iPhone 15 Pro Max', 256, 1200000),
        ('apple', 'iPhone 14 Pro', 128, 950000),
        ('apple', 'iPhone 13', 128, 750000),
        ('samsung', 'Galaxy S24 Ultra', 512, 1350000),
        ('samsung', 'Galaxy S23', 256, 850000),
        ('samsung', 'Galaxy Z Flip5', 256, 980000),
        ('samsung', 'Galaxy Z Fold5', 512, 1650000),
        ('apple', 'iPhone 12 Pro', 256, 650000),
        ('samsung', 'Galaxy S22', 128, 620000),
        ('xiaomi', 'Xiaomi 13 Pro', 256, 780000),
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
    ]
    
    meeting_places = [
        '지하철역 앞',
        '스타벅스',
        '편의점 앞',
        '아파트 정문',
        '대학교 정문',
    ]
    
    created_count = 0
    
    for i, (brand, model, storage, price) in enumerate(phone_models):
        color = colors[i % len(colors)]
        condition = conditions[i % len(conditions)]
        battery_status = battery_statuses[i % len(battery_statuses)]
        description = descriptions[i % len(descriptions)]
        meeting_place = meeting_places[i % len(meeting_places)]
        
        # 메인 지역 선택
        main_region = regions[i % len(regions)]
        
        # 가격 제안 허용 여부
        accept_offers = i % 2 == 0
        min_offer_price = price - 100000 if accept_offers else None
        
        # 구성품 설정
        body_only = i % 3 == 0
        has_box = not body_only and i % 2 == 0
        has_charger = not body_only and i % 2 == 1
        has_earphones = not body_only and i % 4 == 0
        
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
                view_count=(i + 1) * 10,
                favorite_count=i,
                offer_count=i // 2,
            )
            
            # 메인 지역을 UsedPhoneRegion에도 추가
            UsedPhoneRegion.objects.create(
                used_phone=phone,
                region=main_region
            )
            
            # 추가 지역 설정 (3개 중 1개만)
            if i % 3 == 0 and len(regions) > 1:
                additional_region = regions[(i + 1) % len(regions)]
                if additional_region.id != main_region.id:
                    UsedPhoneRegion.objects.create(
                        used_phone=phone,
                        region=additional_region
                    )
            
            created_count += 1
            print(f'{created_count}. {model} 생성 완료')
            
        except Exception as e:
            print(f'생성 실패: {e}')
    
    print(f'총 {created_count}개의 중고폰 샘플 데이터가 생성되었습니다.')


def reverse_sample_phones(apps, schema_editor):
    """샘플 데이터 삭제 (롤백용)"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    # 샘플 데이터만 삭제 (iPhone, Galaxy 등이 포함된 모델명)
    UsedPhone.objects.filter(
        model__in=[
            'iPhone 15 Pro Max', 'iPhone 14 Pro', 'iPhone 13',
            'Galaxy S24 Ultra', 'Galaxy S23', 'Galaxy Z Flip5',
            'Galaxy Z Fold5', 'iPhone 12 Pro', 'Galaxy S22',
            'Xiaomi 13 Pro'
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0004_fix_accessories_field'),
    ]

    operations = [
        migrations.RunPython(create_sample_phones, reverse_sample_phones),
    ]