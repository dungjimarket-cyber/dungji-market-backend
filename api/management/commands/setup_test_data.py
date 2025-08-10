from django.core.management.base import BaseCommand
from api.models import Category, Product

class Command(BaseCommand):
    help = 'Setup initial test data'

    def handle(self, *args, **kwargs):
        # Create electronics category
        electronics, created = Category.objects.get_or_create(
            name="전자기기",
            defaults={"detail_type": "electronics"}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created electronics category'))
        
        # Create sample products
        products = [
            {
                "name": "아이폰 15",
                "description": "최신 아이폰",
                "price": 1200000,
                "category": electronics
            },
            {
                "name": "갤럭시 S24",
                "description": "삼성 최신 스마트폰",
                "price": 1100000,
                "category": electronics
            },
            {
                "name": "맥북 프로",
                "description": "Apple 노트북",
                "price": 2500000,
                "category": electronics
            }
        ]
        
        for product_data in products:
            product, created = Product.objects.get_or_create(
                name=product_data["name"],
                defaults={
                    "description": product_data["description"],
                    "price": product_data["price"],
                    "category": product_data["category"]
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created product {product.name}')
                )
