#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungjimarket.settings')
django.setup()

from api.models_custom import CustomGroupBuy

# 최근 생성된 커스텀 공구 확인
recent = CustomGroupBuy.objects.order_by('-created_at').first()
if recent:
    print(f'최근 생성된 공구: ID={recent.id}, 제목={recent.title}')
    print(f'타입: {recent.type}, 상태: {recent.status}')
    print(f'판매자: {recent.seller.username if recent.seller else "None"}')
    print(f'생성일: {recent.created_at}')
    print(f'지역 개수: {recent.region_links.count()}')
    if recent.region_links.exists():
        for region_link in recent.region_links.all():
            print(f'  - {region_link.region.full_name if hasattr(region_link.region, "full_name") else region_link.region.name}')
else:
    print('생성된 공구가 없습니다')

# 전체 개수 확인
total = CustomGroupBuy.objects.count()
print(f'\n전체 커스텀 공구 개수: {total}')

# 최근 5개 확인
print('\n최근 5개 공구:')
for gb in CustomGroupBuy.objects.order_by('-created_at')[:5]:
    print(f'  - ID: {gb.id}, 제목: {gb.title}, 생성: {gb.created_at}')