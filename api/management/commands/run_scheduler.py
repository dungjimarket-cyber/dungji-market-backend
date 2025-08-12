from django.core.management.base import BaseCommand
from django.core.management import call_command
import time
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '백그라운드에서 주기적으로 공구 상태를 업데이트합니다'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=600,  # 기본값: 10분(600초)
            help='실행 간격(초 단위)'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS(f'스케줄러 시작 - {interval}초마다 실행'))
        
        def run_update():
            while True:
                try:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.stdout.write(f'[{current_time}] 공구 상태 업데이트 시작...')
                    
                    # update_groupbuy_status 명령 실행
                    call_command('update_groupbuy_status')
                    
                    self.stdout.write(f'[{current_time}] 공구 상태 업데이트 완료')
                except Exception as e:
                    logger.error(f"스케줄러 실행 중 오류: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'오류 발생: {str(e)}'))
                
                # 지정된 시간만큼 대기
                time.sleep(interval)
        
        # 스레드로 실행
        scheduler_thread = threading.Thread(target=run_update)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # 메인 스레드 유지
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\n스케줄러 종료'))