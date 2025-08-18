from api.models import Product

phones = Product.objects.filter(category__name='휴대폰')
print(f'휴대폰 상품 총 {phones.count()}개:')
for p in phones[:10]:
    print(f'  - {p.name}')

print('\n통신사 관련 카테고리 확인:')
from api.models import Category
for cat in Category.objects.filter(name__contains='통신'):
    print(f'  - {cat.name} (detail_type: {cat.detail_type})')