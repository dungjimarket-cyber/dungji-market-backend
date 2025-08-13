#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 컨테이너 이름
CONTAINER_NAME="dungji-market-backend"

# 함수: 헤더 출력
print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}   Dungji Market Backend Logs Viewer   ${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

# 함수: 메뉴 표시
show_menu() {
    echo -e "${GREEN}Available log commands:${NC}"
    echo ""
    echo -e "${YELLOW}1.${NC} View Cron Status Log (실시간)"
    echo -e "${YELLOW}2.${NC} View Notification Log (실시간)"
    echo -e "${YELLOW}3.${NC} View Cleanup Log"
    echo -e "${YELLOW}4.${NC} View Sync Log"
    echo -e "${YELLOW}5.${NC} View Gunicorn Access Log"
    echo -e "${YELLOW}6.${NC} View Gunicorn Error Log"
    echo -e "${YELLOW}7.${NC} View ALL Cron Logs (최근 50줄)"
    echo -e "${YELLOW}8.${NC} Check Cron Jobs Status"
    echo -e "${YELLOW}9.${NC} Test Cron Job Manually"
    echo -e "${YELLOW}0.${NC} Exit"
    echo ""
}

# 함수: 로그 확인
view_log() {
    case $1 in
        1)
            echo -e "${BLUE}Viewing Cron Status Log (Ctrl+C to stop)...${NC}"
            docker exec -it $CONTAINER_NAME tail -f /app/logs/cron.log
            ;;
        2)
            echo -e "${BLUE}Viewing Notification Log (Ctrl+C to stop)...${NC}"
            docker exec -it $CONTAINER_NAME tail -f /app/logs/notification.log
            ;;
        3)
            echo -e "${BLUE}Viewing Cleanup Log...${NC}"
            docker exec -it $CONTAINER_NAME cat /app/logs/cleanup.log
            ;;
        4)
            echo -e "${BLUE}Viewing Sync Log...${NC}"
            docker exec -it $CONTAINER_NAME cat /app/logs/sync.log
            ;;
        5)
            echo -e "${BLUE}Viewing Gunicorn Access Log (Ctrl+C to stop)...${NC}"
            docker exec -it $CONTAINER_NAME tail -f /app/logs/access.log
            ;;
        6)
            echo -e "${BLUE}Viewing Gunicorn Error Log (Ctrl+C to stop)...${NC}"
            docker exec -it $CONTAINER_NAME tail -f /app/logs/error.log
            ;;
        7)
            echo -e "${BLUE}Viewing ALL Cron Logs (last 50 lines)...${NC}"
            echo -e "${PURPLE}--- Cron Status Log ---${NC}"
            docker exec -it $CONTAINER_NAME tail -n 10 /app/logs/cron.log
            echo ""
            echo -e "${PURPLE}--- Notification Log ---${NC}"
            docker exec -it $CONTAINER_NAME tail -n 10 /app/logs/notification.log
            echo ""
            echo -e "${PURPLE}--- Cleanup Log ---${NC}"
            docker exec -it $CONTAINER_NAME tail -n 10 /app/logs/cleanup.log
            echo ""
            echo -e "${PURPLE}--- Sync Log ---${NC}"
            docker exec -it $CONTAINER_NAME tail -n 10 /app/logs/sync.log
            ;;
        8)
            echo -e "${BLUE}Checking Cron Jobs Status...${NC}"
            echo ""
            echo -e "${PURPLE}Current crontab configuration:${NC}"
            docker exec -it $CONTAINER_NAME crontab -l
            echo ""
            echo -e "${PURPLE}Cron service status:${NC}"
            docker exec -it $CONTAINER_NAME service cron status
            ;;
        9)
            echo -e "${BLUE}Testing Cron Job Manually...${NC}"
            echo -e "${YELLOW}Select job to test:${NC}"
            echo "1. Update GroupBuy Status"
            echo "2. Run Notification Scheduler"
            echo "3. Sync Participant Counts"
            read -p "Enter choice: " test_choice
            
            case $test_choice in
                1)
                    echo -e "${GREEN}Running update_groupbuy_status...${NC}"
                    docker exec -it $CONTAINER_NAME python manage.py update_groupbuy_status
                    ;;
                2)
                    echo -e "${GREEN}Running notification scheduler...${NC}"
                    docker exec -it $CONTAINER_NAME python manage.py run_notification_scheduler
                    ;;
                3)
                    echo -e "${GREEN}Running sync participant counts...${NC}"
                    docker exec -it $CONTAINER_NAME python manage.py sync_participant_counts
                    ;;
                *)
                    echo -e "${RED}Invalid choice${NC}"
                    ;;
            esac
            ;;
        0)
            echo -e "${GREEN}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
}

# 메인 루프
main() {
    # Docker 컨테이너 실행 확인
    if ! docker ps | grep -q $CONTAINER_NAME; then
        echo -e "${RED}Error: Container '$CONTAINER_NAME' is not running!${NC}"
        echo "Please start the container first with: docker-compose up -d"
        exit 1
    fi

    print_header

    while true; do
        show_menu
        read -p "Enter your choice: " choice
        echo ""
        view_log $choice
        echo ""
        read -p "Press Enter to continue..."
        clear
        print_header
    done
}

# 스크립트 실행
main