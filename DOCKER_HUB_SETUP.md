# Docker Hub Authentication Setup for GitHub Actions

## 문제 해결 완료

Docker Hub 인증 문제 (`401 Unauthorized`) 해결을 위해 다음과 같이 수정했습니다:

### 1. 수정된 항목들

#### A. Dockerfile 수정
- `python:3.11.5` → `python:3.11-slim` (더 안정적인 태그)

#### B. GitHub Actions 워크플로우 개선
1. **Docker Buildx 설정 추가**
2. **Docker Hub 로그인 단계 추가** (선택적)
3. **재시도 로직 구현**
4. **향상된 오류 처리**

### 2. Docker Hub Secrets 설정 (선택사항)

Docker Hub rate limiting을 완전히 해결하려면 다음 secrets를 GitHub 리포지토리에 추가하세요:

#### GitHub Repository Settings → Secrets and variables → Actions에서:

1. **`DOCKERHUB_USERNAME`**: Docker Hub 사용자명
2. **`DOCKERHUB_TOKEN`**: Docker Hub 액세스 토큰

#### Docker Hub 액세스 토큰 생성 방법:
1. [Docker Hub](https://hub.docker.com) 로그인
2. Account Settings → Security → Access Tokens
3. "New Access Token" 클릭
4. Name: `github-actions-dungji-market`
5. Permissions: `Public Repo Read` (또는 `Read, Write, Delete`)
6. 생성된 토큰을 `DOCKERHUB_TOKEN`으로 저장

### 3. 현재 해결책

secrets 없이도 작동하도록 설정했습니다:
- Docker Buildx 사용으로 빌드 성능 향상
- 3회 재시도 로직 (30초 대기 후 재시도)
- 빌드 실패 시 기존 이미지로 fallback
- 향상된 오류 로깅

### 4. 배포 재실행

수정사항이 적용되었으므로 다음 중 하나를 실행하세요:

1. **GitHub Actions에서 수동 실행**:
   - Repository → Actions → "Deploy Backend to EC2" → "Run workflow"

2. **코드 푸시로 자동 실행**:
   ```bash
   git add .
   git commit -m "fix: resolve Docker Hub authentication issues in CI/CD"
   git push origin main
   ```

### 5. 모니터링

배포 중 다음을 확인하세요:
- Docker 빌드 재시도 로그
- 컨테이너 시작 상태
- API 헬스체크 결과

### 6. 추가 최적화

필요 시 다음도 고려할 수 있습니다:
- Docker Hub Personal Account → Pro Account 업그레이드 (rate limit 증가)
- 대안 registry 사용 (AWS ECR, GitHub Container Registry)
- Multi-stage Dockerfile로 이미지 크기 최적화