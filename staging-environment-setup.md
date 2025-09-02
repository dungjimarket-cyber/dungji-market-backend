# 🚀 GitHub Environment Secrets 설정 가이드

## 🎯 단일 Secret으로 간편 관리

여러 개의 secrets 대신 하나의 Environment secret으로 모든 설정을 관리하세요!

## 📋 설정 단계

### 1단계: GitHub Environment 생성

1. **Repository** → **Settings** → **Environments** 
2. **New environment** 클릭
3. Environment name: `staging`

### 2단계: STAGING_SECRETS 생성

**staging environment** → **Add secret**

**Secret name**: `STAGING_SECRETS`

**Secret value**:
```bash
# AWS 설정 (기존 .env 파일의 실제 값 사용)
AWS_ACCESS_KEY_ID=your_actual_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_actual_aws_secret_access_key
S3_DEPLOYMENT_BUCKET=dungji-market-staging-deployments
STAGING_HOST=your_ec2_public_ip
STAGING_USER=ubuntu
STAGING_SECRET_KEY=your_generated_django_secret_key
STAGING_SSH_KEY=-----BEGIN RSA PRIVATE KEY-----
your_complete_ssh_private_key_content_here
-----END RSA PRIVATE KEY-----
SLACK_WEBHOOK_URL=your_slack_webhook_url_optional
```

## 🔑 실제 값 얻는 방법

### AWS 자격 증명
```bash
# 기존 .env 파일에서 복사
grep AWS_ACCESS_KEY_ID .env
grep AWS_SECRET_ACCESS_KEY .env
```

### Django Secret Key 생성
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### AWS 인프라 및 SSH 키 생성
```bash
./setup-aws-staging.sh
# 완료 후 나오는 IP와 생성된 .pem 파일 사용
cat dungji-market-staging-key.pem
```

## ✅ 장점

- **관리 편의성**: 하나의 secret만 관리
- **보안성**: GitHub가 모든 값 자동 마스킹  
- **환경 분리**: staging/production 별도 관리
- **팀 협업**: Environment 단위 권한 제어

## 🎯 완료 후

develop 브랜치에 푸시하면 자동으로 staging 서버에 배포됩니다!

```bash
git checkout develop
git push origin develop
```