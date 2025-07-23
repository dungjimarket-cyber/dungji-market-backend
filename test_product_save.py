#!/usr/bin/env python
import os
import django

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from api.models import Product, Category

print("=" * 50)
print("Product 모델 이미지 저장 테스트")
print("=" * 50)

# 설정 확인
print(f"\n[Django Settings]")
print(f"USE_S3: {settings.USE_S3}")
print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
print(f"AWS_STORAGE_BUCKET_NAME: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')}")

# 카테고리 가져오기 또는 생성
category = Category.objects.first()
if not category:
    print("\n카테고리가 없어서 테스트 카테고리를 생성합니다...")
    category = Category.objects.create(
        name="테스트 카테고리",
        detail_type="standard"
    )

# 테스트 상품 생성
print(f"\n테스트 상품을 생성합니다...")
test_content = b"test image content"
test_file = ContentFile(test_content, name='test_product_image.jpg')

product = Product(
    name="테스트 상품 - Shell",
    slug="test-product-shell",
    description="Django shell에서 생성한 테스트 상품",
    category=category,
    product_type='device',
    base_price=10000
)

# 이미지 할당
product.image = test_file

# 저장
print("\n상품 저장 중...")
product.save()

print(f"\n저장 완료!")
print(f"Product ID: {product.id}")
print(f"Product 이미지 필드: {product.image}")
print(f"Product 이미지 URL: {product.image.url if product.image else 'None'}")