# 패널티 테스트 스크립트
# Django shell에서 실행: python manage.py shell < api/test_penalty.py

from api.models import User, Penalty
from django.utils import timezone
from datetime import timedelta

# 사용자 ID 107 조회
user = User.objects.get(id=107)
print(f"\n사용자: {user.username} (ID: {user.id})")

# 모든 패널티 조회
all_penalties = Penalty.objects.filter(user=user)
print(f"\n전체 패널티: {all_penalties.count()}개")

for p in all_penalties:
    print(f"  - ID: {p.id}")
    print(f"    Type: {p.penalty_type}")
    print(f"    is_active: {p.is_active}")
    print(f"    start_date: {p.start_date}")
    print(f"    end_date: {p.end_date}")
    print(f"    현재시간: {timezone.now()}")
    print(f"    유효한가?: {p.end_date > timezone.now()}")
    print(f"    활성 상태?: {p.is_active and p.end_date > timezone.now()}")

# 활성 패널티 조회
active_penalty = Penalty.objects.filter(
    user=user,
    is_active=True,
    end_date__gt=timezone.now()
).first()

print(f"\n활성 패널티: {active_penalty}")

if active_penalty:
    print(f"  Type: {active_penalty.penalty_type}")
    print(f"  Reason: {active_penalty.reason}")
    print(f"  End date: {active_penalty.end_date}")
else:
    print("  활성 패널티 없음")

# 테스트 패널티 생성 (필요시)
create_test = input("\n테스트 패널티를 생성하시겠습니까? (y/n): ")
if create_test.lower() == 'y':
    test_penalty = Penalty.objects.create(
        user=user,
        penalty_type='NO_SHOW',
        reason='테스트 패널티',
        count=1,
        is_active=True,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(hours=24)
    )
    print(f"테스트 패널티 생성됨: {test_penalty}")