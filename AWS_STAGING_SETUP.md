# AWS Staging Server 자동 설정 가이드

## 🚀 한 번에 AWS 스테이징 서버 구축하기

이 가이드는 AWS CLI를 사용해서 던지마켓 스테이징 서버를 프리티어로 완전 자동화 구축하는 방법을 설명합니다.

## 📋 사전 준비사항

### 1. AWS 계정 및 CLI 설정
```bash
# AWS CLI 설치 (macOS)
brew install awscli

# AWS CLI 설치 (Ubuntu)
sudo apt install awscli

# AWS 자격 증명 설정
aws configure
# AWS Access Key ID: [입력]
# AWS Secret Access Key: [입력]  
# Default region name: ap-northeast-2
# Default output format: json
```

### 2. 프리티어 확인
- EC2 t2.micro 인스턴스: 월 750시간 무료
- S3 스토리지: 5GB 무료
- 데이터 전송: 15GB 무료

## 🎯 자동 설정 실행

```bash
# 실행 권한 부여
chmod +x setup-aws-staging.sh

# 자동 설정 시작
./setup-aws-staging.sh
```

## 📦 자동으로 생성되는 리소스

### 🔧 인프라 리소스
- **EC2 인스턴스**: t2.micro (프리티어)
- **보안 그룹**: HTTP/HTTPS/SSH 접근 설정
- **키 페어**: SSH 접속용 (.pem 파일)
- **S3 버킷**: 배포 파일 저장용
- **IAM 역할**: EC2에서 S3 접근 권한

### 🛡️ 보안 설정
- SSH 접근: 현재 IP만 허용
- HTTP/HTTPS: 전체 허용 (80, 443 포트)
- 애플리케이션: 전체 허용 (8001 포트)

### 📱 자동 설치 소프트웨어
- Docker & Docker Compose
- AWS CLI  
- 필수 패키지 (curl, wget, git, certbot)

## 🔑 GitHub Secrets 설정

스크립트 실행 후 출력되는 정보를 GitHub에 등록하세요:

```bash
# GitHub Repository → Settings → Secrets and variables → Actions

AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_DEPLOYMENT_BUCKET=dungji-market-staging-deployments
STAGING_HOST=your_ec2_public_ip
STAGING_USER=ubuntu
STAGING_SSH_KEY=contents_of_pem_file
STAGING_SECRET_KEY=generate_random_key
```

## 📋 설정 완료 후 작업

### 1. SSH 접속 확인
```bash
ssh -i dungji-market-staging-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### 2. 도메인 설정 (선택사항)
```bash
# Route 53에서 도메인 설정
# staging-api.dungjimarket.com → EC2 Public IP

# SSL 인증서 발급 (서버에서 실행)
sudo certbot certonly --standalone -d staging-api.dungjimarket.com
```

### 3. 첫 배포 테스트
```bash
# develop 브랜치에 커밋하면 자동 배포
git checkout develop
git add .
git commit -m "test: trigger staging deployment"  
git push origin develop
```

## 💰 프리티어 비용 최적화

### ✅ 무료 사용량
- **t2.micro 인스턴스**: 월 750시간 (24/7 운영 가능)
- **EBS 볼륨**: 30GB까지 무료
- **S3 저장소**: 5GB까지 무료
- **데이터 전송**: 15GB/월까지 무료

### ⚠️ 비용 발생 주의사항
```bash
# 1. 인스턴스 중지 (비용 절약)
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# 2. 인스턴스 시작
aws ec2 start-instances --instance-ids i-1234567890abcdef0

# 3. 완전 삭제 (더 이상 사용 안 할 때)
aws ec2 terminate-instances --instance-ids i-1234567890abcdef0
```

### 📊 비용 모니터링
1. **AWS Billing Dashboard** 정기 확인
2. **CloudWatch 알림** 설정 (월 $1 이상 시 알림)
3. **프리티어 사용량 추적** 대시보드 활용

## 🔧 문제 해결

### SSH 접속 실패
```bash
# 보안 그룹 확인
aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx

# 현재 IP 확인 및 업데이트
CURRENT_IP=$(curl -s https://checkip.amazonaws.com)/32
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 22 \
    --cidr $CURRENT_IP
```

### 인스턴스 상태 확인
```bash
# 인스턴스 상태 확인
aws ec2 describe-instances --instance-ids i-xxxxxxxxx

# 시스템 로그 확인
aws ec2 get-console-output --instance-id i-xxxxxxxxx
```

### S3 배포 실패
```bash
# S3 버킷 권한 확인
aws s3api get-bucket-policy --bucket dungji-market-staging-deployments

# IAM 역할 확인
aws iam get-role --role-name dungji-market-staging-ec2-role
```

## 🎯 완료 확인 체크리스트

- [ ] EC2 인스턴스 정상 실행
- [ ] SSH 접속 가능
- [ ] Docker 설치 확인
- [ ] S3 버킷 생성 확인
- [ ] GitHub Secrets 등록
- [ ] GitHub Actions 배포 테스트
- [ ] Health check 엔드포인트 확인 (`http://PUBLIC_IP:8001/api/health/`)

## 🔄 유지보수

### 정기 작업
- **월 1회**: AWS 프리티어 사용량 확인
- **주 1회**: 보안 업데이트 적용
- **필요시**: SSL 인증서 갱신 (Let's Encrypt)

### 백업 및 복구
```bash
# EC2 스냅샷 생성
aws ec2 create-snapshot --volume-id vol-xxxxxxxxx --description "staging-backup-$(date +%Y%m%d)"

# S3 버킷 백업
aws s3 sync s3://dungji-market-staging-deployments ./backups/
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. AWS 프리티어 한도 확인
2. 보안 그룹 설정 확인  
3. GitHub Actions 로그 확인
4. EC2 인스턴스 상태 및 로그 확인

---

**🎉 축하합니다!** 
이제 완전 자동화된 AWS 스테이징 서버가 구축되었습니다. 
develop 브랜치에 코드를 푸시하면 자동으로 배포가 진행됩니다!