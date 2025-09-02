#!/bin/bash

# AWS CLI를 사용한 Dungji Market Staging 서버 자동 설정
# 프리티어 최적화 버전

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정 변수
PROJECT_NAME="dungji-market"
STAGE="staging"
REGION="ap-northeast-2"  # 서울 리전 (프리티어 사용 가능)
INSTANCE_TYPE="t2.micro"  # 프리티어 무료
KEY_NAME="${PROJECT_NAME}-${STAGE}-key"
SECURITY_GROUP_NAME="${PROJECT_NAME}-${STAGE}-sg"
S3_BUCKET="${PROJECT_NAME}-${STAGE}-deployments"
INSTANCE_NAME="${PROJECT_NAME}-${STAGE}-server"

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# AWS CLI 설치 확인
check_aws_cli() {
    log_info "AWS CLI 설치 확인 중..."
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI가 설치되지 않았습니다."
        echo "다음 명령어로 설치하세요:"
        echo "brew install awscli  # macOS"
        echo "sudo apt install awscli  # Ubuntu"
        exit 1
    fi
    
    # AWS 자격 증명 확인
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS 자격 증명이 설정되지 않았습니다."
        echo "다음 명령어로 설정하세요:"
        echo "aws configure"
        exit 1
    fi
    
    log_success "AWS CLI 설정 완료"
}

# VPC ID 가져오기 (기본 VPC 사용)
get_default_vpc() {
    log_info "기본 VPC 정보 가져오는 중..."
    DEFAULT_VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=is-default,Values=true" \
        --query "Vpcs[0].VpcId" \
        --output text \
        --region $REGION)
    
    if [ "$DEFAULT_VPC_ID" == "None" ] || [ -z "$DEFAULT_VPC_ID" ]; then
        log_error "기본 VPC를 찾을 수 없습니다."
        exit 1
    fi
    
    log_success "기본 VPC ID: $DEFAULT_VPC_ID"
}

# 키 페어 생성
create_key_pair() {
    log_info "SSH 키 페어 생성 중..."
    
    # 기존 키 페어 확인
    if aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
        log_warning "키 페어 '$KEY_NAME'이 이미 존재합니다."
        read -p "기존 키를 삭제하고 새로 생성하시겠습니까? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            aws ec2 delete-key-pair --key-name $KEY_NAME --region $REGION
            log_info "기존 키 페어 삭제됨"
        else
            log_info "기존 키 페어 사용"
            return 0
        fi
    fi
    
    # 새 키 페어 생성
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text \
        --region $REGION > ${KEY_NAME}.pem
    
    chmod 400 ${KEY_NAME}.pem
    log_success "키 페어 생성 완료: ${KEY_NAME}.pem"
    log_warning "⚠️  ${KEY_NAME}.pem 파일을 안전한 곳에 백업하세요!"
}

# 보안 그룹 생성
create_security_group() {
    log_info "보안 그룹 생성 중..."
    
    # 기존 보안 그룹 확인
    EXISTING_SG=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
        --query "SecurityGroups[0].GroupId" \
        --output text \
        --region $REGION 2>/dev/null || echo "None")
    
    if [ "$EXISTING_SG" != "None" ] && [ -n "$EXISTING_SG" ]; then
        log_warning "보안 그룹 '$SECURITY_GROUP_NAME'이 이미 존재합니다."
        SECURITY_GROUP_ID=$EXISTING_SG
        log_info "기존 보안 그룹 사용: $SECURITY_GROUP_ID"
        return 0
    fi
    
    # 새 보안 그룹 생성
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for ${PROJECT_NAME} staging server" \
        --vpc-id $DEFAULT_VPC_ID \
        --query 'GroupId' \
        --output text \
        --region $REGION)
    
    log_success "보안 그룹 생성됨: $SECURITY_GROUP_ID"
    
    # 보안 규칙 추가
    log_info "보안 규칙 설정 중..."
    
    # SSH 접근 (현재 IP만 허용)
    CURRENT_IP=$(curl -s https://checkip.amazonaws.com)/32
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 22 \
        --cidr $CURRENT_IP \
        --region $REGION
    
    # HTTP 접근 (전체 허용)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    # HTTPS 접근 (전체 허용)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    # 애플리케이션 포트 8001 (전체 허용)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 8001 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    log_success "보안 규칙 설정 완료"
    log_info "SSH 접근이 현재 IP ($CURRENT_IP)로 제한되었습니다."
}

# S3 버킷 생성
create_s3_bucket() {
    log_info "S3 배포 버킷 생성 중..."
    
    # 기존 버킷 확인
    if aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
        log_warning "S3 버킷 '$S3_BUCKET'이 이미 존재합니다."
        return 0
    fi
    
    # S3 버킷 생성 (ap-northeast-2는 LocationConstraint 필요)
    if [ "$REGION" == "us-east-1" ]; then
        aws s3api create-bucket --bucket $S3_BUCKET --region $REGION
    else
        aws s3api create-bucket \
            --bucket $S3_BUCKET \
            --region $REGION \
            --create-bucket-configuration LocationConstraint=$REGION
    fi
    
    # 버전 관리 활성화
    aws s3api put-bucket-versioning \
        --bucket $S3_BUCKET \
        --versioning-configuration Status=Enabled
    
    log_success "S3 버킷 생성 완료: $S3_BUCKET"
}

