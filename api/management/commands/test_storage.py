from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '현재 스토리지 백엔드 확인'

    def handle(self, *args, **options):
        self.stdout.write("=" * 50)
        self.stdout.write("스토리지 설정 디버깅")
        self.stdout.write("=" * 50)
        
        # 설정 확인
        self.stdout.write(f"\nUSE_S3: {settings.USE_S3}")
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        
        # INSTALLED_APPS 확인
        if 'storages' in settings.INSTALLED_APPS:
            self.stdout.write("✅ 'storages' 앱이 INSTALLED_APPS에 있습니다.")
        else:
            self.stdout.write("❌ 'storages' 앱이 INSTALLED_APPS에 없습니다!")
        
        # default_storage 확인
        self.stdout.write(f"\ndefault_storage 클래스: {default_storage.__class__}")
        self.stdout.write(f"default_storage 모듈: {default_storage.__class__.__module__}")
        
        # AWS 설정 확인
        if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
            self.stdout.write(f"\nAWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
            self.stdout.write(f"AWS_ACCESS_KEY_ID 설정됨: {'예' if settings.AWS_ACCESS_KEY_ID else '아니오'}")
            self.stdout.write(f"AWS_SECRET_ACCESS_KEY 설정됨: {'예' if settings.AWS_SECRET_ACCESS_KEY else '아니오'}")
        else:
            self.stdout.write("\n❌ AWS 설정이 없습니다!")
        
        # 실제 import 테스트
        try:
            from api.storage_backends import MediaStorage
            self.stdout.write("\n✅ MediaStorage 클래스 import 성공")
            
            # 인스턴스 생성 테스트
            try:
                storage = MediaStorage()
                self.stdout.write(f"✅ MediaStorage 인스턴스 생성 성공")
                self.stdout.write(f"   버킷명: {storage.bucket_name if hasattr(storage, 'bucket_name') else 'Unknown'}")
            except Exception as e:
                self.stdout.write(f"❌ MediaStorage 인스턴스 생성 실패: {str(e)}")
                
        except Exception as e:
            self.stdout.write(f"\n❌ MediaStorage import 실패: {str(e)}")