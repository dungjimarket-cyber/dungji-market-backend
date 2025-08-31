#!/usr/bin/env python
"""
Django 환경 설정 확인 스크립트
개발/스테이징/프로덕션 환경별 CORS 및 CSRF 설정을 확인합니다.
"""
import os
import sys
import django
from pathlib import Path

# Django 설정 모듈 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.conf import settings

def check_environment_settings():
    """환경별 설정 확인"""
    print("=" * 60)
    print("🔧 Django 환경 설정 확인")
    print("=" * 60)
    
    print(f"환경 (DJANGO_ENV): {getattr(settings, 'DJANGO_ENV', 'Not Set')}")
    print(f"디버그 모드 (DEBUG): {settings.DEBUG}")
    print(f"허용 호스트: {settings.ALLOWED_HOSTS}")
    
    print("\n📡 CORS 설정:")
    print(f"CORS 허용 오리진: {getattr(settings, 'CORS_ALLOWED_ORIGINS', 'Not Set')}")
    print(f"모든 오리진 허용: {getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)}")
    print(f"자격 증명 허용: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)}")
    
    print("\n🔒 CSRF 설정:")
    print(f"CSRF 신뢰 오리진: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', 'Not Set')}")
    
    print("\n📧 이메일 설정:")
    print(f"이메일 백엔드: {settings.EMAIL_BACKEND}")
    print(f"기본 발신자: {settings.DEFAULT_FROM_EMAIL}")
    print(f"사이트 URL: {getattr(settings, 'SITE_URL', 'Not Set')}")
    
    print("\n💾 데이터베이스:")
    db_engine = settings.DATABASES['default']['ENGINE']
    db_name = settings.DATABASES['default']['NAME']
    print(f"DB 엔진: {db_engine}")
    print(f"DB 이름: {db_name}")
    
    # Vercel Preview 도메인 확인
    vercel_domain = "https://dungji-market-frontend-git-develop-dungjimarkets-projects.vercel.app"
    cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    csrf_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    
    print(f"\n🚀 Vercel Preview 도메인 지원:")
    print(f"CORS에 Vercel 도메인 포함: {vercel_domain in cors_origins}")
    print(f"CSRF에 Vercel 도메인 포함: {vercel_domain in csrf_origins}")
    
    return True

if __name__ == "__main__":
    try:
        check_environment_settings()
        print("\n✅ 환경 설정 확인 완료!")
    except Exception as e:
        print(f"\n❌ 환경 설정 확인 중 오류: {e}")
        sys.exit(1)