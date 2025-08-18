#!/usr/bin/env python
"""
파트너 테스트 데이터 생성 스크립트
실제 파트너 계정에 테스트 데이터를 추가합니다.
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
from decimal import Decimal

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.models_partner import (
    Partner, ReferralRecord, PartnerSettlement, 
    PartnerLink, PartnerNotification
)
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def create_test_data_for_partner(username='holyfavor'):
    """특정 파트너에 대한 테스트 데이터 생성"""
    
    try:
        # 사용자 찾기
        user = User.objects.get(username=username)
        
        # 파트너 프로필 가져오기 또는 생성
        partner, created = Partner.objects.get_or_create(
            user=user,
            defaults={
                'partner_name': user.first_name or f'파트너_{user.id}',
                'partner_code': f'PARTNER_{user.id}',
                'commission_rate': Decimal('30.00'),
                'bank_name': '신한은행',
                'account_number': '110-123-456789',
                'account_holder': user.first_name or user.username,
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ 파트너 프로필 생성: {partner.partner_name}")
        else:
            print(f"✅ 기존 파트너 프로필 사용: {partner.partner_name}")
        
        # 1. 추천 링크 생성
        # short_code는 10자 제한이 있으므로 줄여야 함
        short_code = partner.partner_code.lower()[:10] if len(partner.partner_code) > 10 else partner.partner_code.lower()
        link, created = PartnerLink.objects.get_or_create(
            partner=partner,
            original_url=f'https://dungjimarket.com/register?ref={partner.partner_code}',
            defaults={
                'short_code': short_code,
                'short_url': f'https://dng.kr/{short_code}'
            }
        )
        print(f"  - 추천 링크: {'생성' if created else '기존 사용'}")
        
        # 2. 테스트 추천 회원 생성 (30명)
        print(f"\n📊 추천 회원 데이터 생성 중...")
        
        for i in range(30):
            # 랜덤 사용자 생성
            test_username = f'test_ref_{partner.id}_{i}'
            test_user, created = User.objects.get_or_create(
                username=test_username,
                defaults={
                    'email': f'test{partner.id}_{i}@example.com',
                    'first_name': f'테스트회원{i}',
                    'referred_by': partner.partner_code
                }
            )
            
            # 추천 기록 생성
            status = random.choice(['active', 'active', 'active', 'cancelled', 'paused'])  # 활성 비율 높게
            subscription_amount = random.choice([29900, 39900, 49900]) if status == 'active' else 0
            
            # 가입일을 최근 90일 내로 랜덤 설정
            days_ago = random.randint(0, 90)
            joined_date = timezone.now() - timedelta(days=days_ago)
            
            # 수수료 계산 (활성 상태일 때만)
            commission_amount = int(subscription_amount * 0.3) if status == 'active' else 0
            
            # 티켓 정보 (랜덤)
            ticket_count = random.randint(0, 10) if status == 'active' else 0
            ticket_amount = ticket_count * 10000
            
            record, created = ReferralRecord.objects.get_or_create(
                partner=partner,
                referred_user=test_user,
                defaults={
                    'subscription_status': status,
                    'subscription_amount': subscription_amount,
                    'ticket_count': ticket_count,
                    'ticket_amount': ticket_amount,
                    'commission_amount': commission_amount,
                    'settlement_status': random.choice(['pending', 'pending', 'completed'])  # 대부분 pending
                }
            )
            
            if created:
                record.created_at = joined_date
                record.save()
        
        print(f"  - 추천 회원 30명 생성 완료")
        
        # 3. 정산 내역 생성 (과거 정산 3건)
        print(f"\n💰 정산 내역 생성 중...")
        
        for i in range(3):
            months_ago = (i + 1) * 2  # 2, 4, 6개월 전
            settlement_date = timezone.now() - timedelta(days=months_ago * 30)
            
            settlement, created = PartnerSettlement.objects.get_or_create(
                partner=partner,
                requested_at__date=settlement_date.date(),
                defaults={
                    'settlement_amount': random.randint(100000, 500000),
                    'tax_invoice_requested': bool(random.randint(0, 1)),
                    'status': 'completed',
                    'bank_name': partner.bank_name,
                    'account_number': partner.account_number,
                    'account_holder': partner.account_holder,
                    'requested_at': settlement_date,
                    'processed_at': settlement_date + timedelta(days=3),
                    'memo': f'{months_ago}개월 전 정산'
                }
            )
            
            if created:
                print(f"  - {months_ago}개월 전 정산: {settlement.settlement_amount:,}원")
        
        # 4. 알림 생성 (최근 10개)
        print(f"\n🔔 알림 생성 중...")
        
        notification_types = [
            ('signup', '새로운 회원 가입', '추천 링크를 통해 새로운 회원이 가입했습니다.'),
            ('payment', '구독료 결제 완료', '추천 회원이 구독료를 결제했습니다.'),
            ('cancellation', '구독 취소', '추천 회원이 구독을 취소했습니다.'),
            ('settlement', '정산 완료', '요청하신 정산이 완료되었습니다.'),
            ('system', '시스템 공지', '파트너 시스템 업데이트 안내입니다.'),
        ]
        
        for i in range(10):
            days_ago = random.randint(0, 30)
            notification_date = timezone.now() - timedelta(days=days_ago)
            notification_type = random.choice(notification_types)
            
            notification, created = PartnerNotification.objects.get_or_create(
                partner=partner,
                notification_type=notification_type[0],
                title=notification_type[1],
                defaults={
                    'message': notification_type[2],
                    'is_read': random.choice([True, False, False]),  # 대부분 안 읽음
                    'created_at': notification_date
                }
            )
            
            if created and notification.is_read:
                notification.read_at = notification_date + timedelta(hours=random.randint(1, 24))
                notification.save()
        
        print(f"  - 알림 10개 생성 완료")
        
        # 5. 통계 출력
        print(f"\n📈 파트너 통계:")
        print(f"  - 총 추천 회원: {partner.get_total_referrals()}명")
        print(f"  - 활성 구독자: {partner.get_active_subscribers()}명")
        print(f"  - 이번달 수익: {partner.get_monthly_revenue():,}원")
        print(f"  - 정산가능금액: {partner.get_available_settlement_amount():,}원")
        
        print(f"\n✅ 테스트 데이터 생성 완료!")
        print(f"\n🔑 로그인 정보:")
        print(f"  - URL: https://dungjimarket.com/partner-login")
        print(f"  - ID: {username}")
        print(f"  - PW: (사용자의 실제 비밀번호)")
        
        return partner
        
    except User.DoesNotExist:
        print(f"❌ 사용자를 찾을 수 없습니다: {username}")
        
        # 사용 가능한 사용자 목록 표시
        users_with_partners = User.objects.filter(partner_profile__isnull=False)
        if users_with_partners.exists():
            print("\n사용 가능한 파트너 사용자:")
            for u in users_with_partners[:5]:
                print(f"  - {u.username} ({u.first_name})")
        
        return None
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    import sys
    
    # 커맨드라인 인자로 username 받기
    username = sys.argv[1] if len(sys.argv) > 1 else 'holyfavor'
    
    print(f"🚀 파트너 테스트 데이터 생성 시작")
    print(f"   대상 사용자: {username}")
    print("=" * 50)
    
    partner = create_test_data_for_partner(username)
    
    if partner:
        print("\n" + "=" * 50)
        print("✨ 모든 작업이 완료되었습니다!")
        print("   파트너 대시보드에서 확인해보세요.")
    else:
        print("\n" + "=" * 50)
        print("⚠️  테스트 데이터 생성에 실패했습니다.")