#!/usr/bin/env python
"""
파트너 로그인 정보 설정 스크립트
Django Admin에서 생성한 파트너의 로그인 정보를 설정합니다.
"""

import os
import sys
import django
from django.contrib.auth.hashers import make_password

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.models_partner import Partner, PartnerLink
from django.contrib.auth import get_user_model

User = get_user_model()

def setup_partner_login():
    """파트너 로그인 정보 설정"""
    
    # 파트너 코드로 파트너 찾기
    partner_code = 'PARTNER_KOJVOR'
    
    try:
        partner = Partner.objects.get(partner_code=partner_code)
        print(f"파트너 찾음: {partner.partner_name}")
        
        # partner_id와 password 설정
        if not partner.partner_id:
            partner.partner_id = f'partner_{partner.user.id}'
        
        # 비밀번호 설정 (해시 처리)
        raw_password = 'Test1234!'  # 테스트용 비밀번호
        partner.partner_password = make_password(raw_password)
        
        partner.save()
        
        print(f"파트너 로그인 정보 설정 완료:")
        print(f"  파트너 ID: {partner.partner_id}")
        print(f"  비밀번호: {raw_password}")
        print(f"  파트너 코드: {partner.partner_code}")
        
        # 추천 링크가 없으면 생성
        if not PartnerLink.objects.filter(partner=partner).exists():
            base_url = 'https://dungjimarket.com'
            PartnerLink.objects.create(
                partner=partner,
                link_type='default',
                full_url=f'{base_url}/register?ref={partner_code}',
                short_url=f'{base_url}/r/{partner_code}',
                qr_code_url=f'{base_url}/api/partners/qr/{partner_code}.png'
            )
            print("  추천 링크 생성 완료")
        
        # 테스트용 추천 회원 몇 명 생성
        from api.models_partner import ReferralRecord
        from datetime import datetime, timedelta
        import random
        
        # 기존 추천 회원이 없으면 테스트 데이터 생성
        if not ReferralRecord.objects.filter(partner=partner).exists():
            for i in range(5):
                # 추천으로 가입한 사용자 생성
                username = f'ref_user_{partner.id}_{i}'
                if not User.objects.filter(username=username).exists():
                    referred_user = User.objects.create_user(
                        username=username,
                        email=f'ref{partner.id}_{i}@test.com',
                        password='Test1234!',
                        first_name=f'회원{i}',
                        referred_by=partner_code
                    )
                    
                    # 추천 기록 생성
                    status = random.choice(['active', 'cancelled', 'paused'])
                    subscription_amount = random.choice([29900, 39900, 49900]) if status == 'active' else 0
                    
                    record = ReferralRecord.objects.create(
                        partner=partner,
                        referred_user=referred_user,
                        subscription_status=status,
                        subscription_amount=subscription_amount,
                        ticket_count=random.randint(0, 5),
                        ticket_amount=random.randint(0, 3) * 10000,
                        commission_rate=30.00
                    )
                    
                    # 가입일 랜덤 설정
                    days_ago = random.randint(0, 30)
                    record.joined_date = datetime.now() - timedelta(days=days_ago)
                    record.save()
            
            print(f"  테스트 추천 회원 5명 생성 완료")
        
        return True
        
    except Partner.DoesNotExist:
        print(f"파트너를 찾을 수 없습니다: {partner_code}")
        
        # 모든 파트너 목록 표시
        all_partners = Partner.objects.all()
        if all_partners.exists():
            print("\n사용 가능한 파트너 목록:")
            for p in all_partners:
                print(f"  - {p.partner_name} (코드: {p.partner_code})")
        else:
            print("\n생성된 파트너가 없습니다.")
        
        return False
    
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = setup_partner_login()
    if success:
        print("\n✅ 파트너 로그인 설정 완료!")
        print("이제 파트너 로그인 페이지에서 로그인할 수 있습니다.")
    else:
        print("\n❌ 파트너 로그인 설정 실패")