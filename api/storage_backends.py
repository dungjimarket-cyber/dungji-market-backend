from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import logging

logger = logging.getLogger(__name__)

class MediaStorage(S3Boto3Storage):
    """S3 미디어 파일 스토리지 백엔드"""
    location = 'media'
    file_overwrite = False
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"MediaStorage 초기화: bucket={self.bucket_name}, location={self.location}")
    
    def _save(self, name, content):
        """파일 저장 시 로깅 추가"""
        logger.info(f"S3에 파일 저장 시작: {name}")
        result = super()._save(name, content)
        logger.info(f"S3에 파일 저장 완료: {result}")
        return result
    
    def url(self, name):
        """파일 URL 반환"""
        # 로깅 비활성화 - 너무 많은 로그 생성 방지
        # logger.info(f"S3 파일 URL: {name} -> {url}")
        return super().url(name)