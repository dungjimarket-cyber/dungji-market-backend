# 테스트 패널티 생성 스크립트
# Django shell에서 실행: python manage.py shell

from api.models import User, Penalty
from django.utils import timezone
from datetime import timedelta

# 사용자 조회
user = User.objects.get(id=107)
print(f"사용자: {user.username} (ID: {user.id})")

# 기존 활성 패널티 비활성화
old_penalties = Penalty.objects.filter(user=user, is_active=True)
for p in old_penalties:
    p.is_active = False
    p.save()
    print(f"기존 패널티 비활성화: {p.id}")

# 새 테스트 패널티 생성
new_penalty = Penalty.objects.create(
    user=user,
    penalty_type='NO_SHOW',
    reason='테스트용 노쇼 패널티',
    count=1,
    is_active=True,
    start_date=timezone.now(),
    end_date=timezone.now() + timedelta(hours=24)  # 24시간 후 만료
)

print(f"\n✅ 새 패널티 생성 완료!")
print(f"  - ID: {new_penalty.id}")
print(f"  - Type: {new_penalty.penalty_type}")
print(f"  - is_active: {new_penalty.is_active}")
print(f"  - start_date: {new_penalty.start_date}")
print(f"  - end_date: {new_penalty.end_date}")
print(f"  - 만료까지: 24시간")

# 확인
active = Penalty.objects.filter(
    user=user,
    is_active=True,
    end_date__gt=timezone.now()
).first()

print(f"\n활성 패널티 확인: {active}")
if active:
    print(f"  - Type: {active.penalty_type}")
    print(f"  - Reason: {active.reason}")
    print(f"  - Active: {active.is_active}")
    print(f"  - Valid: {active.end_date > timezone.now()}")