from django.core.management.base import BaseCommand
from django.utils import timezone
import logging
from api.utils.notification_scheduler import NotificationScheduler

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '알림 스케줄러를 실행하여 자동 알림 및 상태 업데이트를 처리합니다.'

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(self.style.SUCCESS(f'알림 스케줄러 시작: {start_time}'))
        
        try:
            # 모든 스케줄링 작업 실행
            NotificationScheduler.run_all_tasks()
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(self.style.SUCCESS(f'알림 스케줄러 완료: {end_time} (소요 시간: {duration:.2f}초)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'알림 스케줄러 실행 중 오류 발생: {str(e)}'))
            logger.error(f'알림 스케줄러 실행 중 오류 발생: {str(e)}', exc_info=True)
