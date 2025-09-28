"""
커스텀 특가 이미지 업로드 API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from api.services.image_service import ImageService
import logging

logger = logging.getLogger(__name__)


class CustomImageUploadView(APIView):
    """커스텀 특가 이미지 업로드 API"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        이미지 업로드

        Request:
            - images: 이미지 파일 리스트 (최대 10장)

        Response:
            {
                "success": true,
                "urls": ["https://...", "https://..."],
                "count": 2
            }
        """
        try:
            # 이미지 파일 가져오기
            image_files = request.FILES.getlist('images')

            if not image_files:
                return Response(
                    {'error': '이미지 파일이 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 개수 체크
            if len(image_files) > ImageService.MAX_IMAGES:
                return Response(
                    {'error': f'최대 {ImageService.MAX_IMAGES}장까지 업로드 가능합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3 업로드 (압축 포함)
            uploaded_urls = ImageService.upload_multiple_images(
                image_files,
                folder='custom'
            )

            return Response({
                'success': True,
                'urls': uploaded_urls,
                'count': len(uploaded_urls)
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            # 유효성 검사 실패
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # 서버 오류
            logger.error(f"이미지 업로드 오류: {str(e)}")
            return Response(
                {'error': '이미지 업로드 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomImageDeleteView(APIView):
    """커스텀 특가 이미지 삭제 API"""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        이미지 삭제

        Request:
            {
                "url": "https://s3.amazonaws.com/..."
            }

        Response:
            {
                "success": true,
                "message": "이미지가 삭제되었습니다."
            }
        """
        try:
            image_url = request.data.get('url')

            if not image_url:
                return Response(
                    {'error': '삭제할 이미지 URL이 필요합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # S3에서 삭제
            success = ImageService.delete_from_s3(image_url)

            if success:
                return Response({
                    'success': True,
                    'message': '이미지가 삭제되었습니다.'
                })
            else:
                return Response(
                    {'error': '이미지 삭제에 실패했습니다.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"이미지 삭제 오류: {str(e)}")
            return Response(
                {'error': '이미지 삭제 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )