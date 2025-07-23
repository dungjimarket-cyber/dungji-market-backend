#!/usr/bin/env python
import os
import django

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from api.models import Product, Category
import requests

print("=" * 50)
print("Admin에서 상품 생성 시뮬레이션")
print("=" * 50)

# 설정 확인
print(f"\n[Django Settings]")
print(f"USE_S3: {settings.USE_S3}")
print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")

# 카테고리 가져오기
category = Category.objects.first()

# 테스트 이미지 생성
print("\n테스트 이미지 생성 중...")
# 간단한 PNG 이미지 바이트 (1x1 픽셀 투명 PNG)
image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x00\x00\x00IEND\xaeB`\x82'

# SimpleUploadedFile 생성 (Django admin에서 업로드하는 것과 동일)
uploaded_file = SimpleUploadedFile(
    name='test_admin_product.png',
    content=image_content,
    content_type='image/png'
)

# Product 생성
print("\n상품 생성 중...")
product = Product(
    name="테스트 상품 - Admin 시뮬레이션",
    slug="test-product-admin-sim",
    description="Admin에서 생성한 것처럼 시뮬레이션",
    category=category,
    product_type='device',
    base_price=20000
)

# 이미지 할당
product.image = uploaded_file

# 저장
product.save()

print(f"\n저장 완료!")
print(f"Product ID: {product.id}")
print(f"Product 이미지 필드: {product.image}")
print(f"Product 이미지 URL: {product.image.url if product.image else 'None'}")

# Serializer 테스트
from api.serializers import ProductSerializer
serializer = ProductSerializer(product)
data = serializer.data
print(f"\nSerializer data:")
print(f"image: {data.get('image')}")
print(f"image_url: {data.get('image_url')}")