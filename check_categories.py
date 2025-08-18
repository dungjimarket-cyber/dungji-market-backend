from api.models import Product, Category

print('카테고리별 상품 수:')
for cat in Category.objects.all():
    count = Product.objects.filter(category=cat).count()
    if count > 0:
        print(f'{cat.name}: {count}개 (detail_type: {cat.detail_type})')

print('\n휴대폰/통신사 관련 상품:')
for p in Product.objects.all()[:10]:
    print(f'- {p.name} | 카테고리: {p.category_name} | detail_type: {p.category.detail_type if p.category else "None"}')