#!/bin/bash

# 자동 재시작 스크립트
# Git pull 후 Docker 컨테이너를 자동으로 재시작합니다.

echo "Starting auto-reload script for Dungji Market Backend..."

# 환경 변수 설정
ENV=${1:-prod}  # 기본값은 prod
COMPOSE_FILE="docker-compose.${ENV}.yml"

# Docker Compose 파일 확인
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: $COMPOSE_FILE not found!"
    exit 1
fi

echo "Using Docker Compose file: $COMPOSE_FILE"

# Git repository 확인
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository!"
    exit 1
fi

# 현재 커밋 해시 저장
LAST_COMMIT=$(git rev-parse HEAD)

# 무한 루프로 변경사항 감지
while true; do
    # Git pull
    echo "Checking for updates..."
    git fetch origin main
    
    # 새로운 커밋이 있는지 확인
    CURRENT_COMMIT=$(git rev-parse origin/main)
    
    if [ "$LAST_COMMIT" != "$CURRENT_COMMIT" ]; then
        echo "New commits detected! Pulling changes..."
        
        # 변경사항 pull
        git pull origin main
        
        # requirements.txt가 변경되었는지 확인
        if git diff HEAD@{1} HEAD --name-only | grep -q "requirements.txt"; then
            echo "requirements.txt has changed. Rebuilding Docker image..."
            docker-compose -f $COMPOSE_FILE build web
        fi
        
        # Django 애플리케이션 재시작
        echo "Restarting Django application..."
        docker-compose -f $COMPOSE_FILE restart web
        
        # 마이그레이션 실행
        echo "Running migrations..."
        docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate
        
        # 정적 파일 수집 (프로덕션 환경일 경우)
        if [ "$ENV" = "prod" ]; then
            echo "Collecting static files..."
            docker-compose -f $COMPOSE_FILE exec -T web python manage.py collectstatic --noinput
        fi
        
        # 현재 커밋 해시 업데이트
        LAST_COMMIT=$CURRENT_COMMIT
        
        echo "Update completed successfully!"
    fi
    
    # 30초 대기
    sleep 30
done