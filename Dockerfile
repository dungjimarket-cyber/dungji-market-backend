FROM python:3.11.5
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# cron 설치
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# 필요한 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/mediafiles /app/static /app/logs

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 모든 파일 복사
COPY . /app/

# crontab과 entrypoint 스크립트 복사 및 권한 설정
COPY crontab /app/crontab
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 정적 파일 수집을 위한 환경 변수 설정
# 빌드 시점에서는 임시 설정 사용
ENV SECRET_KEY=temp_secret_key_for_collectstatic
ENV DEBUG=False
ENV DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ENV DJANGO_SETTINGS_MODULE=dungji_market_backend.settings

# 정적 파일 수집 (빌드 시점에 실행)
RUN python manage.py collectstatic --noinput

# Entrypoint 설정
ENTRYPOINT ["/app/docker-entrypoint.sh"]