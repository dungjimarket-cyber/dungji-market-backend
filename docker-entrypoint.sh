#!/bin/bash

echo "Starting Dungji Market Backend Container..."

# 로그 디렉토리 생성 및 권한 설정
mkdir -p /app/logs
touch /app/logs/cron.log /app/logs/notification.log /app/logs/cleanup.log /app/logs/sync.log
chmod 666 /app/logs/*.log

# 시작 시간 로그
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Container started" >> /app/logs/cron.log

# crontab 설정
echo "Setting up cron jobs..."
crontab /app/crontab

# cron 서비스 시작
echo "Starting cron daemon..."
service cron start

# cron 상태 확인
service cron status

# 현재 설정된 cron jobs 확인
echo "Current cron jobs:"
crontab -l

# Migration 상태 확인
echo "================================================"
echo "🔍 Checking current migration status..."
echo "================================================"
python manage.py showmigrations used_electronics || echo "Could not show migrations"
echo "================================================"

# Django migrations 실행
echo "Running Django migrations..."
echo "================================================"
python manage.py migrate --noinput
echo "================================================"

# used_phones 앱 migration 명시적 실행
echo "Running used_phones migrations specifically..."
python manage.py migrate used_phones --noinput || echo "Used phones migration failed, but continuing..."

# Migration 상태 확인
echo "Current migration status:"
python manage.py showmigrations used_phones | tail -10 || echo "Could not show migrations"
echo "================================================"

# Static files 수집 (이미 Dockerfile에서 했지만 안전을 위해)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 환경 정보 로그
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Environment: DEBUG=$DEBUG, USE_S3=$USE_S3" >> /app/logs/cron.log

# Django 서버 시작
echo "Starting Django server with gunicorn..."
exec gunicorn dungji_market_backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info