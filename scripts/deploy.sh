#!/bin/bash

# 배포 스크립트
# AWS EC2에서 실행하여 최신 코드를 배포합니다.

echo "Starting deployment for Dungji Market Backend..."

# 스크립트 실행 위치 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 환경 변수
ENV=${1:-prod}
COMPOSE_FILE="docker-compose.${ENV}.yml"

# Git pull
echo "Pulling latest changes..."
git pull origin main

# Docker Compose로 서비스 재시작
echo "Restarting services with $COMPOSE_FILE..."

# 이미지 재빌드가 필요한 경우
if [ "$2" = "--build" ]; then
    echo "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build
fi

# 서비스 재시작
docker-compose -f $COMPOSE_FILE down
docker-compose -f $COMPOSE_FILE up -d

# 로그 확인
echo "Deployment completed! Checking logs..."
docker-compose -f $COMPOSE_FILE logs --tail=50 web

echo "To view real-time logs, run:"
echo "docker-compose -f $COMPOSE_FILE logs -f web"