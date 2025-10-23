from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
import os

@api_view(['GET'])
@permission_classes([AllowAny])
def test_naver_shopping_api(request):
    """네이버 쇼핑 API 테스트"""

    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID', '94jb615v38')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', 'w4d0lOz6oxGwC6xj038t7Lzj5OvPCwUWZSRThvGM')

    query = request.GET.get('query', '아이폰')

    try:
        url = "https://openapi.naver.com/v1/search/shop.json"
        params = {
            "query": query,
            "display": 5,
            "sort": "asc"  # 가격 낮은순
        }
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # 결과 포맷팅
            result = {
                'success': True,
                'total_count': data.get('total', 0),
                'displayed_count': len(data.get('items', [])),
                'products': []
            }

            for item in data.get('items', []):
                result['products'].append({
                    'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                    'price': item.get('lprice', 0),
                    'mall_name': item.get('mallName', 'N/A'),
                    'link': item.get('link', ''),
                    'image': item.get('image', ''),
                })

            return Response(result)
        else:
            return Response({
                'success': False,
                'error': f'API 호출 실패: {response.status_code}',
                'detail': response.text
            }, status=response.status_code)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
