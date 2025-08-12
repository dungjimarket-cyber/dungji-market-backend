# 둥지마켓 자동 상태 업데이트 스케줄러 설정

## 개요
둥지마켓에서는 다음과 같은 자동 처리가 필요합니다:
- 공구 마감 시간 도달 시 자동으로 최종선택 단계로 전환
- 구매자 최종선택 12시간 만료 시 자동 처리
- **판매자 최종선택 6시간 만료 시 자동 판매포기 처리**
- 거래 상태 자동 업데이트

## 스케줄러 실행 방법

### 방법 1: Django 관리 명령어 (개발/테스트용)
수동으로 한 번 실행:
```bash
cd /Users/crom/workspace_joshua/dungji-market/backend
python manage.py update_groupbuy_status
```

### 방법 2: 내장 스케줄러 사용 (권장)
백그라운드에서 지속적으로 실행:
```bash
cd /Users/crom/workspace_joshua/dungji-market/backend
# 5분(300초)마다 실행
python manage.py run_scheduler --interval 300
```

### 방법 3: Crontab 설정 (프로덕션)
```bash
# 크론탭 설정 스크립트 실행
cd /Users/crom/workspace_joshua/dungji-market/backend
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh

# 또는 수동으로 크론탭 편집
crontab -e
# 다음 줄 추가 (10분마다 실행)
*/10 * * * * cd /path/to/backend && python manage.py update_groupbuy_status >> logs/cron_groupbuy_status.log 2>&1
```

### 방법 4: Systemd 서비스 (프로덕션 서버)
```bash
# 서비스 파일 복사
sudo cp scripts/dungji-scheduler.service /etc/systemd/system/

# 서비스 파일 경로 수정 (필요시)
sudo nano /etc/systemd/system/dungji-scheduler.service

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable dungji-scheduler
sudo systemctl start dungji-scheduler

# 상태 확인
sudo systemctl status dungji-scheduler
```

## 자동 처리 로직

### 1. 공구 마감 → 구매자 최종선택 (12시간)
- 공구 마감 시간 도달 시 `final_selection_buyers` 상태로 전환
- 12시간 타이머 시작

### 2. 구매자 최종선택 만료 → 판매자 최종선택 (6시간)
- 구매확정자가 1명 이상이면 `final_selection_seller` 상태로 전환
- 6시간 타이머 시작
- 모두 포기 시 공구 자동 취소

### 3. 판매자 최종선택 만료 → 자동 판매포기
- **6시간 내 미선택 시 자동으로 판매포기(`rejected`) 처리**
- 판매포기 시 공구 취소(`cancelled`) 상태로 변경
- 확정률 50% 이하인 경우 패널티 없음

## 로그 확인
```bash
# 스케줄러 로그
tail -f /Users/crom/workspace_joshua/dungji-market/backend/logs/scheduler.log

# 크론 실행 로그
tail -f /Users/crom/workspace_joshua/dungji-market/backend/logs/cron_groupbuy_status.log
```

## 문제 해결

### 스케줄러가 실행되지 않는 경우
1. Python 경로 확인: `which python3`
2. Django 설정 확인: `DJANGO_SETTINGS_MODULE` 환경변수
3. 로그 디렉토리 권한 확인: `ls -la logs/`

### 자동 처리가 되지 않는 경우
1. 수동 실행으로 테스트: `python manage.py update_groupbuy_status`
2. 데이터베이스 시간대 설정 확인
3. `seller_selection_end` 필드값 확인

## 주의사항
- 스케줄러는 하나의 인스턴스만 실행되어야 합니다
- 프로덕션 환경에서는 systemd 또는 supervisor 사용 권장
- 로그 파일 크기 관리 필요 (logrotate 설정)