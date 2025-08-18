from api.models import Category, Product

# 인터넷 카테고리 생성
internet_category, created = Category.objects.get_or_create(
    name='인터넷',
    defaults={
        'slug': 'internet',
        'detail_type': 'internet',
        'is_service': True
    }
)
print(f"인터넷 카테고리: {'생성됨' if created else '이미 존재'}")

# 인터넷+TV 카테고리 생성
internet_tv_category, created = Category.objects.get_or_create(
    name='인터넷+TV',
    defaults={
        'slug': 'internet-tv',
        'detail_type': 'internet_tv',
        'is_service': True
    }
)
print(f"인터넷+TV 카테고리: {'생성됨' if created else '이미 존재'}")

# 인터넷 상품 생성
products_data = [
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
    }
]

for product_data in products_data:
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
    print(f"{product.name}: {'생성됨' if created else '이미 존재'}")

print("\n인터넷 카테고리 및 상품 생성 완료!")