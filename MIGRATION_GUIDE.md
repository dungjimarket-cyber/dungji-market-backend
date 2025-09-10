# 마이그레이션 가이드

## 2025년 9월 11일 - 중고폰 거래 시스템 업데이트

### 1. 서버 접속
```bash
ssh -i your-key.pem ubuntu@54.180.82.238
```

### 2. Docker 컨테이너 접속
```bash
docker exec -it dungjimarket-backend-1 bash
```

### 3. 마이그레이션 적용
```bash
# 마이그레이션 확인
python manage.py showmigrations used_phones

# 마이그레이션 적용
python manage.py migrate used_phones

# 적용 확인
python manage.py showmigrations used_phones
```

### 4. 서버 재시작 (필요시)
```bash
# 컨테이너 밖에서 실행
docker-compose restart backend
```

## 새로운 기능
- `is_modified` 필드: 견적 후 수정된 상품 표시
- `UsedPhoneDeletePenalty` 모델: 삭제 패널티 관리
- 제안 금액 최대 990만원 제한

## 주의사항
- 마이그레이션 전 데이터베이스 백업 권장
- 마이그레이션 후 Admin 페이지에서 정상 작동 확인