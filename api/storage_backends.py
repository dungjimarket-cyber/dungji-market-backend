from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import logging
import os

logger = logging.getLogger(__name__)

class MediaStorage(S3Boto3Storage):
    """S3 미디어 파일 스토리지 백엔드"""
    location = 'media'
    file_overwrite = False
    # ACL 설정 제거 (S3 버킷이 ACL을 지원하지 않는 경우)
    default_acl = None
    object_parameters = {'CacheControl': 'max-age=86400'}

    def __init__(self, *args, **kwargs):
        # S3 버킷 이름이 설정되어 있는지 확인
        bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
        if not bucket_name:
            logger.error("AWS_STORAGE_BUCKET_NAME 환경변수가 설정되지 않았습니다.")
            logger.error("현재 환경변수 목록:")
            for key, value in os.environ.items():
                if 'AWS' in key or 'S3' in key:
                    logger.error(f"  {key} = {value}")
            raise ValueError("AWS_STORAGE_BUCKET_NAME이 설정되지 않았습니다. .env 파일을 확인해주세요.")

        super().__init__(*args, **kwargs)
        logger.info(f"MediaStorage 초기화: bucket={self.bucket_name}, location={self.location}")

    def _save(self, name, content):
        """파일 저장 시 로깅 추가"""
        logger.info(f"S3에 파일 저장 시작: {name}")
        result = super()._save(name, content)
        logger.info(f"S3에 파일 저장 완료: {result}")
        return result

    def url(self, name):
        """파일 URL 반환 - 버킷 설정 확인"""
        try:
            if not self.bucket_name:
                logger.error(f"버킷 이름이 설정되지 않아 URL을 생성할 수 없습니다: {name}")
                return f"/media/{name}"  # 로컬 URL로 폴백
            return super().url(name)
        except Exception as e:
            logger.error(f"S3 URL 생성 중 오류 발생: {e}, 파일명: {name}")
            return f"/media/{name}"  # 로컬 URL로 폴백