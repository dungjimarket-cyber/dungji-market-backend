"""
URL 패턴 확인 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.urls import get_resolver
from used_phones.views import UsedPhoneViewSet

# ViewSet의 action 메서드들 확인
print("=== UsedPhoneViewSet Actions ===")
viewset = UsedPhoneViewSet()
for attr_name in dir(viewset):
    attr = getattr(viewset, attr_name)
    if hasattr(attr, 'mapping'):  # action decorator가 있는 메서드
        print(f"Action: {attr_name}")
        print(f"  - URL: {getattr(attr, 'url_path', 'N/A')}")
        print(f"  - Methods: {getattr(attr, 'mapping', {})}")

print("\n=== Registered URLs for used_phones ===")
resolver = get_resolver()
for pattern in resolver.url_patterns:
    if hasattr(pattern, 'pattern'):
        pattern_str = str(pattern.pattern)
        if 'used' in pattern_str:
            print(f"Pattern: {pattern_str}")