# 🔧 Docker 권한 문제 해결 가이드

## 📊 문제 분석 결과

Git commit 분석을 통해 다음 변경사항들이 권한 문제를 일으켰음을 확인했습니다:

### Breaking Changes 타임라인

1. **commit a4500c8** - Bind mount 제거
   ```diff
   - - .:/app  # 호스트 디렉토리 마운트 제거
   + # bind mount 제거됨
   ```

2. **commit 2183af8** - Container name 제거
   ```diff
   - container_name: dungji-market-backend
   + # container_name: dungji-market-backend  # 주석 처리
   ```

3. **commit 37a38b4** - Migration 로직 이동
   - docker-entrypoint.sh에서 migration 로직 제거
   - deploy.sh로 이동 (하지만 GitHub Actions에서 미사용)

### 근본 원인

**컨테이너 이름 불일치**:
- 서버의 기존 컨테이너: `dungji-market-backend-web-1` (이전 설정)
- 새로 생성하려는 컨테이너: `dungji-backend-web-1` (현재 설정)
- Docker Compose는 이름이 다르면 별개의 컨테이너로 인식
- 기존 컨테이너를 정리하지 못하고 포트 8000 충돌

---

## ✅ 해결 방법

### 방법 1: 즉시 수동 해결 (⭐️ 추천)

서버에 SSH 접속하여 모든 컨테이너를 강제 삭제:

```bash
# 1. SSH 접속
ssh ubuntu@54.180.82.238

# 2. 모든 Docker 컨테이너 강제 종료 및 삭제
sudo docker kill $(sudo docker ps -q) 2>/dev/null || true
sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true

# 3. 네트워크 및 볼륨 정리
sudo docker network prune -f
sudo docker volume prune -f  # ⚠️ 주의: 데이터 손실 가능

# 4. 포트 8000 확인
sudo lsof -i :8000

# 5. 여전히 사용 중이면 프로세스 강제 종료
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# 6. 배포 디렉토리로 이동
cd ~/dungji-market-backend

# 7. 새로운 설정으로 컨테이너 시작
sudo docker-compose -p dungji-backend up --build -d --force-recreate

# 8. 컨테이너 상태 확인
sudo docker-compose -p dungji-backend ps

# 9. 로그 확인
sudo docker-compose -p dungji-backend logs -f web
```

### 방법 2: docker-compose.yml 수정 (영구 해결)

기존 설정과의 호환성을 위해 container_name 복원:

```yaml
services:
  web:
    build: .
    container_name: dungji-backend-web  # 명확한 이름 지정
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
      - logs_volume:/app/logs
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=dungji_market_backend.settings
      - PYTHONUNBUFFERED=1
      - DEBUG=${DEBUG:-False}
      - USE_S3=${USE_S3:-True}
    restart: always

volumes:
  static_volume:
  media_volume:
  logs_volume:
```

**변경 사항:**
- ✅ `container_name: dungji-backend-web` 추가 (일관성)
- ✅ bind mount 제거 유지 (production 권장)
- ✅ named volumes 사용 (데이터 영속성)

### 방법 3: GitHub Actions Workflow 정리

현재 workflow의 정리 로직을 더 강력하게:

```yaml
# 기존 컨테이너 강제 정리 (더 공격적으로)
echo "🧹 Force removing ALL containers..."
sudo docker ps -aq | xargs -r sudo docker rm -f || true

# 특정 이름 패턴의 컨테이너만 정리
sudo docker ps -a --format '{{.Names}}' | grep -E 'dungji|backend' | xargs -r sudo docker rm -f || true

# 새 컨테이너 시작 (프로젝트명 명시)
sudo docker-compose -p dungji-backend up --build -d --force-recreate
```

---

## 🔄 권장 워크플로우

### 1단계: 수동 정리 (한 번만)
```bash
ssh ubuntu@54.180.82.238
sudo docker kill $(sudo docker ps -q) || true
sudo docker rm -f $(sudo docker ps -aq) || true
sudo docker network prune -f
```

### 2단계: docker-compose.yml 수정
```yaml
container_name: dungji-backend-web  # 추가
```

### 3단계: 변경사항 커밋 및 푸시
```bash
git add docker-compose.yml
git commit -m "fix: restore container_name for consistent deployment"
git push origin main
```

### 4단계: GitHub Actions가 자동 배포
- Workflow가 자동 실행됨
- 이제 일관된 컨테이너 이름 사용
- 권한 문제 해결됨

---

## 🎯 검증 체크리스트

배포 후 다음 사항 확인:

- [ ] 컨테이너가 정상 실행 중: `sudo docker ps`
- [ ] 포트 8000 리스닝: `sudo lsof -i :8000`
- [ ] 애플리케이션 응답: `curl http://localhost:8000/api/`
- [ ] S3 설정 확인: 로그에서 `MediaStorage initialized` 확인
- [ ] Migration 완료: 로그에서 migration 성공 메시지 확인

---

## 💡 향후 예방책

### 1. Container Name 일관성 유지
- `container_name`을 명시적으로 지정
- GitHub Actions에서 `-p` 플래그로 같은 프로젝트명 사용

### 2. Deployment Script 통일
- `deploy.sh` 사용 또는 GitHub Actions 사용
- 두 가지를 혼용하지 말 것

### 3. Blue-Green Deployment 고려
```yaml
# 예시: 두 세트의 컨테이너 유지
services:
  web-blue:
    # ...
  web-green:
    # ...
```

### 4. Health Check 추가
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 📞 트러블슈팅

### 문제: 여전히 권한 오류 발생
```bash
# Docker 데몬 재시작
sudo systemctl restart docker

# 권한 확인
sudo usermod -aG docker ubuntu
newgrp docker
```

### 문제: 볼륨 데이터 손실
```bash
# 볼륨 백업 (정리 전)
sudo docker run --rm -v dungji_market_backend_static_volume:/data \
  -v $(pwd):/backup alpine tar czf /backup/static_backup.tar.gz /data

# 볼륨 복원 (필요 시)
sudo docker run --rm -v dungji_market_backend_static_volume:/data \
  -v $(pwd):/backup alpine tar xzf /backup/static_backup.tar.gz -C /
```

### 문제: Migration 오류
```bash
# 컨테이너 내부 접속
sudo docker-compose -p dungji-backend exec web bash

# Migration 상태 확인
python manage.py showmigrations

# 수동 Migration
python manage.py migrate --fake-initial
```

---

## 🎓 학습 포인트

이번 이슈를 통해 배운 것:

1. **Container Naming의 중요성**
   - Docker Compose는 컨테이너 이름으로 lifecycle 관리
   - 이름이 바뀌면 새로운 컨테이너로 인식

2. **Configuration Drift 방지**
   - 코드의 설정과 실행 중인 컨테이너의 설정을 일치시켜야 함
   - 변경 시 기존 컨테이너를 완전히 정리 필요

3. **Deployment Strategy**
   - 점진적 변경보다는 명확한 cutover
   - Blue-Green 또는 Rolling deployment 고려

4. **Monitoring & Logging**
   - Container lifecycle events 모니터링
   - 권한 문제를 조기에 발견할 수 있는 로깅

---

**작성일**: 2025-10-17
**작성자**: Claude Code Analysis
