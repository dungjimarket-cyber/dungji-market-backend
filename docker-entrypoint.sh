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

# Migration history 정리 (renumbered migrations 처리)
echo "Fixing migration history with direct SQL..."
python manage.py shell <<EOF
from django.db import connection
with connection.cursor() as cursor:
    # 0007: 0010_electronicsdeletepenalty → 0007_electronicsdeletepenalty
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'used_electronics', '0007_electronicsdeletepenalty', NOW()
        WHERE EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0010_electronicsdeletepenalty'
        )
        AND NOT EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0007_electronicsdeletepenalty'
        );
    """)

    # 0008: 0010_change_transaction_to_foreignkey → 0008_change_transaction_to_foreignkey
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'used_electronics', '0008_change_transaction_to_foreignkey', NOW()
        WHERE EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0010_change_transaction_to_foreignkey'
        )
        AND NOT EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0008_change_transaction_to_foreignkey'
        );
    """)

    # 0009: 0011_add_bump_fields → 0009_add_bump_fields
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'used_electronics', '0009_add_bump_fields', NOW()
        WHERE EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0011_add_bump_fields'
        )
        AND NOT EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0009_add_bump_fields'
        );
    """)

    # 0010: 0012_update_condition_grade_choices → 0010_update_condition_grade_choices
    cursor.execute("""
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'used_electronics', '0010_update_condition_grade_choices', NOW()
        WHERE EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0012_update_condition_grade_choices'
        )
        AND NOT EXISTS (
            SELECT 1 FROM django_migrations
            WHERE app = 'used_electronics' AND name = '0010_update_condition_grade_choices'
        );
    """)
    print("✅ Migration history fixed")
EOF

# Django migrations 실행
echo "Running Django migrations..."
echo "================================================"
python manage.py migrate --noinput || echo "Migration failed, but continuing..."

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