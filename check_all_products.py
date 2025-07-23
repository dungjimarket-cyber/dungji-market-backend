#!/usr/bin/env python
import os
import django

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import Product
from api.serializers import ProductSerializer

# 모든 상품 확인
products = Product.objects.all().order_by('-id')[:5]

print("최근 생성된 상품 5개:")
print("=" * 50)

for product in products:
    print(f"\nID: {product.id}")
    print(f"이름: {product.name}")
    print(f"이미지 필드: {product.image}")
    print(f"이미지 URL 필드: {product.image_url}")
    
    if product.image:
        print(f"실제 이미지 URL: {product.image.url}")
    
    # Serializer 출력
    serializer = ProductSerializer(product)
    data = serializer.data
    print(f"Serializer image: {data.get('image')}")
    print(f"Serializer image_url: {data.get('image_url')}")
    print("-" * 30)