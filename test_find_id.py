import os
import django
import sys

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount

User = get_user_model()

# 테스트할 휴대폰 번호 입력
phone_number = input("테스트할 휴대폰 번호 입력 (하이픈 없이): ").strip()

try:
    user = User.objects.get(phone_number=phone_number)
    print(f"\n✅ 사용자 찾음:")
    print(f"  - ID: {user.id}")
    print(f"  - Username: {user.username}")
    print(f"  - Phone: {user.phone_number}")
    
    # SocialAccount 체크
    social_accounts = SocialAccount.objects.filter(user=user)
    if social_accounts.exists():
        print(f"\n🔍 SNS 계정 정보:")
        for sa in social_accounts:
            print(f"  - Provider: {sa.provider}")
            print(f"  - UID: {sa.uid}")
            print(f"  - Date joined: {sa.date_joined}")
    else:
        print(f"\n❌ SNS 계정 없음 - 일반 계정입니다")
        
except User.DoesNotExist:
    print(f"\n❌ 해당 번호로 등록된 사용자 없음: {phone_number}")
except Exception as e:
    print(f"\n❌ 오류 발생: {str(e)}")