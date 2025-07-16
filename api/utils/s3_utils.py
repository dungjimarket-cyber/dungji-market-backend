import os
import uuid
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone

def get_s3_client():
    """
    S3 클라이언트 객체를 반환합니다.
    """
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

def upload_file_to_s3(file_obj, folder='products'):
    """
    파일을 S3에 업로드하고 URL을 반환합니다.
    
    Args:
        file_obj: 업로드할 파일 객체
        folder: S3 버킷 내 저장할 폴더 경로
        
    Returns:
        str: 업로드된 파일의 URL
    """
    if not settings.USE_S3:
        # S3가 비활성화된 경우 로컬 파일 경로 반환
        # 실제 구현에서는 로컬 파일 저장 로직 추가 필요
        return None
    
    # 파일 확장자 추출
    _, file_extension = os.path.splitext(file_obj.name)
    
    # 고유한 파일명 생성 (UUID + 타임스탬프)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{uuid.uuid4().hex}_{timestamp}{file_extension}"
    
    # S3 경로 설정
    s3_path = f"{folder}/{unique_filename}"
    
    try:
        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            file_obj,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_path,
            ExtraArgs={
                'ContentType': file_obj.content_type,
            }
        )
        
        # 업로드된 파일의 URL 생성
        file_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_path}"
        return file_url
    
    except ClientError as e:
        print(f"S3 업로드 오류: {e}")
        return None
    except Exception as e:
        print(f"파일 업로드 중 예상치 못한 오류 발생: {e}")
        return None

def delete_file_from_s3(file_url):
    """
    S3에서 파일을 삭제합니다.
    
    Args:
        file_url: 삭제할 파일의 URL
        
    Returns:
        bool: 삭제 성공 여부
    """
    if not settings.USE_S3 or not file_url:
        return False
    
    try:
        # URL에서 S3 키 추출
        if settings.AWS_S3_CUSTOM_DOMAIN in file_url:
            s3_key = file_url.split(settings.AWS_S3_CUSTOM_DOMAIN + '/')[-1]
        else:
            return False
        
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key
        )
        return True
    
    except ClientError as e:
        print(f"S3 파일 삭제 오류: {e}")
        return False
    except Exception as e:
        print(f"파일 삭제 중 예상치 못한 오류 발생: {e}")
        return False
