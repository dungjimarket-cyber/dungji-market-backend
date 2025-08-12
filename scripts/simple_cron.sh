#!/bin/bash

# 간단한 버전 - API 엔드포인트 호출 방식
# 서버에서 직접 실행: bash simple_cron.sh

# 크론 작업 추가 (현재 크론탭 유지하면서 추가)
(crontab -l 2>/dev/null; cat << 'EOF'

# Dungji Market - API 엔드포인트 호출 방식
# 5분마다 상태 업데이트
*/5 * * * * curl -X POST http://localhost:8000/api/cron/update-groupbuy-status/ -H "Authorization: Bearer your-secret-token" >> /home/ubuntu/logs/api-cron.log 2>&1

# 1시간마다 알림 발송
0 * * * * curl -X POST http://localhost:8000/api/cron/send-reminders/ -H "Authorization: Bearer your-secret-token" >> /home/ubuntu/logs/api-cron.log 2>&1

EOF
) | crontab -

echo "✅ API 방식 크론 작업이 추가되었습니다."
echo "현재 크론 작업 확인: crontab -l"