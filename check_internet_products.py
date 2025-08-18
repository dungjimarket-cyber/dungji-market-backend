from api.models import Product, Category

# 인터넷 카테고리 확인
internet_cat = Category.objects.filter(detail_type='internet').first()
internet_tv_cat = Category.objects.filter(detail_type='internet_tv').first()

print(f"인터넷 카테고리: {internet_cat}")
print(f"인터넷+TV 카테고리: {internet_tv_cat}")

# 인터넷 상품 확인
internet = Product.objects.filter(category__detail_type='internet')
internet_tv = Product.objects.filter(category__detail_type='internet_tv')

print(f'\n인터넷 상품: {internet.count()}개')
for p in internet[:5]:
    print(f'  - {p.name}')
    print(f'    extra_data: {p.extra_data}')
    print(f'    category: {p.category.name if p.category else "None"}')
    print(f'    category_detail_type: {p.category.detail_type if p.category else "None"}')

print(f'\n인터넷+TV 상품: {internet_tv.count()}개')
for p in internet_tv[:5]:
    print(f'  - {p.name}')
    print(f'    extra_data: {p.extra_data}')
    print(f'    category: {p.category.name if p.category else "None"}')
    print(f'    category_detail_type: {p.category.detail_type if p.category else "None"}')