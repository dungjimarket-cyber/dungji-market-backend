#!/bin/bash
# Emergency Docker Fix Script
# 권한 문제로 컨테이너를 제거할 수 없을 때 사용

set -e

echo "🚨 Emergency Docker Fix Script"
echo "================================"
echo ""

# 현재 상태 확인
echo "📊 Current Docker status:"
sudo docker ps -a
echo ""

# Docker 데몬 재시작
echo "🔄 Restarting Docker daemon..."
sudo systemctl restart docker

# 재시작 대기
echo "⏳ Waiting for Docker daemon to restart..."
sleep 5

# Docker 데몬 상태 확인
echo "✅ Docker daemon status:"
sudo systemctl status docker --no-pager | head -10
echo ""

# 컨테이너 확인
echo "📊 Checking containers after restart:"
sudo docker ps -a
echo ""

# 만약 여전히 컨테이너가 있으면
if sudo docker ps -aq | grep -q .; then
    echo "🧹 Found containers, removing all..."
    sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true
else
    echo "✅ No containers found"
fi

# 네트워크 정리
echo "🧹 Cleaning up networks..."
sudo docker network prune -f

# 볼륨 리스트 (삭제하지 않음)
echo "📦 Available volumes:"
sudo docker volume ls
echo ""

# 포트 확인
echo "🔍 Checking port 8000..."
if sudo lsof -i :8000; then
    echo "⚠️  Port 8000 is still in use by process above"
    echo "Attempting to kill process..."
    sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true
    sleep 2
else
    echo "✅ Port 8000 is available"
fi
echo ""

# 디렉토리 확인
echo "📁 Checking deployment directory..."
if [ ! -d ~/dungji-market-backend ]; then
    echo "❌ Directory ~/dungji-market-backend not found!"
    exit 1
fi

cd ~/dungji-market-backend

# 파일 확인
if [ ! -f docker-compose.yml ]; then
    echo "❌ docker-compose.yml not found!"
    exit 1
fi

if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
fi

# 최종 상태
echo "✅ Ready to deploy!"
echo ""
echo "To deploy, run:"
echo "  cd ~/dungji-market-backend"
echo "  sudo docker-compose up --build -d --force-recreate"
echo ""
echo "To monitor logs:"
echo "  sudo docker logs -f dungji-backend-web"
