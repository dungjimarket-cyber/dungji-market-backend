#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market.settings')
django.setup()

from api.models import Category, Product
import json

def create_internet_categories_and_products():
    # 인터넷 카테고리 생성
    internet_category, created = Category.objects.get_or_create(
        name='인터넷',
        defaults={
            'slug': 'internet',
            'detail_type': 'internet',
            'is_service': True
        }
    )
    if created:
        print(f"Created category: {internet_category.name}")
    else:
        print(f"Category already exists: {internet_category.name}")

    # 인터넷+TV 카테고리 생성
    internet_tv_category, created = Category.objects.get_or_create(
        name='인터넷+TV',
        defaults={
            'slug': 'internet-tv',
            'detail_type': 'internet_tv',
            'is_service': True
        }
    )
    if created:
        print(f"Created category: {internet_tv_category.name}")
    else:
        print(f"Category already exists: {internet_tv_category.name}")

    # 인터넷 상품 생성
    internet_products = [
        {
            'name': 'KT 1G 신규',
            'category': internet_category,
            'base_price': 35000,
            'extra_data': {
                'carrier': 'KT',
                'speed': '1G',
                'subscription_type': 'new',
                'monthly_fee': '35000',
                'installation_fee': '30000'
            }
        },
        {
            'name': 'SK브로드밴드 500M 신규',
            'category': internet_category,
            'base_price': 29000,
            'extra_data': {
                'carrier': 'SK',
                'speed': '500M',
                'subscription_type': 'new',
                'monthly_fee': '29000',
                'installation_fee': '30000'
            }
        },
        {
            'name': 'LG U+ 2.5G 통신사이동',
            'category': internet_category,
            'base_price': 45000,
            'extra_data': {
                'carrier': 'LGU',
                'speed': '2.5G',
                'subscription_type': 'transfer',
                'monthly_fee': '45000',
                'installation_fee': '0'
            }
        }
    ]

    # 인터넷+TV 상품 생성
    internet_tv_products = [
        {
            'name': 'KT 1G + TV 베이직 신규',
            'category': internet_tv_category,
            'base_price': 55000,
            'extra_data': {
                'carrier': 'KT',
                'speed': '1G',
                'subscription_type': 'new',
                'monthly_fee': '55000',
                'installation_fee': '30000',
                'has_tv': True,
                'tv_channels': '기본 100채널'
            }
        },
        {
            'name': 'SK브로드밴드 500M + B tv 신규',
            'category': internet_tv_category,
            'base_price': 49000,
            'extra_data': {
                'carrier': 'SK',
                'speed': '500M',
                'subscription_type': 'new',
                'monthly_fee': '49000',
                'installation_fee': '30000',
                'has_tv': True,
                'tv_channels': '기본 150채널 + 프리미엄 20채널'
            }
        }
    ]

    # 모든 상품 생성
    all_products = internet_products + internet_tv_products
    
    for product_data in all_products:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            category=product_data['category'],
            defaults={
                'slug': product_data['name'].lower().replace(' ', '-').replace('+', '-'),
                'description': f"{product_data['name']} 상품입니다.",
                'category_name': product_data['category'].name,
                'product_type': 'service',
                'base_price': product_data['base_price'],
                'is_available': True,
                'attributes': {},
                'extra_data': product_data['extra_data']
            }
        )
        if created:
            print(f"Created product: {product.name}")
        else:
            print(f"Product already exists: {product.name}")

if __name__ == '__main__':
    create_internet_categories_and_products()
    print("\n인터넷 카테고리 및 상품 생성 완료!")