#!/bin/bash

# Docker 컨테이너 정리 및 재시작 스크립트

echo "기존 컨테이너 정리 중..."

# 기존 컨테이너 중지 및 제거
sudo docker-compose -f docker-compose.prod.yml down

# 모든 중지된 컨테이너 제거
sudo docker container prune -f

# 사용하지 않는 이미지 제거 (선택사항)
sudo docker image prune -f

echo "새로운 컨테이너 빌드 및 시작..."
sudo docker-compose -f docker-compose.prod.yml up --build -d

echo "완료! 로그 확인:"
sudo docker-compose -f docker-compose.prod.yml logs --tail=50