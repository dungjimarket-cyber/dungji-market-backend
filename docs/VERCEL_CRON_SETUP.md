# Vercel Cron Jobs 설정 가이드

## 개요
백엔드 서버의 부하를 줄이기 위해 상태 변경 스케줄러를 Vercel Cron Jobs로 이전했습니다.

## 설정 방법

### 1. 환경 변수 설정

#### Django 백엔드 (.env)
```env
# Cron job 인증을 위한 시크릿 토큰
CRON_SECRET_TOKEN=your-secure-random-token-here
```

#### Next.js 프론트엔드 (Vercel 환경 변수)
```env
# Vercel Cron Job이 사용하는 시크릿 (Vercel이 자동 생성)
CRON_SECRET=<Vercel이 자동으로 생성>

# Django 백엔드 인증 토큰 (Django의 CRON_SECRET_TOKEN과 동일해야 함)
CRON_AUTH_TOKEN=your-secure-random-token-here

# 백엔드 API URL
NEXT_PUBLIC_API_URL=https://api.dungjimarket.com
```

### 2. Cron Job 스케줄

현재 설정된 스케줄:
- **상태 업데이트**: 5분마다 실행 (`*/5 * * * *`)
- **리마인더 알림**: 매일 오전 9시, 오후 2시, 오후 6시 (`0 9,14,18 * * *`)

### 3. Vercel 배포

1. `vercel.json` 파일이 프로젝트 루트에 있는지 확인
2. Vercel에 배포: `vercel --prod`
3. Vercel 대시보드에서 환경 변수 설정
4. Cron Jobs 탭에서 실행 상태 확인

### 4. 로컬 테스트

#### Django 백엔드 테스트
```bash
# 상태 업데이트 테스트
curl -X POST http://localhost:8000/api/cron/update-status/ \
  -H "Authorization: Bearer your-secure-random-token-here"

# 리마인더 알림 테스트
curl -X POST http://localhost:8000/api/cron/send-reminders/ \
  -H "Authorization: Bearer your-secure-random-token-here"
```

#### Next.js Cron 핸들러 테스트
```bash
# 로컬에서 실행
curl http://localhost:3000/api/cron/update-status \
  -H "Authorization: Bearer test-cron-secret"
```

### 5. 모니터링

- **Vercel Dashboard**: Functions 탭에서 실행 로그 확인
- **Django Logs**: 백엔드 서버 로그에서 cron job 실행 확인

### 6. 보안 고려사항

1. **토큰 보안**: `CRON_SECRET_TOKEN`은 강력한 랜덤 문자열 사용
2. **HTTPS 필수**: 프로덕션에서는 반드시 HTTPS 사용
3. **IP 제한**: 가능하다면 Vercel IP에서만 접근 허용

### 7. 문제 해결

#### Cron Job이 실행되지 않을 때
1. Vercel Dashboard에서 Cron Jobs 상태 확인
2. 환경 변수가 올바르게 설정되었는지 확인
3. `vercel.json` 파일 경로와 스케줄 확인

#### 인증 오류가 발생할 때
1. Django와 Vercel의 토큰이 일치하는지 확인
2. Authorization 헤더 형식 확인 (`Bearer ` 주의)

#### 백엔드 연결 실패
1. `NEXT_PUBLIC_API_URL`이 올바른지 확인
2. 백엔드 서버가 실행 중인지 확인
3. CORS 설정 확인