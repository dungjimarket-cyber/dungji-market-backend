"""
v3.0 데이터 마이그레이션 스크립트
- bidding 상태를 recruiting으로 변경
- 기존 데이터를 v3.0 스펙에 맞게 수정
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import GroupBuy
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'v3.0 데이터 마이그레이션 - bidding 상태 제거 및 데이터 정리'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('===================================='))
        self.stdout.write(self.style.WARNING('v3.0 데이터 마이그레이션 시작'))
        self.stdout.write(self.style.WARNING('===================================='))
        
        try:
            with transaction.atomic():
                # 1. bidding 상태를 가진 공구들을 조회
                bidding_groupbuys = GroupBuy.objects.filter(status='bidding')
                bidding_count = bidding_groupbuys.count()
                
                if bidding_count > 0:
                    self.stdout.write(f"\n📋 'bidding' 상태 공구 {bidding_count}개 발견")
                    
                    for gb in bidding_groupbuys:
                        self.stdout.write(f"  - {gb.id}: {gb.title}")
                    
                    # 현재 시간 기준으로 상태 결정
                    now = timezone.now()
                    
                    for gb in bidding_groupbuys:
                        old_status = gb.status
                        
                        # 종료 시간이 지났으면 final_selection_buyers로
                        if gb.end_time and now > gb.end_time:
                            gb.status = 'final_selection_buyers'
                            # final_selection_end가 없으면 설정
                            if not gb.final_selection_end:
                                from datetime import timedelta
                                gb.final_selection_end = gb.end_time + timedelta(hours=12)
                        else:
                            # 아직 진행중이면 recruiting으로
                            gb.status = 'recruiting'
                        
                        gb.save()
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ 공구 {gb.id} 상태 변경: {old_status} → {gb.status}")
                        )
                else:
                    self.stdout.write(self.style.SUCCESS("✅ 'bidding' 상태 공구가 없습니다."))
                
                # 2. 통계 출력
                from django.db import models as django_models
                self.stdout.write("\n📊 마이그레이션 후 상태별 공구 수:")
                status_counts = GroupBuy.objects.values('status').annotate(
                    count=django_models.Count('id')
                ).order_by('status')
                
                for item in status_counts:
                    status = item['status']
                    count = item['count']
                    status_display = dict(GroupBuy.STATUS_CHOICES).get(status, status)
                    self.stdout.write(f"  - {status_display} ({status}): {count}개")
                
                self.stdout.write(self.style.SUCCESS('\n✅ v3.0 데이터 마이그레이션 완료!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 마이그레이션 중 오류 발생: {str(e)}'))
            logger.error(f"마이그레이션 오류: {str(e)}", exc_info=True)
            raise