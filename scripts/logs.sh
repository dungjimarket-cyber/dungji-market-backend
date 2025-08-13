#!/bin/bash

# 간단한 로그 확인 스크립트
# 사용법: ./logs.sh [cron|notification|cleanup|sync|access|error|all]

CONTAINER_NAME="dungji-market-backend"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Docker 컨테이너 실행 확인
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Error: Container '$CONTAINER_NAME' is not running!"
    exit 1
fi

case "$1" in
    cron)
        echo -e "${GREEN}📋 Cron Status Log (live):${NC}"
        docker exec -it $CONTAINER_NAME tail -f /app/logs/cron.log
        ;;
    notification)
        echo -e "${GREEN}🔔 Notification Log (live):${NC}"
        docker exec -it $CONTAINER_NAME tail -f /app/logs/notification.log
        ;;
    cleanup)
        echo -e "${GREEN}🧹 Cleanup Log:${NC}"
        docker exec -it $CONTAINER_NAME tail -n 50 /app/logs/cleanup.log
        ;;
    sync)
        echo -e "${GREEN}🔄 Sync Log:${NC}"
        docker exec -it $CONTAINER_NAME tail -n 50 /app/logs/sync.log
        ;;
    access)
        echo -e "${GREEN}📊 Access Log (live):${NC}"
        docker exec -it $CONTAINER_NAME tail -f /app/logs/access.log
        ;;
    error)
        echo -e "${GREEN}❌ Error Log (live):${NC}"
        docker exec -it $CONTAINER_NAME tail -f /app/logs/error.log
        ;;
    all)
        echo -e "${GREEN}📚 All Recent Logs:${NC}"
        echo -e "${YELLOW}--- Cron (last 10) ---${NC}"
        docker exec $CONTAINER_NAME tail -n 10 /app/logs/cron.log
        echo ""
        echo -e "${YELLOW}--- Notification (last 10) ---${NC}"
        docker exec $CONTAINER_NAME tail -n 10 /app/logs/notification.log
        echo ""
        echo -e "${YELLOW}--- Error (last 10) ---${NC}"
        docker exec $CONTAINER_NAME tail -n 10 /app/logs/error.log
        ;;
    *)
        echo "Usage: $0 [cron|notification|cleanup|sync|access|error|all]"
        echo ""
        echo "Options:"
        echo "  cron         - View cron status log (live)"
        echo "  notification - View notification log (live)"
        echo "  cleanup      - View cleanup log"
        echo "  sync         - View sync log"
        echo "  access       - View gunicorn access log (live)"
        echo "  error        - View gunicorn error log (live)"
        echo "  all          - View all recent logs"
        echo ""
        echo "Example: $0 cron"
        exit 1
        ;;
esac