"""
네이버 쇼핑 검색 API
"""
import os
import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
def search_shopping(request):
    """
    네이버 쇼핑 검색 API

    Query Parameters:
        query (str): 검색어 (필수)
        display (int): 검색 결과 개수 (기본값: 10, 최대: 100)
        start (int): 검색 시작 위치 (기본값: 1)
        sort (str): 정렬 방법 (sim: 정확도순, date: 날짜순, asc: 가격낮은순, dsc: 가격높은순)

    Returns:
        {
            "success": true,
            "total": 683811,
            "start": 1,
            "display": 10,
            "items": [
                {
                    "title": "상품명",
                    "link": "상품 링크",
                    "image": "이미지 URL",
                    "lprice": "최저가",
                    "hprice": "최고가",
                    "mallName": "쇼핑몰명",
                    "productId": "상품ID",
                    "productType": "상품 타입",
                    "brand": "브랜드",
                    "maker": "제조사",
                    "category1": "카테고리1",
                    "category2": "카테고리2",
                    "category3": "카테고리3",
                    "category4": "카테고리4"
                }
            ]
        }
    """
    # 검색어 확인
    query = request.GET.get('query')
    if not query:
        return Response({
            'success': False,
            'error': '검색어를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 파라미터 설정
    display = request.GET.get('display', '10')
    start = request.GET.get('start', '1')
    sort_order = request.GET.get('sort', 'sim')  # sim(정확도), date(날짜), asc(가격낮은순), dsc(가격높은순)

    try:
        display = int(display)
        start = int(start)

        # 범위 제한
        if display < 1 or display > 100:
            display = 10
        if start < 1:
            start = 1

    except ValueError:
        display = 10
        start = 1

    # 네이버 쇼핑 검색 API 인증 정보
    client_id = 'NlUGvThlg3C4nzaKRE8a'
    client_secret = 'ZYPZHopqG3'

    # 네이버 쇼핑 검색 API 호출
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort_order
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # HTML 태그 제거 (title에 <b> 태그가 포함될 수 있음)
            import re
            for item in data.get('items', []):
                if 'title' in item:
                    item['title'] = re.sub(r'<[^>]+>', '', item['title'])

            return Response({
                'success': True,
                'total': data.get('total', 0),
                'start': data.get('start', 1),
                'display': data.get('display', 0),
                'items': data.get('items', [])
            })
        else:
            return Response({
                'success': False,
                'error': f'네이버 API 오류: {response.status_code}',
                'detail': response.text
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.Timeout:
        return Response({
            'success': False,
            'error': '네이버 API 응답 시간 초과'
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)

    except Exception as e:
        return Response({
            'success': False,
            'error': f'API 호출 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