# 최신 Ubuntu AMI ID 가져오기
get_latest_ubuntu_ami() {
    log_info "최신 Ubuntu 22.04 LTS AMI 검색 중..."
    
    UBUNTU_AMI_ID=$(aws ec2 describe-images \
        --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
                  "Name=state,Values=available" \
        --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" \
        --output text \
        --region $REGION)
    
    log_success "Ubuntu AMI ID: $UBUNTU_AMI_ID"
}

# EC2 인스턴스 시작
launch_ec2_instance() {
    log_info "EC2 인스턴스 시작 중..."
    
    # 사용자 데이터 스크립트 생성
    cat > user-data.sh << 'EOF'
#!/bin/bash
set -e

# 시스템 업데이트
apt-get update && apt-get upgrade -y

# Docker 설치
apt-get install -y docker.io docker-compose-plugin
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu

# AWS CLI 설치
apt-get install -y awscli

# 필수 패키지 설치
apt-get install -y curl wget unzip git certbot

# 스테이징 디렉토리 생성
mkdir -p /home/ubuntu/dungji-market-staging
chown ubuntu:ubuntu /home/ubuntu/dungji-market-staging

# Docker Compose 최신 버전 설치 (플러그인과 별개)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 시작 완료 로그
echo "EC2 instance setup completed at $(date)" > /home/ubuntu/setup-complete.log
chown ubuntu:ubuntu /home/ubuntu/setup-complete.log
EOF

    # EC2 인스턴스 시작
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $UBUNTU_AMI_ID \
        --count 1 \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $SECURITY_GROUP_ID \
        --user-data file://user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME},{Key=Project,Value=$PROJECT_NAME},{Key=Stage,Value=$STAGE}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $REGION)
    
    log_success "EC2 인스턴스 시작됨: $INSTANCE_ID"
    
    # 인스턴스가 실행될 때까지 대기
    log_info "인스턴스가 실행되기를 기다리는 중..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    
    # 퍼블릭 IP 가져오기
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region $REGION)
    
    log_success "인스턴스 실행 완료!"
    log_info "퍼블릭 IP: $PUBLIC_IP"
    
    # 정리
    rm -f user-data.sh
}

# IAM 역할 생성 (EC2 인스턴스용)
create_iam_role() {
    log_info "IAM 역할 생성 중..."
    
    ROLE_NAME="${PROJECT_NAME}-${STAGE}-ec2-role"
    
    # 기존 역할 확인
    if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
        log_warning "IAM 역할 '$ROLE_NAME'이 이미 존재합니다."
        return 0
    fi
    
    # 신뢰 정책 생성
    cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # IAM 역할 생성
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json
    
    # S3 접근 정책 생성
    cat > s3-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::${S3_BUCKET}/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::${S3_BUCKET}"
        }
    ]
}
EOF

    # 정책을 역할에 연결
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name "${PROJECT_NAME}-${STAGE}-s3-policy" \
        --policy-document file://s3-policy.json
    
    # 인스턴스 프로필 생성
    aws iam create-instance-profile --instance-profile-name $ROLE_NAME
    aws iam add-role-to-instance-profile \
        --instance-profile-name $ROLE_NAME \
        --role-name $ROLE_NAME
    
    log_success "IAM 역할 생성 완료: $ROLE_NAME"
    
    # 정리
    rm -f trust-policy.json s3-policy.json
}

# GitHub Secrets 출력
print_github_secrets() {
    log_info "GitHub Secrets 설정 정보:"
    echo
    echo "다음 secrets를 GitHub 리포지토리에 추가하세요:"
    echo "Settings → Secrets and variables → Actions"
    echo
    echo "AWS_ACCESS_KEY_ID=<your-aws-access-key>"
    echo "AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>"
    echo "S3_DEPLOYMENT_BUCKET=$S3_BUCKET"
    echo "STAGING_HOST=$PUBLIC_IP"
    echo "STAGING_USER=ubuntu"
    echo "STAGING_SSH_KEY=<content-of-${KEY_NAME}.pem>"
    echo "STAGING_SECRET_KEY=<generate-random-secret-key>"
    echo
    echo "SSH 접속 명령어:"
    echo "ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
    echo
    echo "⚠️  주의사항:"
    echo "1. ${KEY_NAME}.pem 파일을 안전한 곳에 백업하세요"
    echo "2. 인스턴스 초기 설정이 완료될 때까지 5-10분 기다려주세요"
    echo "3. 프리티어 사용량을 확인하여 요금이 발생하지 않도록 주의하세요"
}

# 메인 실행 함수
main() {
    log_info "=== AWS Staging Server 자동 설정 시작 ==="
    log_info "프로젝트: $PROJECT_NAME"
    log_info "스테이지: $STAGE"
    log_info "리전: $REGION"
    log_info "인스턴스 타입: $INSTANCE_TYPE (프리티어)"
    echo
    
    check_aws_cli
    get_default_vpc
    create_key_pair
    create_security_group
    create_s3_bucket
    create_iam_role
    get_latest_ubuntu_ami
    launch_ec2_instance
    
    log_success "=== AWS Staging Server 설정 완료! ==="
    echo
    print_github_secrets
}

# 스크립트 실행
main "$@"