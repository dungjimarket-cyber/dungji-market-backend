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
- **해결**: SSH 키 전체를 정확히 복사했는지 확인

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

## 6. 추가 시크릿 (선택사항)

필요에 따라 다음 시크릿도 추가할 수 있습니다:

- `DJANGO_SECRET_KEY`: Django 시크릿 키
- `DB_PASSWORD`: 데이터베이스 비밀번호
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키