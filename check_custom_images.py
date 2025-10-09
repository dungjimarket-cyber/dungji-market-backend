#!/usr/bin/env python
"""
커스텀 공구 이미지 확인 스크립트
"""
import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from api.models_custom import CustomGroupBuy, CustomGroupBuyImage

def main():
    print('=' * 100)
    print('커스텀 공구 이미지 확인')
    print('=' * 100)
    print()

    # 최근 등록된 공구 5개
    recent = CustomGroupBuy.objects.select_related('seller').prefetch_related('images').order_by('-id')[:5]

    print(f'📊 최근 등록된 커스텀 공구 {recent.count()}개\n')

    for gb in recent:
        print(f'🆔 ID: {gb.id}')
        print(f'📝 제목: {gb.title[:50]}')
        print(f'👤 판매자: {gb.seller.username if gb.seller else "N/A"}')
        print(f'📅 등록일: {gb.created_at.strftime("%Y-%m-%d %H:%M:%S")}')

        images = gb.images.all()
        print(f'🖼️  이미지 개수: {images.count()}')

        if images.exists():
            for idx, img in enumerate(images, 1):
                print(f'   [{idx}] ID: {img.id} | Primary: {img.is_primary} | Order: {img.order_index}')
                if img.image_url:
                    # URL이 길면 앞뒤만 표시
                    url = img.image_url
                    if len(url) > 80:
                        url = url[:40] + '...' + url[-37:]
                    print(f'       URL: {url}')
                else:
                    print(f'       URL: ❌ None')
        else:
            print(f'   ⚠️  이미지가 등록되지 않았습니다!')

        print('-' * 100)
        print()

    # 전체 통계
    print('\n📈 전체 통계')
    print(f'   - 전체 커스텀 공구 수: {CustomGroupBuy.objects.count()}')
    print(f'   - 전체 이미지 수: {CustomGroupBuyImage.objects.count()}')
    print(f'   - 이미지 없는 공구 수: {CustomGroupBuy.objects.filter(images__isnull=True).distinct().count()}')
    print()

    # 특정 ID 확인 (가장 최근 것)
    if recent.exists():
        latest = recent.first()
        print(f'\n🔍 가장 최근 공구 (ID: {latest.id}) 상세 확인')
        print(f'   제목: {latest.title}')
        print(f'   타입: {latest.type}')
        print(f'   카테고리: {latest.categories}')

        images = latest.images.all()
        print(f'   이미지:')
        if images.exists():
            for img in images:
                print(f'      - {img.image_url}')
        else:
            print(f'      ⚠️  이미지 없음')

    print('\n' + '=' * 100)

if __name__ == '__main__':
    main()
