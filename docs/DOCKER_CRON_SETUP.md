# Docker 환경에서 Cron Job 설정

Docker 환경에서 공구 상태 자동 전환을 위한 cron job 설정 방법입니다.

## 🚀 설정 방법 (3가지 옵션)

### 방법 1: 간단한 while loop 스케줄러 (현재 적용됨)

**장점**: 설정이 간단, 즉시 적용 가능
**단점**: 정확한 cron 시간 간격은 아님

현재 `docker-compose.yml`에 추가된 `scheduler` 서비스:

```yaml
scheduler:
  build: .
  command: >
    sh -c '
    echo "스케줄러 시작 - 5분마다 공구 상태 업데이트 실행" &&
    while true; do
      echo "$$(date): 공구 상태 업데이트 시작" &&
      python manage.py update_groupbuy_status &&
      echo "$$(date): 공구 상태 업데이트 완료" &&
      sleep 300;
    done'
```

**실행 방법**:
```bash
# 스케줄러 포함하여 재시작
docker-compose up -d --build

# 스케줄러 로그 확인
docker-compose logs -f scheduler
```

### 방법 2: 실제 Cron 사용 스케줄러

**장점**: 정확한 cron 시간 간격, 시스템 표준
**단점**: 설정이 복잡함

**실행 방법**:
```bash
# cron 스케줄러 포함하여 시작
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d --build

# cron 스케줄러 로그 확인
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml logs -f cron-scheduler
```

### 방법 3: 기존 웹 컨테이너에서 직접 실행

**장점**: 별도 컨테이너 불필요
**단점**: 웹 서버와 스케줄러가 같은 프로세스

```bash
# 웹 컨테이너에 접속
docker-compose exec web bash

# 수동으로 cron 실행
python manage.py update_groupbuy_status

# 또는 백그라운드에서 무한 루프 실행
nohup sh -c 'while true; do python manage.py update_groupbuy_status; sleep 300; done' &
```

## 📊 각 방법 비교

| 방법 | 정확성 | 복잡도 | 자원 사용 | 권장도 |
|------|--------|--------|-----------|---------|
| while loop | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **개발/테스트** |
| cron | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **운영** |
| 웹 컨테이너 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **임시** |

## 🔧 현재 권장 설정

**개발/테스트 환경**: 방법 1 (while loop) - 이미 적용됨
**운영 환경**: 방법 2 (cron) 권장

## 📋 실행 및 모니터링

### 현재 설정으로 시작하기
```bash
# Docker 서비스 재시작
docker-compose down
docker-compose up -d --build

# 스케줄러 정상 작동 확인
docker-compose logs scheduler

# 실시간 로그 모니터링
docker-compose logs -f scheduler
```

### 로그에서 확인할 내용
```
scheduler_1  | 스케줄러 시작 - 5분마다 공구 상태 업데이트 실행
scheduler_1  | Thu Aug  1 14:45:00 UTC 2025: 공구 상태 업데이트 시작
scheduler_1  | 공구 상태 업데이트가 완료되었습니다.
scheduler_1  | Thu Aug  1 14:45:01 UTC 2025: 공구 상태 업데이트 완료
```

### 수동 실행 (테스트용)
```bash
# 스케줄러 컨테이너에서 수동 실행
docker-compose exec scheduler python manage.py update_groupbuy_status
```

## 🔍 트러블슈팅

### 1. 스케줄러 서비스가 시작되지 않는 경우
```bash
# 컨테이너 상태 확인
docker-compose ps

# 에러 로그 확인
docker-compose logs scheduler

# 컨테이너 재시작
docker-compose restart scheduler
```

### 2. 환경 변수 문제
```bash
# 환경 변수 확인
docker-compose exec scheduler env | grep DJANGO

# .env 파일 확인
cat .env
```

### 3. 데이터베이스 연결 문제
```bash
# Django 설정 테스트
docker-compose exec scheduler python manage.py check

# 데이터베이스 마이그레이션 상태 확인
docker-compose exec scheduler python manage.py showmigrations
```

## ⚙️ 커스터마이제이션

### 실행 간격 변경
```yaml
# 1분 간격으로 변경
sleep 60;

# 10분 간격으로 변경  
sleep 600;
```

### 타임존 설정
```yaml
environment:
  - TZ=Asia/Seoul
```

### 로그 레벨 조정
```yaml
environment:
  - DJANGO_LOG_LEVEL=INFO
```

## 🔒 보안 고려사항

1. **컨테이너 권한**: 최소 권한으로 실행
2. **환경 변수**: 민감한 정보는 Docker secrets 사용
3. **로그 관리**: 로그 로테이션 설정

## 📈 성능 최적화

1. **메모리 제한**: 스케줄러 컨테이너에 메모리 제한 설정
2. **CPU 제한**: CPU 사용량 제한
3. **볼륨 최적화**: 불필요한 볼륨 마운트 제거

```yaml
scheduler:
  # 리소스 제한 추가
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
```

## 🚀 다음 단계

1. **현재 설정으로 테스트**: `docker-compose up -d --build`
2. **로그 모니터링**: `docker-compose logs -f scheduler`
3. **운영 환경**: cron 방식으로 업그레이드 고려