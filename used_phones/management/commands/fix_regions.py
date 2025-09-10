"""
중고폰 지역 데이터 수정 커맨드
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from used_phones.models import UsedPhone, UsedPhoneRegion
from api.models import Region


class Command(BaseCommand):
    help = '중고폰 지역 데이터 수정'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-duplicates',
            action='store_true',
            help='중복된 지역 제거',
        )
        parser.add_argument(
            '--sync-region-name',
            action='store_true',
            help='region_name 필드 동기화',
        )
        parser.add_argument(
            '--sync-main-region',
            action='store_true',
            help='첫 번째 UsedPhoneRegion을 main region으로 동기화',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n===== 중고폰 지역 데이터 수정 시작 =====\n')
        
        if options['fix_duplicates']:
            self.fix_duplicates()
        
        if options['sync_region_name']:
            self.sync_region_name()
        
        if options['sync_main_region']:
            self.sync_main_region()
        
        if not any([options['fix_duplicates'], options['sync_region_name'], options['sync_main_region']]):
            self.stdout.write('옵션을 선택하세요:')
            self.stdout.write('  --fix-duplicates: 중복 지역 제거')
            self.stdout.write('  --sync-region-name: region_name 필드 동기화')
            self.stdout.write('  --sync-main-region: 메인 region 필드 동기화')
    
    @transaction.atomic
    def fix_duplicates(self):
        """중복된 지역 제거"""
        self.stdout.write('\n🔄 중복 지역 제거 중...')
        
        # 중복 찾기
        from django.db.models import Count
        duplicates = UsedPhoneRegion.objects.values('used_phone', 'region').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        fixed_count = 0
        for dup in duplicates:
            # 중복된 항목들 가져오기
            dup_items = UsedPhoneRegion.objects.filter(
                used_phone_id=dup['used_phone'],
                region_id=dup['region']
            ).order_by('created_at')
            
            # 첫 번째만 남기고 나머지 삭제
            to_delete = list(dup_items[1:])
            for item in to_delete:
                item.delete()
                fixed_count += 1
        
        self.stdout.write(f'✅ {fixed_count}개 중복 항목 제거 완료')
    
    @transaction.atomic
    def sync_region_name(self):
        """region_name 필드 동기화"""
        self.stdout.write('\n📝 region_name 필드 동기화 중...')
        
        updated_count = 0
        for phone in UsedPhone.objects.filter(region__isnull=False):
            if phone.region and (not phone.region_name or phone.region_name != phone.region.full_name):
                phone.region_name = phone.region.full_name
                phone.save(update_fields=['region_name'])
                updated_count += 1
        
        self.stdout.write(f'✅ {updated_count}개 region_name 업데이트 완료')
    
    @transaction.atomic
    def sync_main_region(self):
        """첫 번째 UsedPhoneRegion을 main region으로 동기화"""
        self.stdout.write('\n🔗 메인 region 필드 동기화 중...')
        
        updated_count = 0
        
        # region이 없지만 UsedPhoneRegion이 있는 경우
        for phone in UsedPhone.objects.filter(region__isnull=True):
            first_region = UsedPhoneRegion.objects.filter(used_phone=phone).first()
            if first_region:
                phone.region = first_region.region
                phone.region_name = first_region.region.full_name
                phone.save(update_fields=['region', 'region_name'])
                updated_count += 1
                self.stdout.write(f'   Phone ID {phone.id}: {first_region.region.full_name} 설정')
        
        # region과 첫 번째 UsedPhoneRegion이 다른 경우
        mismatch_fixed = 0
        for phone in UsedPhone.objects.filter(region__isnull=False):
            first_region = UsedPhoneRegion.objects.filter(used_phone=phone).first()
            if first_region and first_region.region != phone.region:
                phone.region = first_region.region
                phone.region_name = first_region.region.full_name
                phone.save(update_fields=['region', 'region_name'])
                mismatch_fixed += 1
        
        self.stdout.write(f'✅ {updated_count}개 메인 region 설정')
        self.stdout.write(f'✅ {mismatch_fixed}개 불일치 수정')
        
        self.stdout.write('\n===== 수정 완료 =====\n')