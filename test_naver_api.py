import requests
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID', '94jb615v38')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', 'w4d0lOz6oxGwC6xj038t7Lzj5OvPCwUWZSRThvGM')

# 네이버 쇼핑 검색 API 테스트
url = "https://openapi.naver.com/v1/search/shop.json"
params = {
    "query": "아이폰",
    "display": 5,
    "sort": "asc"  # 가격 낮은순
}
headers = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
}

print("=" * 60)
print("네이버 쇼핑 API 테스트")
print("=" * 60)
print(f"Client ID: {NAVER_CLIENT_ID}")
print(f"검색어: {params['query']}")
print()

try:
    response = requests.get(url, params=params, headers=headers)
    print(f"응답 상태 코드: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✅ API 호출 성공!")
        print(f"총 검색 결과: {data.get('total', 0)}개")
        print(f"표시된 결과: {len(data.get('items', []))}개")
        print()

        if data.get('items'):
            print("=" * 60)
            print("첫 5개 상품 (가격 낮은순):")
            print("=" * 60)
            for idx, item in enumerate(data['items'], 1):
                print(f"\n{idx}. {item['title']}")
                print(f"   가격: {item['lprice']:,}원")
                print(f"   최저가: {item.get('lprice', 0):,}원 | 최고가: {item.get('hprice', 0):,}원")
                print(f"   쇼핑몰: {item.get('mallName', 'N/A')}")
                print(f"   링크: {item['link'][:80]}...")
        print()
        print("=" * 60)
        print("결론: 현재 API 키로 쇼핑 검색 가능! ✅")
        print("=" * 60)

    else:
        print("❌ API 호출 실패")
        print(f"응답 내용: {response.text}")

except Exception as e:
    print(f"❌ 에러 발생: {e}")
