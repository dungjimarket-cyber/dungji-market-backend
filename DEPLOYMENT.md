# Dungji Market Backend 배포 가이드

## AWS Docker 배포 문제 해결

### 1. 현재 로그에서 발견된 문제들

1. **반복되는 초기화 로그**
   - 원인: Gunicorn의 각 워커가 모듈을 로드할 때마다 모듈 레벨 로깅이 실행됨
   - 해결: DEBUG 모드에서만 로깅하도록 수정됨

2. **개발 환경으로 실행**
   - 원인: DJANGO_ENV가 'development'로 설정됨
   - 해결: .env.production 파일 사용 및 DJANGO_ENV=production 설정

3. **"Not Found: /" 경고**
   - 원인: 루트 경로에 대한 엔드포인트가 없음
   - 해결: 헬스체크 엔드포인트 추가

### 2. 프로덕션 배포 준비

#### 2.1 환경 변수 설정
```bash
# .env.production 파일을 복사하고 실제 값으로 수정
cp .env.production .env
```

주요 설정:
- `DEBUG=False`
- `DJANGO_ENV=production`
- `ALLOWED_HOSTS=your-domain.com,www.your-domain.com`
- `DATABASE_URL` - PostgreSQL 권장
- `AWS_*` - S3 설정
- `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET` - 카카오 앱 설정에서 프로덕션 URL 추가 필요

#### 2.2 카카오 로그인 설정
1. [카카오 개발자 콘솔](https://developers.kakao.com) 접속
2. 앱 설정 > 플랫폼 > Web 플랫폼 등록
   - 사이트 도메인: `https://your-domain.com`
3. 앱 설정 > 카카오 로그인
   - Redirect URI: `https://your-domain.com/api/auth/callback/kakao`

### 3. Docker 배포

#### 3.1 프로덕션용 Docker Compose 사용
```bash
# 프로덕션 환경에서 실행
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 재시작
docker-compose -f docker-compose.prod.yml restart
```

#### 3.2 Nginx 설정 수정
`nginx.prod.conf` 파일에서 도메인 변경:
```nginx
server_name your-domain.com www.your-domain.com;
```

### 4. SSL 인증서 설정 (Let's Encrypt)

```bash
# Certbot 설치 및 인증서 발급
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d your-domain.com -d www.your-domain.com
```

인증서 발급 후 `nginx.prod.conf`의 HTTPS 섹션 주석 해제

### 5. 데이터베이스 마이그레이션

```bash
# 컨테이너 내부에서 실행
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 6. 정적 파일 수집

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 7. 모니터링 및 로그

#### 7.1 로그 확인
```bash
# 전체 로그
docker-compose -f docker-compose.prod.yml logs

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.prod.yml logs nginx

# 실시간 로그
docker-compose -f docker-compose.prod.yml logs -f
```

#### 7.2 헬스체크
```bash
curl http://your-domain.com/
# 응답: {"status": "ok", "service": "dungji-market-backend"}
```

### 8. 문제 해결

#### 8.1 502 Bad Gateway
- Gunicorn이 실행 중인지 확인
- `docker-compose -f docker-compose.prod.yml ps`

#### 8.2 정적 파일이 로드되지 않음
- 정적 파일 수집 확인
- Nginx 볼륨 마운트 확인

#### 8.3 카카오 로그인 실패
- ALLOWED_HOSTS 설정 확인
- 카카오 앱의 Redirect URI 설정 확인
- CORS 설정 확인

#### 8.4 CORS 오류
**증상**: "Access to fetch at 'https://api.dungjimarket.com/...' from origin 'https://dungjimarket.com' has been blocked by CORS policy"

**해결방법**:
1. Django settings.py에서 CORS_ALLOWED_ORIGINS 확인:
   ```python
   CORS_ALLOWED_ORIGINS = [
       "https://dungjimarket.com",
       "https://www.dungjimarket.com",
       # 다른 허용된 도메인들...
   ]
   ```

2. Nginx에서 CORS 헤더를 추가하지 않도록 확인 (Django가 처리하도록 함)
   - `nginx.prod.conf`에서 `add_header 'Access-Control-Allow-Origin'` 제거

3. Django 재시작:
   ```bash
   docker-compose -f docker-compose.prod.yml restart web
   ```

4. 캐시 문제인 경우:
   - 브라우저 캐시 지우기
   - Django 서버 재시작
   - Nginx 재시작

### 9. 성능 최적화

#### 9.1 Gunicorn 워커 수 조정
```yaml
# docker-compose.prod.yml
command: gunicorn ... --workers 3  # CPU 코어 수 × 2 + 1
```

#### 9.2 Redis 캐싱 추가 (선택사항)
```yaml
redis:
  image: redis:alpine
  restart: always
  networks:
    - dungji_network
```

### 10. 백업

#### 10.1 데이터베이스 백업
```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U username dbname > backup.sql
```

#### 10.2 미디어 파일 백업
```bash
docker run --rm -v dungji-market_media_volume:/data -v $(pwd):/backup alpine tar czf /backup/media-backup.tar.gz -C /data .
```