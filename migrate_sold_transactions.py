"""
기존 거래완료(sold) 상태 상품들에 대한 UsedPhoneTransaction 생성 스크립트
"""
import os
import sys
import django
from django.utils import timezone

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from used_phones.models import UsedPhone, UsedPhoneOffer, UsedPhoneTransaction

def migrate_sold_transactions():
    """판매완료 상태이지만 Transaction이 없는 상품들 처리"""

    # sold 상태인 모든 상품 조회
    sold_phones = UsedPhone.objects.filter(status='sold')

    created_count = 0
    skipped_count = 0
    error_count = 0

    for phone in sold_phones:
        try:
            # 이미 transaction이 있는지 확인
            existing_transaction = UsedPhoneTransaction.objects.filter(phone=phone).first()

            if existing_transaction:
                print(f"✓ Phone {phone.id} already has transaction")
                skipped_count += 1
                continue

            # accepted 상태의 offer 찾기
            accepted_offer = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='accepted'
            ).first()

            if not accepted_offer:
                print(f"⚠ Phone {phone.id} has no accepted offer - skipping")
                error_count += 1
                continue

            # Transaction 생성
            transaction = UsedPhoneTransaction.objects.create(
                phone=phone,
                offer=accepted_offer,
                seller=phone.seller,
                buyer=accepted_offer.buyer,
                final_price=accepted_offer.offered_price,
                status='completed',
                seller_confirmed=True,
                buyer_confirmed=True,
                seller_confirmed_at=phone.sold_at or timezone.now(),
                buyer_confirmed_at=phone.sold_at or timezone.now()
            )

            print(f"✅ Created transaction for Phone {phone.id} (Transaction ID: {transaction.id})")
            created_count += 1

        except Exception as e:
            print(f"❌ Error processing Phone {phone.id}: {str(e)}")
            error_count += 1

    print("\n" + "="*50)
    print(f"Migration Complete:")
    print(f"  - Created: {created_count} transactions")
    print(f"  - Skipped: {skipped_count} (already exists)")
    print(f"  - Errors: {error_count}")
    print("="*50)

if __name__ == '__main__':
    print("Starting migration for sold phones without transactions...")
    migrate_sold_transactions()