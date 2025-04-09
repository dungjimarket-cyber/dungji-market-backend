import os
import django
import random
from datetime import datetime, timedelta

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import Product, GroupBuy

# 통신사 선택지
carriers = ['SKT', 'KT', 'LGU', 'MVNO']

# 등록 유형 선택지
registration_types = ['MNP', 'NEW', 'CHANGE']

# 요금제 정보 선택지
plan_infos = [
    '5G 프리미엄 요금제', 
    '5G 스탠다드 요금제', 
    '5G 라이트 요금제',
    '4G 무제한 요금제',
    '4G 데이터 중심 요금제',
    '알뜰 요금제'
]

# 계약 정보 선택지
contract_infos = [
    '24개월 약정',
    '36개월 약정',
    '12개월 약정',
    '무약정'
]

# 출시일 범위
start_date = datetime(2023, 1, 1)
end_date = datetime(2025, 3, 1)

def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)

def update_products():
    products = Product.objects.all()
    
    print(f"총 {products.count()}개의 제품 데이터를 업데이트합니다.")
    
    for product in products:
        # 카테고리 이름 설정
        if not product.category_name and product.category:
            product.category_name = product.category.name
        
        # 통신사 설정
        if not product.carrier:
            product.carrier = random.choice(carriers)
        
        # 등록 유형 설정
        if not product.registration_type:
            product.registration_type = random.choice(registration_types)
        
        # 요금제 정보 설정
        if not product.plan_info:
            product.plan_info = random.choice(plan_infos)
        
        # 계약 정보 설정
        if not product.contract_info:
            product.contract_info = random.choice(contract_infos)
        
        # 총 지원금 설정 (출고가의 10~40% 사이)
        if not product.total_support_amount:
            product.total_support_amount = int(product.base_price * random.uniform(0.1, 0.4))
        
        # 출시일 설정
        if not product.release_date:
            product.release_date = random_date(start_date, end_date).date()
        
        product.save()
        print(f"제품 '{product.name}' 업데이트 완료")

def update_groupbuys():
    groupbuys = GroupBuy.objects.all()
    
    print(f"총 {groupbuys.count()}개의 공동구매 데이터를 업데이트합니다.")
    
    for groupbuy in groupbuys:
        # 제품 이름 백업
        if not groupbuy.product_name and groupbuy.product:
            groupbuy.product_name = groupbuy.product.name
            groupbuy.save()
            print(f"공동구매 '{groupbuy.title}' 업데이트 완료")

if __name__ == "__main__":
    print("샘플 데이터 업데이트를 시작합니다...")
    update_products()
    update_groupbuys()
    print("샘플 데이터 업데이트가 완료되었습니다.")
