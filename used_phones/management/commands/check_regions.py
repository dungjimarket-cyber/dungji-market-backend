"""
중고폰 지역 데이터 체크 커맨드
- 지역이 없는 데이터
- 중복된 지역
- region vs regions 불일치
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from used_phones.models import UsedPhone, UsedPhoneRegion
from api.models import Region


class Command(BaseCommand):
    help = '중고폰 지역 데이터 체크'

    def handle(self, *args, **kwargs):
        self.stdout.write('\n===== 중고폰 지역 데이터 체크 =====\n')
        
        # 1. 전체 중고폰 수
        total_phones = UsedPhone.objects.filter(status='active').count()
        self.stdout.write(f'📊 전체 활성 중고폰: {total_phones}개\n')
        
        # 2. region 필드가 없는 중고폰
        no_region = UsedPhone.objects.filter(status='active', region__isnull=True)
        self.stdout.write(f'\n❌ region 필드가 없는 중고폰: {no_region.count()}개')
        if no_region.exists():
            for phone in no_region[:5]:  # 처음 5개만 표시
                self.stdout.write(f'   - ID {phone.id}: {phone.model} (seller: {phone.seller.username})')
        
        # 3. region_name 필드가 없는 중고폰
        no_region_name = UsedPhone.objects.filter(
            status='active', 
            region__isnull=False,
            region_name__isnull=True
        ).count()
        self.stdout.write(f'\n⚠️  region은 있지만 region_name이 없는 중고폰: {no_region_name}개')
        
        # 4. UsedPhoneRegion 테이블 체크
        self.stdout.write(f'\n📍 UsedPhoneRegion 다중 지역 정보:')
        phones_with_regions = UsedPhoneRegion.objects.values('used_phone').distinct().count()
        self.stdout.write(f'   - 다중 지역이 설정된 중고폰: {phones_with_regions}개')
        
        # 지역 개수별 분포
        region_counts = UsedPhoneRegion.objects.values('used_phone').annotate(
            region_count=Count('region')
        ).values('region_count').annotate(
            phone_count=Count('used_phone')
        ).order_by('region_count')
        
        for rc in region_counts:
            self.stdout.write(f'   - {rc["region_count"]}개 지역: {rc["phone_count"]}개 중고폰')
        
        # 5. 중복 지역 체크 (같은 중고폰에 같은 지역이 여러 번)
        duplicates = UsedPhoneRegion.objects.values('used_phone', 'region').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicates.exists():
            self.stdout.write(f'\n🔄 중복된 지역 설정: {duplicates.count()}건')
            for dup in duplicates[:5]:
                phone = UsedPhone.objects.get(id=dup['used_phone'])
                region = Region.objects.get(id=dup['region'])
                self.stdout.write(f'   - Phone ID {phone.id} ({phone.model}): {region.full_name} x {dup["count"]}번')
        else:
            self.stdout.write(f'\n✅ 중복된 지역 설정 없음')
        
        # 6. region과 UsedPhoneRegion 불일치 체크
        self.stdout.write(f'\n🔍 region 필드와 UsedPhoneRegion 일치성 체크:')
        
        mismatch_count = 0
        for phone in UsedPhone.objects.filter(status='active', region__isnull=False):
            phone_regions = UsedPhoneRegion.objects.filter(used_phone=phone)
            
            if phone_regions.exists():
                # 첫 번째 지역이 메인 region과 같은지 확인
                first_region = phone_regions.first()
                if first_region and first_region.region != phone.region:
                    mismatch_count += 1
                    if mismatch_count <= 5:  # 처음 5개만 표시
                        self.stdout.write(
                            f'   - Phone ID {phone.id}: '
                            f'region={phone.region.name if phone.region else "None"}, '
                            f'첫 지역={first_region.region.name}'
                        )
        
        if mismatch_count > 0:
            self.stdout.write(f'   ⚠️ 불일치 건수: {mismatch_count}개')
        else:
            self.stdout.write(f'   ✅ 모든 데이터 일치')
        
        # 7. 가장 많이 사용된 지역 TOP 10
        self.stdout.write(f'\n📈 가장 많이 사용된 지역 TOP 10:')
        top_regions = UsedPhoneRegion.objects.values('region__full_name').annotate(
            count=Count('used_phone', distinct=True)
        ).order_by('-count')[:10]
        
        for idx, tr in enumerate(top_regions, 1):
            self.stdout.write(f'   {idx}. {tr["region__full_name"]}: {tr["count"]}개')
        
        # 8. 지역이 전혀 없는 중고폰 (region도 없고 UsedPhoneRegion도 없음)
        phones_without_any_region = []
        for phone in UsedPhone.objects.filter(status='active'):
            has_region = phone.region is not None
            has_phone_regions = UsedPhoneRegion.objects.filter(used_phone=phone).exists()
            
            if not has_region and not has_phone_regions:
                phones_without_any_region.append(phone)
        
        self.stdout.write(f'\n❗ 지역 정보가 전혀 없는 중고폰: {len(phones_without_any_region)}개')
        for phone in phones_without_any_region[:5]:
            self.stdout.write(
                f'   - ID {phone.id}: {phone.model} '
                f'(created: {phone.created_at.strftime("%Y-%m-%d")})'
            )
        
        self.stdout.write('\n===== 체크 완료 =====\n')