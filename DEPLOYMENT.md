# 둥지마켓 백엔드 배포 가이드

## GitHub Actions 설정

### 1. GitHub Secrets 설정

GitHub 리포지토리의 Settings > Secrets and variables > Actions에서 다음 시크릿을 추가해야 합니다:

- `EC2_HOST`: EC2 인스턴스의 퍼블릭 IP 주소 (예: 54.180.82.238)
- `EC2_SSH_KEY`: EC2 접속용 SSH 프라이빗 키 (전체 내용 복사)
- `ENV_FILE`: 전체 .env 파일 내용 (아래 예시 참조)

### 2. EC2 서버 초기 설정

```bash
# 1. SSH로 EC2 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. 필요한 패키지 설치
sudo apt update
sudo apt install -y docker.io docker-compose

# 3. ubuntu 사용자를 docker 그룹에 추가
sudo usermod -aG docker ubuntu

# 4. 로그아웃 후 재접속

# 5. 프로젝트 디렉토리 생성
mkdir -p ~/dungji-market-backend

# 6. .env 파일 생성
cd ~/dungji-market-backend
nano .env
```

### 3. .env 파일 내용

```env
# Django 기본 설정
SECRET_KEY=your-secret-key-here
DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,54.180.82.238,api.dungjimarket.com,dungjimarket.com

# Database
DB_NAME=dungji_market
DB_USER=postgres
DB_PASSWORD=your-strong-password
DB_HOST=db
DB_PORT=5432

# AWS S3 (선택사항)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=ap-northeast-2

# Email (선택사항)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-client-id
KAKAO_CLIENT_SECRET=your-kakao-client-secret

# 환경 설정
ENVIRONMENT=production
```

### 4. 배포 프로세스

1. `main` 브랜치에 코드 푸시
2. GitHub Actions가 자동으로 실행
3. 코드가 EC2로 복사됨
4. Docker Compose로 서비스 재시작
5. 마이그레이션 및 정적 파일 수집

### 5. 수동 배포 명령어

```bash
# EC2에서 직접 배포하는 경우
cd ~/dungji-market-backend
git pull origin main
docker-compose down
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```

### 6. 문제 해결

#### ALLOWED_HOSTS 오류 해결

만약 "Invalid HTTP_HOST header" 오류가 발생하면:

```bash
# EC2에 SSH 접속
ssh -i your-key.pem ubuntu@54.180.82.238

# .env 파일 수정
cd ~/dungji-market-backend
nano .env

# DJANGO_ALLOWED_HOSTS에 IP 또는 도메인 추가
# 예: DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,54.180.82.238,api.dungjimarket.com

# 컨테이너 재시작
docker-compose restart web
```

### 7. 로그 확인

```bash
# 전체 로그
docker-compose logs

# 웹 서비스 로그
docker-compose logs web

# 실시간 로그
docker-compose logs -f
```

### 7. 문제 해결

```bash
# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 재시작
docker-compose restart web

# 데이터베이스 접속
docker-compose exec db psql -U postgres -d dungji_market

# Django 셸 접속
docker-compose exec web python manage.py shell
```

### 8. SSL 인증서 설정 (Let's Encrypt)

```bash
# 초기 인증서 발급
sudo certbot certonly --webroot -w /var/www/certbot -d your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 추가: 0 0 * * * certbot renew --quiet
```

## 주의사항

1. `.env` 파일은 절대 Git에 커밋하지 마세요
2. EC2 보안 그룹에서 필요한 포트(80, 443, 8000)를 열어두세요
3. 정기적으로 서버 업데이트를 수행하세요
4. 백업 정책을 수립하고 실행하세요