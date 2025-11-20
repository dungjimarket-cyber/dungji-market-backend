"""
지역 업체 정보 초기화 스크립트
Django 콘솔에서 직접 실행 가능

사용법:
python manage.py shell < init_local_business.py
"""

import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.core.management import call_command

print("=" * 60)
print("🚀 지역 업체 정보 초기화 시작")
print("=" * 60)

# 1단계: 카테고리 초기화
print("\n[1/2] 📋 카테고리 초기화 중...")
try:
    call_command('init_local_business_categories')
    print("✅ 카테고리 초기화 완료")
except Exception as e:
    print(f"❌ 카테고리 초기화 실패: {str(e)}")
    import traceback
    traceback.print_exc()

# 2단계: 데이터 수집 (강남구만 테스트)
print("\n[2/2] 🔍 데이터 수집 중 (강남구 테스트)...")
try:
    call_command('collect_local_businesses', region='강남구', limit=5)
    print("✅ 데이터 수집 완료")
except Exception as e:
    print(f"❌ 데이터 수집 실패: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 초기화 완료!")
print("=" * 60)
