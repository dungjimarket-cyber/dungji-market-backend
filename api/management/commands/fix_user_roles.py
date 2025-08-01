from django.core.management.base import BaseCommand
from api.models import User

class Command(BaseCommand):
    help = '모든 user role을 buyer로 변경하고 통계를 표시합니다'

    def handle(self, *args, **options):
        # 현재 상태 확인
        self.stdout.write("=== 현재 사용자 role 분포 ===")
        roles = User.objects.values_list('role', flat=True)
        role_counts = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in role_counts.items():
            self.stdout.write(f'{role}: {count}명')
        
        # user role 사용자 확인 및 업데이트
        user_role_users = User.objects.filter(role='user')
        user_count = user_role_users.count()
        
        if user_count > 0:
            self.stdout.write(f"\n'user' role 사용자 {user_count}명을 'buyer'로 변경합니다...")
            
            for user in user_role_users:
                self.stdout.write(f"  업데이트: ID {user.id} - {user.username}")
            
            # 일괄 업데이트
            updated_count = user_role_users.update(role='buyer')
            self.stdout.write(
                self.style.SUCCESS(f"✅ {updated_count}명의 사용자 role을 'buyer'로 업데이트했습니다.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ 모든 사용자가 이미 올바른 role을 가지고 있습니다.")
            )
        
        # 업데이트 후 상태
        self.stdout.write("\n=== 업데이트 후 사용자 role 분포 ===")
        roles = User.objects.values_list('role', flat=True)
        role_counts = {}
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in role_counts.items():
            self.stdout.write(f'{role}: {count}명')
        
        self.stdout.write(
            self.style.SUCCESS("\n✅ User role 정리가 완료되었습니다!")
        )