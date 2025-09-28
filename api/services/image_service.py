"""
이미지 업로드 서비스
S3 업로드 및 이미지 압축 처리
"""
import boto3
import uuid
import io
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging

logger = logging.getLogger(__name__)


class ImageService:
    """이미지 업로드 및 압축 서비스"""

    # 이미지 설정
    MAX_IMAGES = 10  # 최대 이미지 개수
    MAX_SIZE_MB = 10  # 장당 최대 크기 (MB)
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

    # 압축 설정
    MAX_WIDTH = 1920  # 최대 가로 크기
    MAX_HEIGHT = 1920  # 최대 세로 크기
    JPEG_QUALITY = 85  # JPEG 압축 품질 (1-100)
    WEBP_QUALITY = 80  # WebP 압축 품질 (1-100)

    @staticmethod
    def compress_image(image_file, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
        """
        이미지 압축

        Args:
            image_file: Django UploadedFile
            max_width: 최대 가로 크기
            max_height: 최대 세로 크기

        Returns:
            BytesIO: 압축된 이미지 데이터
            str: 파일 확장자
        """
        try:
            # PIL Image로 열기
            img = Image.open(image_file)

            # EXIF 회전 정보 적용
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # RGBA를 RGB로 변환 (JPEG는 투명도 미지원)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 리사이즈 (비율 유지)
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                logger.info(f"이미지 리사이즈: {img.width}x{img.height}")

            # BytesIO에 저장
            output = io.BytesIO()

            # WebP로 저장 (더 나은 압축률)
            img.save(
                output,
                format='WEBP',
                quality=ImageService.WEBP_QUALITY,
                method=6  # 최고 품질 압축
            )

            output.seek(0)

            logger.info(f"이미지 압축 완료: {len(output.getvalue()) / 1024:.2f}KB")

            return output, 'webp'

        except Exception as e:
            logger.error(f"이미지 압축 실패: {str(e)}")
            raise ValueError(f"이미지 압축에 실패했습니다: {str(e)}")

    @staticmethod
    def validate_image(image_file):
        """
        이미지 유효성 검사

        Args:
            image_file: Django UploadedFile

        Raises:
            ValueError: 유효하지 않은 이미지
        """
        # 파일 크기 체크
        if image_file.size > ImageService.MAX_SIZE_BYTES:
            raise ValueError(
                f'이미지 크기가 너무 큽니다. '
                f'최대 {ImageService.MAX_SIZE_MB}MB까지 업로드 가능합니다.'
            )

        # 파일 형식 체크
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            raise ValueError(
                f'지원하지 않는 이미지 형식입니다. '
                f'JPG, PNG, WebP 파일만 업로드 가능합니다.'
            )

        # PIL로 이미지 열기 시도
        try:
            img = Image.open(image_file)
            img.verify()
            image_file.seek(0)  # 파일 포인터 초기화
        except Exception as e:
            raise ValueError(f'손상된 이미지 파일입니다: {str(e)}')

    @staticmethod
    def upload_to_s3(image_file, folder='custom'):
        """
        S3에 이미지 업로드 (압축 포함)

        Args:
            image_file: Django UploadedFile
            folder: S3 폴더명 (기본: custom)

        Returns:
            str: 업로드된 이미지 URL

        Raises:
            ValueError: 유효하지 않은 이미지
            Exception: S3 업로드 실패
        """
        try:
            # 1. 이미지 유효성 검사
            ImageService.validate_image(image_file)

            # 2. 이미지 압축
            compressed_image, ext = ImageService.compress_image(image_file)

            # 3. S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2'),
            )

            # 4. 파일명 생성 (UUID + 확장자)
            file_name = f"{folder}/{uuid.uuid4()}.{ext}"

            # 5. S3 업로드
            s3_client.upload_fileobj(
                compressed_image,
                settings.AWS_STORAGE_BUCKET_NAME,
                file_name,
                ExtraArgs={
                    'ContentType': f'image/{ext}',
                    'ACL': 'public-read',
                    'CacheControl': 'max-age=31536000',  # 1년 캐시
                }
            )

            # 6. URL 생성
            if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
                url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"
            else:
                url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2')}.amazonaws.com/{file_name}"

            logger.info(f"이미지 업로드 완료: {url}")

            return url

        except ValueError as e:
            # 유효성 검사 실패
            logger.warning(f"이미지 유효성 검사 실패: {str(e)}")
            raise

        except Exception as e:
            # S3 업로드 실패
            logger.error(f"S3 업로드 실패: {str(e)}")
            raise Exception(f"이미지 업로드에 실패했습니다: {str(e)}")

    @staticmethod
    def upload_multiple_images(image_files, folder='custom', max_images=MAX_IMAGES):
        """
        여러 이미지 일괄 업로드

        Args:
            image_files: List[Django UploadedFile]
            folder: S3 폴더명
            max_images: 최대 이미지 개수

        Returns:
            List[str]: 업로드된 이미지 URL 리스트

        Raises:
            ValueError: 이미지 개수 초과 또는 유효하지 않은 이미지
        """
        if len(image_files) > max_images:
            raise ValueError(f'최대 {max_images}장까지 업로드 가능합니다.')

        uploaded_urls = []
        failed_count = 0

        for idx, image_file in enumerate(image_files):
            try:
                url = ImageService.upload_to_s3(image_file, folder)
                uploaded_urls.append(url)
                logger.info(f"이미지 {idx + 1}/{len(image_files)} 업로드 완료")

            except Exception as e:
                failed_count += 1
                logger.error(f"이미지 {idx + 1} 업로드 실패: {str(e)}")

                # 일부 실패해도 계속 진행
                if failed_count >= len(image_files) / 2:
                    # 50% 이상 실패 시 중단
                    raise Exception(f"이미지 업로드 실패가 너무 많습니다. ({failed_count}/{len(image_files)})")

        if failed_count > 0:
            logger.warning(f"일부 이미지 업로드 실패: {failed_count}/{len(image_files)}")

        return uploaded_urls

    @staticmethod
    def delete_from_s3(image_url):
        """
        S3에서 이미지 삭제

        Args:
            image_url: 삭제할 이미지 URL

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # URL에서 파일명 추출
            if 'amazonaws.com/' in image_url:
                file_name = image_url.split('amazonaws.com/')[-1]
            elif hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN in image_url:
                file_name = image_url.split(f"{settings.AWS_S3_CUSTOM_DOMAIN}/")[-1]
            else:
                logger.warning(f"잘못된 S3 URL 형식: {image_url}")
                return False

            # S3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2'),
            )

            # 삭제
            s3_client.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=file_name
            )

            logger.info(f"이미지 삭제 완료: {file_name}")
            return True

        except Exception as e:
            logger.error(f"이미지 삭제 실패: {str(e)}")
            return False