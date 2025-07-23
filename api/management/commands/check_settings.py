from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = '현재 Django 설정을 확인합니다'

    def handle(self, *args, **options):
        self.stdout.write("=" * 50)
        self.stdout.write("Django 설정 확인")
        self.stdout.write("=" * 50)
        
        # 환경 변수 직접 확인
        self.stdout.write("\n[환경 변수 직접 확인]")
        self.stdout.write(f"os.getenv('USE_S3'): {os.getenv('USE_S3')}")
        self.stdout.write(f"os.getenv('USE_S3', 'False'): {os.getenv('USE_S3', 'False')}")
        self.stdout.write(f"os.getenv('USE_S3', 'False') == 'True': {os.getenv('USE_S3', 'False') == 'True'}")
        
        # Django settings 확인
        self.stdout.write("\n[Django Settings]")
        self.stdout.write(f"settings.USE_S3: {settings.USE_S3}")
        self.stdout.write(f"settings.DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        self.stdout.write(f"settings.AWS_STORAGE_BUCKET_NAME: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')}")
        self.stdout.write(f"settings.AWS_S3_REGION_NAME: {getattr(settings, 'AWS_S3_REGION_NAME', 'Not set')}")
        self.stdout.write(f"settings.DEBUG: {settings.DEBUG}")
        
        # INSTALLED_APPS 확인
        self.stdout.write("\n[INSTALLED_APPS에서 storages 확인]")
        if 'storages' in settings.INSTALLED_APPS:
            self.stdout.write("✅ 'storages' 앱이 설치되어 있습니다.")
        else:
            self.stdout.write("❌ 'storages' 앱이 설치되어 있지 않습니다.")
        
        # Storage 백엔드 확인
        self.stdout.write("\n[Storage Backend 확인]")
        from django.core.files.storage import default_storage
        self.stdout.write(f"default_storage 클래스: {default_storage.__class__}")
        self.stdout.write(f"default_storage 모듈: {default_storage.__class__.__module__}")
        
        if hasattr(default_storage, 'bucket_name'):
            self.stdout.write(f"bucket_name: {default_storage.bucket_name}")
        
        # Product 모델에서 ImageField 스토리지 확인
        self.stdout.write("\n[Product 모델 ImageField 스토리지]")
        from api.models import Product
        image_field = Product._meta.get_field('image')
        self.stdout.write(f"Product.image.storage: {image_field.storage}")
        if hasattr(image_field.storage, 'bucket_name'):
            self.stdout.write(f"Product.image.storage.bucket_name: {image_field.storage.bucket_name}")