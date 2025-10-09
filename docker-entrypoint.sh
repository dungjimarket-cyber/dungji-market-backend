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

# used_electronics migrations을 강제로 fake 처리 (이미 DB에 적용되어 있음)
echo "🔧 Marking used_electronics migrations as applied (fake)..."
python manage.py migrate used_electronics 0007 --fake || true
python manage.py migrate used_electronics 0008 --fake || true
python manage.py migrate used_electronics 0009 --fake || true
python manage.py migrate used_electronics 0010 --fake || true
echo "✅ used_electronics migrations marked as applied"
echo "================================================"

# Django migrations 실행 (나머지 앱들)
echo "Running Django migrations for other apps..."
echo "================================================"
python manage.py migrate admin --noinput || echo "admin migration done"
python manage.py migrate api --noinput || echo "api migration done"
python manage.py migrate auth --noinput || echo "auth migration done"
python manage.py migrate authtoken --noinput || echo "authtoken migration done"
python manage.py migrate contenttypes --noinput || echo "contenttypes migration done"
python manage.py migrate sessions --noinput || echo "sessions migration done"
python manage.py migrate used_phones --noinput || echo "used_phones migration done"
echo "================================================"

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