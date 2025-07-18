# Dungji Market Backend - 배포 및 자동 재시작 가이드

## 개요
이 문서는 AWS EC2에서 Docker로 실행 중인 Django 애플리케이션의 배포 및 자동 재시작 설정 방법을 설명합니다.

## 환경 구성

### 1. 개발 환경 (Hot Reload 지원)
```bash
# 개발 환경으로 실행 (Django runserver 사용)
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f web
```

### 2. 프로덕션 환경 (Gunicorn 사용)
```bash
# 프로덕션 환경으로 실행
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f web
```

## 자동 재시작 설정

### 방법 1: Git Pull 후 자동 재시작 (추천)
```bash
# 백그라운드에서 자동 재시작 스크립트 실행
nohup ./scripts/auto_reload.sh prod > reload.log 2>&1 &

# 프로세스 확인
ps aux | grep auto_reload.sh

# 로그 확인
tail -f reload.log
```

### 방법 2: 파일 변경 감지 자동 재시작
```bash
# watchdog 설치
pip install -r requirements-dev.txt

# 파일 감지 스크립트 실행
python scripts/watch_reload.py docker-compose.prod.yml
```

### 방법 3: 수동 배포
```bash
# 최신 코드 pull 및 재시작
./scripts/deploy.sh prod

# 이미지 재빌드가 필요한 경우
./scripts/deploy.sh prod --build
```

## systemd 서비스로 등록 (권장)

EC2 인스턴스가 재부팅되어도 자동으로 시작되도록 systemd 서비스로 등록합니다.

### 1. 서비스 파일 생성
```bash
sudo nano /etc/systemd/system/dungji-backend.service
```

### 2. 서비스 내용
```ini
[Unit]
Description=Dungji Market Backend
Requires=docker.service
After=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dungji-market-backend
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. 자동 재시작 서비스 생성
```bash
sudo nano /etc/systemd/system/dungji-backend-reload.service
```

```ini
[Unit]
Description=Dungji Market Backend Auto Reload
Requires=dungji-backend.service
After=dungji-backend.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dungji-market-backend
ExecStart=/home/ubuntu/dungji-market-backend/scripts/auto_reload.sh prod
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### 4. 서비스 활성화
```bash
# 서비스 리로드
sudo systemctl daemon-reload

# 서비스 활성화
sudo systemctl enable dungji-backend.service
sudo systemctl enable dungji-backend-reload.service

# 서비스 시작
sudo systemctl start dungji-backend.service
sudo systemctl start dungji-backend-reload.service

# 상태 확인
sudo systemctl status dungji-backend.service
sudo systemctl status dungji-backend-reload.service
```

## 문제 해결

### Docker 컨테이너가 재시작되지 않는 경우
```bash
# 컨테이너 상태 확인
docker ps -a

# 컨테이너 로그 확인
docker-compose -f docker-compose.prod.yml logs --tail=100 web

# 강제 재시작
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Git pull 권한 문제
```bash
# SSH 키 확인
ssh -T git@github.com

# Git 설정 확인
git config --list
```

### 메모리 부족
```bash
# 메모리 사용량 확인
free -m

# Docker 리소스 정리
docker system prune -a
```

## 모니터링

### 1. 실시간 로그 확인
```bash
# Django 애플리케이션 로그
docker-compose -f docker-compose.prod.yml logs -f web

# Nginx 로그
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### 2. 시스템 리소스 확인
```bash
# CPU 및 메모리 사용량
docker stats

# 디스크 사용량
df -h
```

### 3. 애플리케이션 상태 확인
```bash
# 헬스체크
curl http://localhost:8000/health/

# API 응답 확인
curl http://localhost:8000/api/
```

## 주의사항

1. **환경 변수**: `.env` 파일이 올바르게 설정되어 있는지 확인
2. **볼륨 권한**: Docker 볼륨의 권한 문제가 발생할 수 있으므로 확인 필요
3. **포트 충돌**: 8000, 8080 포트가 사용 중이지 않은지 확인
4. **메모리**: t2.micro 인스턴스의 경우 메모리가 부족할 수 있으므로 swap 설정 권장

## 추가 팁

1. **로그 로테이션 설정**
```bash
# Docker 로그 크기 제한 설정
echo '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

2. **백업 자동화**
```bash
# 데이터베이스 백업 스크립트를 crontab에 추가
0 2 * * * /home/ubuntu/dungji-market-backend/scripts/backup.sh
```

3. **모니터링 알림**
- CloudWatch 또는 Datadog 등의 모니터링 서비스 연동
- 서비스 다운 시 알림 설정