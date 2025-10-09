from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from api.services.link_preview_service import LinkPreviewService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_link_preview(request):
    """
    링크 미리보기 메타데이터 추출 API

    Query Parameters:
        url (str): 미리보기를 추출할 URL

    Returns:
        200: {
            'title': str,
            'description': str,
            'image': str,
            'url': str
        }
        400: {'error': str}
    """
    url = request.GET.get('url')

    if not url:
        return Response(
            {'error': 'URL 파라미터가 필요합니다'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # URL 유효성 간단 체크
    if not url.startswith(('http://', 'https://')):
        return Response(
            {'error': '올바른 URL 형식이 아닙니다 (http:// 또는 https://로 시작해야 합니다)'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        metadata = LinkPreviewService.extract_metadata(url)

        # error 키가 있어도 200 OK 반환 (링크 자체는 유효하므로)
        # warning 키로 변경되었으므로 항상 200 OK
        return Response(metadata, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f'Link preview API error: {str(e)}')
        # 예외 발생해도 빈 메타데이터 반환 (등록은 계속 진행)
        return Response(
            {
                'title': '',
                'description': '',
                'image': '',
                'url': url,
                'warning': '미리보기 생성 실패'
            },
            status=status.HTTP_200_OK
        )