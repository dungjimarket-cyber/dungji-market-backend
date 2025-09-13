#!/bin/bash

# Django migrations 실행 스크립트

echo "🔄 Starting Django migrations..."

# 전체 migration 상태 확인
echo "\n📊 Current migration status:"
python manage.py showmigrations

# used_phones 앱 마이그레이션 실행
echo "\n🔧 Applying used_phones migrations..."
python manage.py migrate used_phones

# 전체 마이그레이션 실행
echo "\n🔧 Applying all pending migrations..."
python manage.py migrate

# 최종 상태 확인
echo "\n✅ Migration complete. Final status:"
python manage.py showmigrations used_phones

echo "\n✨ All migrations completed successfully!"