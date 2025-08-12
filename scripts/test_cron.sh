#!/bin/bash

# 크론 작업 테스트 스크립트
# 서버에서 실행: bash test_cron.sh

echo "=========================================="
echo "🧪 Dungji Market Cron Jobs Test"
echo "=========================================="

# Docker 컨테이너 이름 자동 감지
CONTAINER_NAME=$(docker ps --format "table {{.Names}}" | grep -E "dungji.*web" | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Error: Docker container not found!"
    exit 1
fi

echo "✅ Found container: $CONTAINER_NAME"
echo ""

# 로그 파일 생성 (없는 경우)
mkdir -p /home/ubuntu/logs
touch /home/ubuntu/logs/cron.log
touch /home/ubuntu/logs/notification.log
touch /home/ubuntu/logs/cleanup.log

echo "📋 Testing cron jobs..."
echo "=========================================="

# 1. 상태 업데이트 테스트
echo ""
echo "1️⃣ Testing status update..."
echo "---"
docker exec $CONTAINER_NAME python manage.py shell -c "
from api.utils import update_groupbuys_status
from api.models import GroupBuy
from django.utils import timezone

# 현재 상태 확인
active = GroupBuy.objects.filter(status__in=['recruiting', 'final_selection_buyers', 'final_selection_seller']).count()
print(f'Active GroupBuys: {active}')

# 업데이트 실행
updated = update_groupbuys_status()
print(f'Updated: {updated} groupbuys')
print(f'Time: {timezone.now()}')
" | tee -a /home/ubuntu/logs/cron.log

# 2. 판매자 타임아웃 체크
echo ""
echo "2️⃣ Testing seller timeout check..."
echo "---"
docker exec $CONTAINER_NAME python manage.py shell -c "
from api.models import GroupBuy
from django.utils import timezone

expired = GroupBuy.objects.filter(
    status='final_selection_seller',
    seller_selection_end__lt=timezone.now()
).count()
print(f'Expired seller decisions: {expired}')
" | tee -a /home/ubuntu/logs/cron.log

# 3. 크론 상태 확인
echo ""
echo "3️⃣ Cron service status..."
echo "---"
service cron status | grep Active

echo ""
echo "4️⃣ Next cron executions..."
echo "---"
# 다음 실행 시간 계산
current_min=$(date +%M)
next_5min=$((((current_min / 5) + 1) * 5))
if [ $next_5min -ge 60 ]; then
    next_5min=$((next_5min - 60))
fi
next_10min=$((((current_min / 10) + 1) * 10))
if [ $next_10min -ge 60 ]; then
    next_10min=$((next_10min - 60))
fi

echo "⏰ Next status update: $(date +%H):$(printf %02d $next_5min)"
echo "⏰ Next timeout check: $(date +%H):$(printf %02d $next_10min)"
echo "⏰ Next hourly notification: $(date +%H):00 (next hour)"

echo ""
echo "=========================================="
echo "📊 Log Files:"
echo "=========================================="
echo "Main log: /home/ubuntu/logs/cron.log"
echo "Last 5 lines:"
tail -5 /home/ubuntu/logs/cron.log 2>/dev/null || echo "(No logs yet)"

echo ""
echo "=========================================="
echo "✅ Test completed!"
echo "=========================================="
echo ""
echo "📌 Useful commands:"
echo "  Watch logs: tail -f /home/ubuntu/logs/cron.log"
echo "  View cron jobs: crontab -l"
echo "  Edit cron jobs: crontab -e"
echo "  Manual update: docker exec $CONTAINER_NAME python manage.py shell -c \"from api.utils import update_groupbuys_status; print(f'Updated {update_groupbuys_status()} groupbuys')\""