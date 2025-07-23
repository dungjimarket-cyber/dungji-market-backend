#!/usr/bin/env python
import os
import django

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models import Product

# ID 16 상품 확인
product = Product.objects.get(id=16)
print(f"Product: {product.name}")
print(f"Image field: {product.image}")
print(f"Image name: {product.image.name if product.image else 'None'}")
print(f"Image URL: {product.image.url if product.image else 'None'}")
print(f"Image storage: {product.image.storage if product.image else 'None'}")

# Serializer 테스트
from api.serializers import ProductSerializer
serializer = ProductSerializer(product)
data = serializer.data
print(f"\nSerializer data:")
print(f"image: {data.get('image')}")
print(f"image_url: {data.get('image_url')}")