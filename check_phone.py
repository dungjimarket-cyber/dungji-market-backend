from used_phones.models import UsedPhone, UsedPhoneTransaction
from django.contrib.auth import get_user_model
User = get_user_model()

# ID 10번 phone 확인
try:
    phone = UsedPhone.objects.get(id=10)
    print(f'Phone ID 10: {phone.title}')
    print(f'Status: {phone.status}')
    print(f'Seller: {phone.seller}')

    # 거래 정보 확인
    transaction = UsedPhoneTransaction.objects.filter(phone=phone, status='trading').first()
    if transaction:
        print(f'Transaction: {transaction}')
        print(f'Buyer: {transaction.buyer}')
    else:
        print('No active transaction')
except UsedPhone.DoesNotExist:
    print('Phone ID 10 does not exist')
except Exception as e:
    print(f'Error: {e}')