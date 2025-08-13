# Docker 컨테이너 내부 Cron 설정 및 로그 관리

## 📋 개요

Docker 컨테이너 ID가 변경되는 문제를 해결하기 위해, cron을 Docker 컨테이너 내부에서 실행하도록 변경했습니다.

## 🚀 배포 방법

### 1. Docker 이미지 빌드 및 실행

```bash
# 기존 컨테이너 정지 및 제거
docker-compose down

# 이미지 재빌드 및 실행
docker-compose up --build -d

# 또는 강제 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### 2. 컨테이너 상태 확인

```bash
# 컨테이너 실행 확인
docker ps | grep dungji-market-backend

# 컨테이너 로그 확인
docker logs dungji-market-backend
```

## 📊 Cron 작업 목록

| 주기 | 작업 | 로그 파일 |
|------|------|-----------|
| 5분마다 | 공구 상태 업데이트 | `/app/logs/cron.log` |
| 10분마다 | 알림 스케줄러 실행 | `/app/logs/notification.log` |
| 매일 03:00 | 만료 데이터 정리 | `/app/logs/cleanup.log` |
| 30분마다 | 참여자 수 동기화 | `/app/logs/sync.log` |
| 1시간마다 | Cron 상태 체크 | `/app/logs/cron.log` |

## 📝 로그 확인 방법

### 방법 1: 대화형 로그 뷰어 사용

```bash
cd /Users/crom/workspace_joshua/dungji-market/backend/scripts
./view_logs.sh
```

메뉴에서 원하는 로그를 선택하여 확인할 수 있습니다:
- 1: Cron 상태 로그 (실시간)
- 2: 알림 로그 (실시간)
- 3: 정리 작업 로그
- 4: 동기화 로그
- 5: Gunicorn 액세스 로그
- 6: Gunicorn 에러 로그
- 7: 모든 Cron 로그 요약
- 8: Cron 작업 상태 확인
- 9: 수동으로 Cron 작업 테스트

### 방법 2: 간단한 로그 명령어 사용

```bash
cd /Users/crom/workspace_joshua/dungji-market/backend/scripts

# Cron 상태 로그 실시간 확인
./logs.sh cron

# 알림 로그 실시간 확인
./logs.sh notification

# 모든 최근 로그 요약
./logs.sh all

# 에러 로그 확인
./logs.sh error
```

### 방법 3: Docker 명령어 직접 사용

```bash
# Cron 로그 실시간 확인
docker exec -it dungji-market-backend tail -f /app/logs/cron.log

# 알림 로그 확인
docker exec -it dungji-market-backend tail -f /app/logs/notification.log

# 최근 50줄 확인
docker exec -it dungji-market-backend tail -n 50 /app/logs/cron.log

# 특정 날짜의 로그 확인
docker exec -it dungji-market-backend grep "2025-01" /app/logs/cron.log
```

## 🔍 Cron 상태 확인

### Cron 서비스 상태 확인

```bash
# Cron 서비스 상태
docker exec -it dungji-market-backend service cron status

# 현재 설정된 Crontab 확인
docker exec -it dungji-market-backend crontab -l
```

### 수동으로 작업 실행 (테스트)

```bash
# 공구 상태 업데이트 수동 실행
docker exec -it dungji-market-backend python manage.py update_groupbuy_status

# 알림 스케줄러 수동 실행
docker exec -it dungji-market-backend python manage.py run_notification_scheduler

# 참여자 수 동기화 수동 실행
docker exec -it dungji-market-backend python manage.py sync_participant_counts
```

## 🛠️ 문제 해결

### Cron이 실행되지 않는 경우

1. 컨테이너 내부에서 cron 서비스 확인:
```bash
docker exec -it dungji-market-backend service cron status
```

2. Cron 서비스 재시작:
```bash
docker exec -it dungji-market-backend service cron restart
```

3. 로그 권한 확인:
```bash
docker exec -it dungji-market-backend ls -la /app/logs/
```

### 로그 파일이 없는 경우

```bash
# 로그 디렉토리 생성
docker exec -it dungji-market-backend mkdir -p /app/logs

# 로그 파일 생성 및 권한 설정
docker exec -it dungji-market-backend touch /app/logs/{cron,notification,cleanup,sync}.log
docker exec -it dungji-market-backend chmod 666 /app/logs/*.log
```

## 📌 주요 변경사항

1. **Container Name 고정**: `dungji-market-backend`로 고정
2. **Cron 내부 실행**: Docker 컨테이너 내부에서 cron 데몬 실행
3. **로그 볼륨**: `logs_volume` 추가로 로그 영속성 보장
4. **Entrypoint 스크립트**: cron과 gunicorn을 동시에 실행

## 🔄 업데이트 프로세스

1. 코드 변경 후 커밋
2. Docker 이미지 재빌드: `docker-compose build`
3. 컨테이너 재시작: `docker-compose up -d`
4. 로그 확인: `./scripts/logs.sh cron`

## 📞 지원

문제가 발생하면 다음을 확인하세요:
- Docker 컨테이너 로그: `docker logs dungji-market-backend`
- Cron 로그: `/app/logs/cron.log`
- Error 로그: `/app/logs/error.log`