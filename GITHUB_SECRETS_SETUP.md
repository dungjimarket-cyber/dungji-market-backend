# GitHub Secrets 설정 가이드

## 1. EC2_HOST 설정

1. GitHub 리포지토리로 이동
2. Settings 탭 클릭
3. 왼쪽 메뉴에서 Secrets and variables > Actions 클릭
4. "New repository secret" 버튼 클릭
5. 다음 정보 입력:
   - Name: `EC2_HOST`
   - Secret: EC2 인스턴스의 퍼블릭 IP 주소 (예: `13.125.123.456`)
   
   **주의사항:**
   - IP 주소만 입력 (http:// 또는 https:// 제외)
   - 포트 번호 제외
   - 공백 없이 입력

## 2. EC2_SSH_KEY 설정

1. 같은 페이지에서 "New repository secret" 버튼 클릭
2. 다음 정보 입력:
   - Name: `EC2_SSH_KEY`
   - Secret: SSH 프라이빗 키 전체 내용

   **SSH 키 복사 방법:**
   ```bash
   # Mac/Linux
   cat ~/.ssh/your-key.pem
   
   # 또는 키 파일이 다른 위치에 있는 경우
   cat /path/to/your-key.pem
   ```

   **주의사항:**
   - 키의 시작(`-----BEGIN RSA PRIVATE KEY-----`)부터 
   - 끝(`-----END RSA PRIVATE KEY-----`)까지 모두 포함
   - 줄바꿈 그대로 유지

   **예시:**
   ```
   -----BEGIN RSA PRIVATE KEY-----
   MIIEpAIBAAKCAQEA...
   ...중간 내용...
   ...나머지 내용...
   -----END RSA PRIVATE KEY-----
   ```

   **중요: SSH 키 형식 확인**
   - OpenSSH 형식 (새로운 형식): `-----BEGIN OPENSSH PRIVATE KEY-----`로 시작
   - RSA 형식 (기존 형식): `-----BEGIN RSA PRIVATE KEY-----`로 시작
   
   **GitHub Actions는 RSA 형식만 지원합니다!** OpenSSH 형식이라면 다음과 같이 변환해야 합니다:
   
   ```bash
   # 1. 먼저 키 형식 확인
   head -1 your-key.pem
   
   # 2. OpenSSH 형식인 경우 RSA 형식으로 변환
   # 주의: 원본 파일이 수정되므로 백업을 먼저 만드세요
   cp your-key.pem your-key.pem.backup
   ssh-keygen -p -m PEM -f your-key.pem
   # 암호를 물어보면 그냥 Enter (빈 암호)
   
   # 3. 변환 확인
   head -1 your-key.pem
   # 출력: -----BEGIN RSA PRIVATE KEY-----
   
   # 4. 또는 새로운 RSA 키 생성
   ssh-keygen -t rsa -b 4096 -m PEM -f new-key.pem -N ""
   ```
   
   **SSH 키 권한 확인**
   ```bash
   # 키 파일 권한이 400이어야 함
   chmod 400 your-key.pem
   ```

## 3. 설정 확인

1. Actions 탭으로 이동
2. 최근 워크플로우 실행 확인
3. "Debug EC2_HOST" 단계에서 "EC2_HOST is set" 메시지 확인

## 4. 일반적인 문제 해결

### 문제: "dial tcp: lookup ***: no such host"
- **원인**: EC2_HOST가 설정되지 않았거나 잘못된 값
- **해결**: EC2_HOST에 올바른 IP 주소 입력

### 문제: "Permission denied (publickey)"
- **원인**: SSH 키가 잘못되었거나 형식이 맞지 않음
- **해결**: 
  1. SSH 키 전체를 정확히 복사했는지 확인
  2. RSA 형식인지 확인 (OpenSSH 형식은 작동하지 않음)
  3. 키 시작과 끝의 공백이나 줄바꿈 확인

### 문제: "ssh: handshake failed: ssh: unable to authenticate"
- **원인**: OpenSSH 형식 키 사용 (GitHub Actions는 RSA 형식만 지원)
- **해결**: 
  1. 위의 "SSH 키 형식 확인" 섹션 참고하여 RSA 형식으로 변환
  2. EC2 인스턴스의 ~/.ssh/authorized_keys에 퍼블릭 키가 있는지 확인
  3. EC2 사용자 이름이 올바른지 확인 (Ubuntu AMI는 'ubuntu', Amazon Linux는 'ec2-user')

### 문제: "Connection refused"
- **원인**: EC2 보안 그룹에서 SSH(22번 포트) 차단
- **해결**: EC2 보안 그룹에서 GitHub Actions IP 또는 모든 IP(0.0.0.0/0)에 대해 22번 포트 열기

## 5. EC2 보안 그룹 설정

1. AWS EC2 콘솔로 이동
2. 인스턴스 선택
3. Security 탭 클릭
4. Security groups 링크 클릭
5. Inbound rules 편집
6. 다음 규칙 추가:
   - Type: SSH
   - Port: 22
   - Source: 0.0.0.0/0 (또는 GitHub Actions IP 범위)
   - Description: GitHub Actions deployment

## 6. SSH 연결 디버깅

만약 여전히 SSH 연결이 실패한다면, EC2에서 다음을 확인하세요:

```bash
# 1. SSH 서비스 상태 확인
sudo systemctl status ssh

# 2. SSH 설정 확인
sudo nano /etc/ssh/sshd_config
# 다음 설정이 있는지 확인:
# PubkeyAuthentication yes
# PasswordAuthentication no

# 3. authorized_keys 파일 확인
ls -la ~/.ssh/
cat ~/.ssh/authorized_keys

# 4. SSH 로그 확인
sudo tail -f /var/log/auth.log

# 5. 수동으로 SSH 연결 테스트 (로컬에서)
ssh -v -i your-key.pem ubuntu@your-ec2-ip
```

## 7. 추가 시크릿 (선택사항)

필요에 따라 다음 시크릿도 추가할 수 있습니다:

- `DJANGO_SECRET_KEY`: Django 시크릿 키
- `DB_PASSWORD`: 데이터베이스 비밀번호
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키