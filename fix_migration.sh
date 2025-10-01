#!/bin/bash
# Docker 컨테이너에서 migration fake 실행

echo "=== Fake migrating 0089_unifiedbump ==="
docker compose exec -T web python manage.py migrate api 0089_unifiedbump --fake

echo ""
echo "=== Running remaining migrations ==="
docker compose exec -T web python manage.py migrate

echo ""
echo "=== Checking migration status ==="
docker compose exec -T web python manage.py showmigrations api | tail -20
