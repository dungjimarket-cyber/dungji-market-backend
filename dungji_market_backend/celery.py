"""
Celery configuration for dungji_market_backend project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')

app = Celery('dungji_market_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    'check-expired-custom-groupbuys': {
        'task': 'api.tasks.check_expired_custom_groupbuys',
        'schedule': crontab(minute='*/5'),  # 5분마다 실행
    },
    'check-seller-decision-deadline': {
        'task': 'api.tasks.check_seller_decision_deadline',
        'schedule': crontab(minute='*/5'),  # 5분마다 실행
    },
}

app.conf.timezone = 'Asia/Seoul'