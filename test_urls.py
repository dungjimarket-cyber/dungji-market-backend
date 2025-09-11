#!/usr/bin/env python
"""Test script to check if URLs are properly registered"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.urls import resolve, reverse
from rest_framework.routers import DefaultRouter
from used_phones.views import UsedPhoneViewSet

# Router를 직접 생성하여 URL 패턴 확인
router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')

print("\n=== Used Phone ViewSet URLs ===")
for url_pattern in router.urls:
    print(f"Pattern: {url_pattern.pattern}")
    if hasattr(url_pattern, 'name'):
        print(f"  Name: {url_pattern.name}")

print("\n=== Testing specific URLs ===")
# seller-info URL 테스트
try:
    url = reverse('usedphone-seller-info', kwargs={'pk': 1})
    print(f"✓ seller-info URL: {url}")
except Exception as e:
    print(f"✗ seller-info URL error: {e}")

# buyer-info URL 테스트  
try:
    url = reverse('usedphone-buyer-info', kwargs={'pk': 1})
    print(f"✓ buyer-info URL: {url}")
except Exception as e:
    print(f"✗ buyer-info URL error: {e}")

print("\n=== ViewSet actions ===")
viewset = UsedPhoneViewSet()
for attr_name in dir(viewset):
    attr = getattr(viewset, attr_name)
    if hasattr(attr, 'mapping'):  # @action decorator adds 'mapping' attribute
        print(f"Action: {attr_name}")
        print(f"  URL path: {getattr(attr, 'url_path', 'default')}")
        print(f"  Methods: {getattr(attr, 'mapping', {})}")