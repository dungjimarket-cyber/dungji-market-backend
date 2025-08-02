from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import GroupBuy, Participation, Bid, Notification, PhoneVerification
import pytz

class Command(BaseCommand):
    help = 'UTC로 저장된 시간 데이터를 한국 시간으로 마이그레이션'

    def handle(self, *args, **options):
        # UTC와 KST 시간대 설정
        utc = pytz.UTC
        kst = pytz.timezone('Asia/Seoul')
        
        # 9시간 차이
        time_diff = timedelta(hours=9)
        
        self.stdout.write('시간 데이터 마이그레이션 시작...')
        
        # 1. GroupBuy 모델
        self.stdout.write('\n1. GroupBuy 시간 데이터 변환 중...')
        groupbuys = GroupBuy.objects.all()
        updated_count = 0
        
        for gb in groupbuys:
            updated = False
            
            # start_time
            if gb.start_time and gb.start_time.hour <= 6:  # 새벽 시간대면 UTC로 저장된 것
                gb.start_time = gb.start_time + time_diff
                updated = True
            
            # end_time
            if gb.end_time and gb.end_time.hour <= 6:
                gb.end_time = gb.end_time + time_diff
                updated = True
            
            # voting_end
            if gb.voting_end and gb.voting_end.hour <= 6:
                gb.voting_end = gb.voting_end + time_diff
                updated = True
            
            # final_selection_end
            if gb.final_selection_end and gb.final_selection_end.hour <= 6:
                gb.final_selection_end = gb.final_selection_end + time_diff
                updated = True
            
            if updated:
                gb.save()
                updated_count += 1
                self.stdout.write(f'  - GroupBuy ID {gb.id} 업데이트 완료')
        
        self.stdout.write(f'  총 {updated_count}개 GroupBuy 업데이트 완료')
        
        # 2. Participation 모델
        self.stdout.write('\n2. Participation 시간 데이터 변환 중...')
        participations = Participation.objects.all()
        updated_count = 0
        
        for p in participations:
            if p.joined_at and p.joined_at.hour <= 6:
                p.joined_at = p.joined_at + time_diff
                # 유효성 검사를 우회하기 위해 직접 업데이트
                Participation.objects.filter(pk=p.pk).update(joined_at=p.joined_at)
                updated_count += 1
        
        self.stdout.write(f'  총 {updated_count}개 Participation 업데이트 완료')
        
        # 3. Bid 모델
        self.stdout.write('\n3. Bid 시간 데이터 변환 중...')
        bids = Bid.objects.all()
        updated_count = 0
        
        for b in bids:
            updated = False
            
            if b.created_at and b.created_at.hour <= 6:
                b.created_at = b.created_at + time_diff
                updated = True
            
            if b.updated_at and b.updated_at.hour <= 6:
                b.updated_at = b.updated_at + time_diff
                updated = True
            
            if updated:
                b.save()
                updated_count += 1
        
        self.stdout.write(f'  총 {updated_count}개 Bid 업데이트 완료')
        
        # 4. Notification 모델
        self.stdout.write('\n4. Notification 시간 데이터 변환 중...')
        notifications = Notification.objects.all()
        updated_count = 0
        
        for n in notifications:
            if n.created_at and n.created_at.hour <= 6:
                n.created_at = n.created_at + time_diff
                n.save()
                updated_count += 1
        
        self.stdout.write(f'  총 {updated_count}개 Notification 업데이트 완료')
        
        # 5. PhoneVerification 모델
        self.stdout.write('\n5. PhoneVerification 시간 데이터 변환 중...')
        verifications = PhoneVerification.objects.all()
        updated_count = 0
        
        for v in verifications:
            updated = False
            
            if v.created_at and v.created_at.hour <= 6:
                v.created_at = v.created_at + time_diff
                updated = True
            
            if v.expires_at and v.expires_at.hour <= 6:
                v.expires_at = v.expires_at + time_diff
                updated = True
            
            if v.verified_at and v.verified_at.hour <= 6:
                v.verified_at = v.verified_at + time_diff
                updated = True
            
            if updated:
                v.save()
                updated_count += 1
        
        self.stdout.write(f'  총 {updated_count}개 PhoneVerification 업데이트 완료')
        
        self.stdout.write(self.style.SUCCESS('\n✅ 시간 데이터 마이그레이션 완료!'))
        
        # 마이그레이션 후 샘플 확인
        self.stdout.write('\n마이그레이션 후 샘플 데이터:')
        sample_gb = GroupBuy.objects.first()
        if sample_gb:
            self.stdout.write(f'GroupBuy ID {sample_gb.id}:')
            self.stdout.write(f'  - start_time: {sample_gb.start_time}')
            self.stdout.write(f'  - end_time: {sample_gb.end_time}')