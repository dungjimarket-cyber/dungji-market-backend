from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import GroupBuy, Participation

class Command(BaseCommand):
    help = '각 공구의 current_participants를 실제 참여자 수와 동기화합니다.'

    def handle(self, *args, **options):
        # 모든 공구를 가져와서 실제 참여자 수와 비교
        groupbuys = GroupBuy.objects.all()
        updated_count = 0
        
        for groupbuy in groupbuys:
            # 실제 참여자 수 계산
            actual_count = Participation.objects.filter(groupbuy=groupbuy).count()
            
            # current_participants와 다른 경우 업데이트
            if groupbuy.current_participants != actual_count:
                old_count = groupbuy.current_participants
                groupbuy.current_participants = actual_count
                groupbuy.save(update_fields=['current_participants'])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'공구 "{groupbuy.title}" (ID: {groupbuy.id}): '
                        f'{old_count}명 → {actual_count}명으로 수정'
                    )
                )
                updated_count += 1
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n총 {updated_count}개의 공구 참여자 수가 수정되었습니다.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('모든 공구의 참여자 수가 정확합니다.')
            )