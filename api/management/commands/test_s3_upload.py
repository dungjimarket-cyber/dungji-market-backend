from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'S3 업로드 설정 테스트'

    def handle(self, *args, **options):
        self.stdout.write("S3 설정 테스트 시작...\n")
        
        # 1. 설정 확인
        self.stdout.write(f"USE_S3: {getattr(settings, 'USE_S3', False)}")
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
        self.stdout.write(f"AWS_STORAGE_BUCKET_NAME: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')}")
        self.stdout.write(f"AWS_S3_REGION_NAME: {getattr(settings, 'AWS_S3_REGION_NAME', 'Not set')}")
        
        # 2. S3 연결 테스트
        try:
            storage = S3Boto3Storage()
            self.stdout.write(f"\n스토리지 백엔드: {storage.__class__.__name__}")
            self.stdout.write(f"버킷명: {storage.bucket_name}")
            self.stdout.write(f"위치: {storage.location}")
            
            # 3. 테스트 파일 업로드
            test_content = b"This is a test file for S3 upload"
            test_file = ContentFile(test_content, name='test_s3_upload.txt')
            
            saved_name = storage.save('test/test_s3_upload.txt', test_file)
            self.stdout.write(self.style.SUCCESS(f"\n테스트 파일 업로드 성공: {saved_name}"))
            
            # 4. URL 확인
            file_url = storage.url(saved_name)
            self.stdout.write(f"파일 URL: {file_url}")
            
            # 5. 파일 삭제
            storage.delete(saved_name)
            self.stdout.write(self.style.SUCCESS("테스트 파일 삭제 완료"))
            
            self.stdout.write(self.style.SUCCESS("\n✅ S3 설정이 올바르게 구성되어 있습니다!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ S3 테스트 실패: {str(e)}"))
            self.stdout.write("\n가능한 원인:")
            self.stdout.write("1. AWS 자격 증명이 올바르지 않음")
            self.stdout.write("2. S3 버킷이 존재하지 않거나 접근 권한이 없음")
            self.stdout.write("3. django-storages가 설치되지 않음")