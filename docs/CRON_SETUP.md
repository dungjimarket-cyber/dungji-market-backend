# Cron Job 설정 가이드

공구 상태 자동 전환을 위한 cron job 설정 방법입니다.

## 1. 상태 전환 흐름

### 자동 전환되는 상태들:
1. **`recruiting` → `bidding`**: 첫 입찰 발생 시
2. **`bidding` → `final_selection`**: 모집 마감 시간 도달 시 (입찰이 있는 경우)
3. **`recruiting/bidding` → `cancelled`**: 모집 마감 시간 도달 시 (입찰이 없는 경우)
4. **`final_selection` → `completed`**: 모든 최종선택 완료 시
5. **`final_selection` → `cancelled`**: 12시간 타이머 만료 시 (선택 미완료)

## 2. Django 관리 명령어

### 직접 실행
```bash
cd /path/to/dungji-market/backend
python manage.py update_groupbuy_status
```

### 명령어 기능
- 모집 마감된 공구의 최종선택 시작 (12시간 타이머)
- 최종선택 시간 만료된 공구의 판매자 확정 대기 전환
- 판매자 확정 시간 만료된 공구의 완료/취소 처리

## 3. Cron Job 설정

### 방법 1: 시스템 Cron (Linux/macOS)

```bash
# crontab 편집
crontab -e

# 5분마다 실행 (권장)
*/5 * * * * cd /path/to/dungji-market/backend && /path/to/python manage.py update_groupbuy_status >> /path/to/logs/cron.log 2>&1

# 1분마다 실행 (더 정확한 타이밍이 필요한 경우)
* * * * * cd /path/to/dungji-market/backend && /path/to/python manage.py update_groupbuy_status >> /path/to/logs/cron.log 2>&1
```

### 방법 2: Next.js API를 통한 실행

환경변수 설정 (.env.local):
```env
CRON_API_KEY=your-secure-api-key-here
BACKEND_PATH=/path/to/dungji-market/backend
PYTHON_PATH=/path/to/python
```

외부 cron 서비스 (예: cron-job.org)에서 호출:
```bash
curl -X GET "https://your-domain.com/api/cron/update-groupbuy-status" \
  -H "Authorization: Bearer your-secure-api-key-here"
```

### 방법 3: Docker 환경

docker-compose.yml에 별도 스케줄러 서비스 추가:
```yaml
services:
  scheduler:
    build: .
    command: sh -c "while true; do python manage.py update_groupbuy_status; sleep 300; done"
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
```

## 4. 로그 및 모니터링

### 로그 파일 위치
```bash
# 로그 디렉토리 생성
mkdir -p /path/to/logs

# 로그 확인
tail -f /path/to/logs/cron.log
```

### 로그에서 확인할 내용
- 상태 전환된 공구 ID
- 처리 시간
- 에러 메시지

## 5. 운영 환경별 권장 설정

### 개발 환경
- 수동 실행으로 테스트
- 필요시 5분 간격 cron

### 스테이징 환경
- 5분 간격 cron 설정
- 로그 모니터링

### 프로덕션 환경
- 1분 간격 cron 설정 (정확한 타이밍 보장)
- 로그 로테이션 설정
- 알림 시스템 연동

## 6. 트러블슈팅

### 일반적인 문제들

1. **권한 문제**
   ```bash
   # Python 실행 권한 확인
   which python
   # 또는
   which python3
   ```

2. **경로 문제**
   ```bash
   # 절대 경로 사용 권장
   /usr/bin/python3 /full/path/to/manage.py update_groupbuy_status
   ```

3. **환경 변수**
   ```bash
   # crontab에서 환경 변수 설정
   PATH=/usr/local/bin:/usr/bin:/bin
   DJANGO_SETTINGS_MODULE=dungji_market_backend.settings
   ```

### 디버깅 명령어

```bash
# 현재 시간 기준 상태 확인
python manage.py shell -c "
from api.models import GroupBuy
from django.utils import timezone
print('현재 시간:', timezone.now())
print('처리 대상 공구:')
for gb in GroupBuy.objects.exclude(status__in=['completed', 'cancelled']):
    print(f'공구 {gb.id}: {gb.status}, 마감시간: {gb.end_time}, 최종선택마감: {gb.final_selection_end}')
"
```

## 7. 보안 고려사항

1. **API 키 보안**: CRON_API_KEY는 충분히 복잡하게 설정
2. **로그 권한**: 로그 파일 읽기 권한 제한
3. **실행 권한**: 최소 권한으로 실행

## 8. 성능 최적화

- 대량의 공구가 있는 경우 배치 처리 고려
- 데이터베이스 인덱스 최적화
- 로그 레벨 조정 (운영시 INFO 레벨 권장)