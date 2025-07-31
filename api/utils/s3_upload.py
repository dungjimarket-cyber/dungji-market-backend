import boto3
import os
import uuid
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def upload_to_s3(file_field, folder_name='uploads'):
    """파일을 S3에 업로드하고 URL을 반환"""
    if not settings.USE_S3:
        return None
        
    try:
        # S3 클라이언트 초기화
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # 파일 이름 생성
        ext = file_field.name.split('.')[-1]
        file_name = f"{folder_name}/{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        
        # S3에 업로드
        s3_client.upload_fileobj(
            file_field,
            settings.AWS_STORAGE_BUCKET_NAME,
            file_name,
            ExtraArgs={
                'ACL': 'public-read',
                'ContentType': file_field.content_type if hasattr(file_field, 'content_type') else 'application/octet-stream'
            }
        )
        
        # URL 생성
        url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_name}"
        logger.info(f"File uploaded to S3: {url}")
        
        return url
        
    except Exception as e:
        logger.error(f"S3 upload error: {str(e)}")
        return None