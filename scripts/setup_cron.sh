#!/bin/bash

# Ubuntu 서버에서 실행할 크론 설정 스크립트
# 사용법: bash setup_cron.sh

# Docker 컨테이너 이름 자동 감지
CONTAINER_NAME=$(docker ps --format "table {{.Names}}" | grep -E "dungji.*web" | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "Error: Docker container not found!"
    echo "Please make sure the backend container is running."
    exit 1
fi

echo "Found Docker container: $CONTAINER_NAME"

# 크론 작업 파일 생성
cat > /tmp/dungji-cron << EOF
# Dungji Market Backend Cron Jobs
# Container: $CONTAINER_NAME

# 5분마다 공구 상태 업데이트 (모집종료 → 최종선택 → 완료/취소)
*/5 * * * * docker exec $CONTAINER_NAME python manage.py shell -c "from api.utils import update_groupbuys_status; print(f'Updated {update_groupbuys_status()} groupbuys')" >> /home/ubuntu/logs/cron.log 2>&1

# 10분마다 판매자 타임아웃 체크
*/10 * * * * docker exec $CONTAINER_NAME python manage.py shell -c "from api.models import GroupBuy, Bid; from django.utils import timezone; expired = GroupBuy.objects.filter(status='final_selection_seller', seller_selection_end__lt=timezone.now()); count = 0; [gb.save() or count for gb in expired if (gb.status := 'cancelled') and (gb.cancellation_reason := '판매자 최종선택 기간 만료')]; print(f'Cancelled {count} expired groupbuys')" >> /home/ubuntu/logs/cron.log 2>&1

# 1시간마다 알림 발송 (있는 경우)
0 * * * * docker exec $CONTAINER_NAME python manage.py run_notification_scheduler >> /home/ubuntu/logs/notification.log 2>&1

# 매일 새벽 3시 만료 데이터 정리
0 3 * * * docker exec $CONTAINER_NAME python manage.py shell -c "from api.models import PhoneVerification; from django.utils import timezone; from datetime import timedelta; deleted = PhoneVerification.objects.filter(created_at__lt=timezone.now()-timedelta(days=7)).delete()[0]; print(f'Deleted {deleted} old verifications')" >> /home/ubuntu/logs/cleanup.log 2>&1

# 상태 체크용 - 매시간 정각 로그
0 * * * * echo "[\$(date '+\%Y-\%m-\%d \%H:\%M:\%S')] Cron is running" >> /home/ubuntu/logs/cron.log
EOF

# 로그 디렉토리 생성
mkdir -p /home/ubuntu/logs

# 현재 크론탭 백업
crontab -l > /tmp/cron-backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true

# 크론탭에 추가
crontab /tmp/dungji-cron

# 크론 서비스 상태 확인
sudo service cron status

echo "========================================"
echo "✅ Cron jobs have been set up successfully!"
echo "========================================"
echo "Container: $CONTAINER_NAME"
echo "Logs directory: /home/ubuntu/logs/"
echo ""
echo "Log files:"
echo "  - /home/ubuntu/logs/cron.log (상태 업데이트)"
echo "  - /home/ubuntu/logs/notification.log (알림)"
echo "  - /home/ubuntu/logs/cleanup.log (정리 작업)"
echo ""
echo "Commands:"
echo "  View cron jobs: crontab -l"
echo "  Edit cron jobs: crontab -e"
echo "  View logs: tail -f /home/ubuntu/logs/cron.log"
echo "  Test status update: docker exec $CONTAINER_NAME python manage.py shell -c \"from api.utils import update_groupbuys_status; print(f'Updated {update_groupbuys_status()} groupbuys')\""
echo "========================================"