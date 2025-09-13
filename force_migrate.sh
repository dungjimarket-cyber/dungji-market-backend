#!/bin/bash

# Force migration script for production server
# Usage: docker exec dungji-market-backend /app/force_migrate.sh

echo "========================================"
echo "Force Migration Script for Dungji Market"
echo "========================================"
echo ""

# 현재 migration 상태 확인
echo "📊 Current migration status:"
python manage.py showmigrations used_phones | tail -20
echo ""

# 모든 migration 강제 실행
echo "🔧 Applying ALL migrations..."
python manage.py migrate --noinput
echo ""

# used_phones 앱 migration 명시적 실행
echo "🔧 Applying used_phones migrations..."
python manage.py migrate used_phones --noinput
echo ""

# 최종 상태 확인
echo "✅ Final migration status:"
python manage.py showmigrations used_phones | tail -20
echo ""

# 테이블 존재 확인
echo "📋 Checking if tables exist:"
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'used_phone%'\")
    tables = cursor.fetchall()
    for table in tables:
        print(f'  ✓ {table[0]}')
" 2>/dev/null || echo "  ⚠️  Could not check tables"
echo ""

echo "========================================"
echo "Migration script completed!"
echo "========================================"