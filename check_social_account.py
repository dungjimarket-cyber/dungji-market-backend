import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()

# 테스트할 휴대폰 번호
phone_number = '01038634492'

print(f"\n=== 휴대폰 번호 {phone_number} 검색 ===\n")

try:
    user = User.objects.get(phone_number=phone_number)
    print(f"✅ 사용자 찾음:")
    print(f"  - User ID: {user.id}")
    print(f"  - Username: {user.username}")
    print(f"  - Email: {user.email}")
    print(f"  - Phone: {user.phone_number}")
    print(f"  - Date joined: {user.date_joined}")
    
    # allauth 앱 설치 확인
    print(f"\n📱 앱 설치 상태:")
    if apps.is_installed('allauth.socialaccount'):
        print(f"  ✅ allauth.socialaccount 앱이 설치됨")
        
        from allauth.socialaccount.models import SocialAccount
        
        # SocialAccount 조회
        social_accounts = SocialAccount.objects.filter(user=user)
        
        if social_accounts.exists():
            print(f"\n🔍 SNS 계정 정보 발견:")
            for sa in social_accounts:
                print(f"  - Provider: {sa.provider}")
                print(f"  - UID: {sa.uid}")
                print(f"  - Extra data: {sa.extra_data}")
                print(f"  - Date joined: {sa.date_joined}")
        else:
            print(f"\n❌ SocialAccount 테이블에 데이터 없음")
            
            # 전체 SocialAccount 수 확인
            total_social = SocialAccount.objects.count()
            print(f"\n📊 전체 SocialAccount 레코드 수: {total_social}")
            
            # 카카오 계정만 확인
            kakao_accounts = SocialAccount.objects.filter(provider='kakao')
            print(f"📊 카카오 계정 수: {kakao_accounts.count()}")
            
            if kakao_accounts.exists():
                print("\n카카오 계정 목록 (처음 5개):")
                for ka in kakao_accounts[:5]:
                    ka_user = ka.user
                    print(f"  - User: {ka_user.username} (ID: {ka_user.id}, Phone: {ka_user.phone_number})")
    else:
        print(f"  ❌ allauth.socialaccount 앱이 설치되지 않음")
        
    # KakaoUser 모델 확인 (있다면)
    print(f"\n🔍 KakaoUser 모델 확인:")
    try:
        from api.models import KakaoUser
        kakao_user = KakaoUser.objects.filter(user=user).first()
        if kakao_user:
            print(f"  ✅ KakaoUser 데이터 발견:")
            print(f"    - Kakao ID: {kakao_user.kakao_id}")
            print(f"    - Created: {kakao_user.created_at if hasattr(kakao_user, 'created_at') else 'N/A'}")
        else:
            print(f"  ❌ KakaoUser 데이터 없음")
    except ImportError:
        print(f"  ℹ️ KakaoUser 모델이 정의되지 않음")
        
except User.DoesNotExist:
    print(f"❌ 해당 번호로 등록된 사용자 없음")
except Exception as e:
    print(f"❌ 오류 발생: {str(e)}")
    import traceback
    traceback.print_exc()