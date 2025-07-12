# 알림 스케줄러 설정 가이드

이 문서는 둥지마켓의 자동 알림 시스템을 위한 스케줄러 설정 방법을 안내합니다.

## 개요

알림 스케줄러는 다음과 같은 기능을 자동화합니다:

1. 입찰 마감 전 2시간 간격 알림 발송 (12, 10, 8, 6, 4, 2시간 전)
2. 입찰 확정 기한 전 알림 발송
3. 판매자 확정 기한 전 알림 발송
4. 기한 만료된 입찰의 자동 포기 처리
5. 기한 만료된 판매자 확정의 자동 완료 처리

## 설정 방법

### 1. Django Management Command 실행

알림 스케줄러는 Django management command로 구현되어 있으며, 다음 명령어로 실행할 수 있습니다:

```bash
python manage.py run_notification_scheduler
```

### 2. Cron Job 설정 (Linux/macOS)

시스템 cron을 사용하여 주기적으로 스케줄러를 실행하도록 설정할 수 있습니다.

1. crontab 편집:

```bash
crontab -e
```

2. 다음 내용 추가 (5분마다 실행):

```
*/5 * * * * cd /path/to/dungji-market/backend && /path/to/venv/bin/python manage.py run_notification_scheduler >> /path/to/logs/notification_scheduler.log 2>&1
```

### 3. Windows Task Scheduler 설정

Windows 환경에서는 Task Scheduler를 사용하여 주기적으로 스케줄러를 실행하도록 설정할 수 있습니다.

1. Task Scheduler 열기
2. '기본 작업 만들기' 클릭
3. 이름과 설명 입력 (예: "둥지마켓 알림 스케줄러")
4. 트리거 설정: '매일' 선택 후 '반복 간격' 5분으로 설정
5. 동작 설정: '프로그램 시작' 선택 후 다음 정보 입력:
   - 프로그램/스크립트: `C:\path\to\python.exe`
   - 인수 추가: `manage.py run_notification_scheduler`
   - 시작 위치: `C:\path\to\dungji-market\backend`

### 4. Docker 환경 설정

Docker 환경에서는 별도의 컨테이너로 스케줄러를 실행하거나, cron을 포함한 컨테이너를 구성할 수 있습니다.

#### 별도 컨테이너로 실행:

```dockerfile
# Dockerfile.scheduler
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "manage.py", "run_notification_scheduler"]
```

```yaml
# docker-compose.yml에 추가
scheduler:
  build:
    context: ./backend
    dockerfile: Dockerfile.scheduler
  volumes:
    - ./backend:/app
  depends_on:
    - db
    - web
  restart: always
  command: sh -c "while true; do python manage.py run_notification_scheduler; sleep 300; done"
```

## 로깅 및 모니터링

알림 스케줄러의 로그는 Django 로깅 시스템을 통해 기록됩니다. 로그 파일을 정기적으로 확인하여 스케줄러가 정상적으로 작동하는지 모니터링하세요.

## 주의사항

1. 서버 시간대가 올바르게 설정되어 있는지 확인하세요.
2. 이메일 발송 설정(SMTP)이 올바르게 구성되어 있는지 확인하세요.
3. 스케줄러 실행 주기를 너무 짧게 설정하면 시스템 부하가 증가할 수 있습니다.
4. 프로덕션 환경에서는 로그 로테이션을 설정하여 로그 파일이 너무 커지지 않도록 관리하세요.
