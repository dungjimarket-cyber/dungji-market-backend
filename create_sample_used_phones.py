"""
중고폰 샘플 데이터 생성 스크립트
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from used_phones.models import UsedPhone, UsedPhoneImage
from api.models import Region

User = get_user_model()

def create_sample_phones():
    # 테스트 사용자 가져오기 또는 생성
    try:
        user = User.objects.filter(is_staff=False).first()
        if not user:
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                phone='010-1234-5678'
            )
            print(f"테스트 사용자 생성: {user.username}")
        else:
            print(f"기존 사용자 사용: {user.username}")
    except Exception as e:
        print(f"사용자 생성/조회 실패: {e}")
        return

    # 샘플 데이터
    sample_phones = [
        {
            'model': 'iPhone 15 Pro Max',
            'brand': 'apple',
            'storage': 256,
            'color': '내추럴 티타늄',
            'price': 1450000,
            'min_offer_price': 1400000,
            'accept_offers': True,
            'condition_grade': 'A',
            'condition_description': '구매한지 3개월, 기스 없음',
            'battery_status': 'excellent',
            'body_only': False,
            'has_box': True,
            'has_charger': True,
            'has_earphones': False,
            'description': '애플케어+ 가입 상품입니다. 보호필름, 케이스 사용으로 깨끗합니다.',
            'meeting_place': '강남역 2번 출구',
        },
        {
            'model': 'Galaxy S24 Ultra',
            'brand': 'samsung',
            'storage': 512,
            'color': '티타늄 블랙',
            'price': 1350000,
            'min_offer_price': 1300000,
            'accept_offers': True,
            'condition_grade': 'A',
            'condition_description': '개봉만 한 미사용 제품',
            'battery_status': 'excellent',
            'body_only': False,
            'has_box': True,
            'has_charger': True,
            'has_earphones': True,
            'description': '선물 받았는데 사용하지 않은 제품입니다. 풀박스 구성품 모두 있습니다.',
            'meeting_place': '판교역 1번 출구',
        },
        {
            'model': 'iPhone 14 Pro',
            'brand': 'apple',
            'storage': 128,
            'color': '딥 퍼플',
            'price': 950000,
            'min_offer_price': 900000,
            'accept_offers': True,
            'condition_grade': 'B',
            'condition_description': '사용감 있지만 기능 정상',
            'battery_status': 'good',
            'body_only': False,
            'has_box': False,
            'has_charger': True,
            'has_earphones': False,
            'description': '1년 사용했습니다. 잔기스 있지만 사용에 문제없습니다.',
            'meeting_place': '신촌역 3번 출구',
        },
        {
            'model': 'Galaxy Z Fold 5',
            'brand': 'samsung',
            'storage': 256,
            'color': '아이시 블루',
            'price': 1550000,
            'min_offer_price': 1500000,
            'accept_offers': False,
            'condition_grade': 'A',
            'condition_description': '2개월 사용, 상태 최상',
            'battery_status': 'excellent',
            'body_only': False,
            'has_box': True,
            'has_charger': True,
            'has_earphones': False,
            'description': '업무용으로 구매했다가 개인 폰으로 통일하려고 판매합니다.',
            'meeting_place': '여의도역 5번 출구',
        },
        {
            'model': 'iPhone 13',
            'brand': 'apple',
            'storage': 128,
            'color': '미드나이트',
            'price': 650000,
            'min_offer_price': 600000,
            'accept_offers': True,
            'condition_grade': 'B',
            'condition_description': '일반 사용감 있음',
            'battery_status': 'fair',
            'body_only': True,
            'has_box': False,
            'has_charger': False,
            'has_earphones': False,
            'description': '본체만 판매합니다. 배터리 성능 78%입니다.',
            'meeting_place': '홍대입구역',
        },
        {
            'model': 'Galaxy S23',
            'brand': 'samsung',
            'storage': 256,
            'color': '라벤더',
            'price': 750000,
            'min_offer_price': 700000,
            'accept_offers': True,
            'condition_grade': 'A',
            'condition_description': '케이스 사용으로 깨끗',
            'battery_status': 'good',
            'body_only': False,
            'has_box': True,
            'has_charger': True,
            'has_earphones': False,
            'description': '자급제 제품입니다. 삼성케어+ 가입되어 있습니다.',
            'meeting_place': '성수역 2번 출구',
        },
        {
            'model': 'iPhone 12 Pro Max',
            'brand': 'apple',
            'storage': 256,
            'color': '퍼시픽 블루',
            'price': 780000,
            'min_offer_price': 750000,
            'accept_offers': True,
            'condition_grade': 'B',
            'condition_description': '뒷면 잔기스 있음',
            'battery_status': 'good',
            'body_only': False,
            'has_box': False,
            'has_charger': True,
            'has_earphones': False,
            'description': '2년 사용했습니다. 기능은 모두 정상입니다.',
            'meeting_place': '건대입구역',
        },
        {
            'model': 'Galaxy A54',
            'brand': 'samsung',
            'storage': 128,
            'color': '오썸 바이올렛',
            'price': 350000,
            'min_offer_price': 320000,
            'accept_offers': True,
            'condition_grade': 'A',
            'condition_description': '거의 새것',
            'battery_status': 'excellent',
            'body_only': False,
            'has_box': True,
            'has_charger': True,
            'has_earphones': True,
            'description': '부모님 선물용으로 구매했다가 다른 기종으로 교체해서 판매합니다.',
            'meeting_place': '잠실역 8번 출구',
        },
    ]

    created_count = 0
    for phone_data in sample_phones:
        try:
            # 중복 체크
            if UsedPhone.objects.filter(
                model=phone_data['model'],
                seller=user
            ).exists():
                print(f"이미 존재: {phone_data['model']}")
                continue

            phone = UsedPhone.objects.create(
                seller=user,
                **phone_data
            )
            
            # 가상의 이미지 정보 추가 (실제 이미지는 없음)
            # UsedPhoneImage.objects.create(
            #     phone=phone,
            #     image_url=f'https://via.placeholder.com/400x400?text={phone.model}',
            #     is_main=True,
            #     order=0
            # )
            
            created_count += 1
            print(f"생성됨: {phone.model} - {phone.price:,}원")
            
        except Exception as e:
            print(f"생성 실패 ({phone_data['model']}): {e}")
    
    print(f"\n총 {created_count}개의 중고폰 데이터가 생성되었습니다.")
    
    # 전체 개수 확인
    total = UsedPhone.objects.filter(status='active').count()
    print(f"활성 중고폰 총 {total}개")

if __name__ == '__main__':
    create_sample_phones()