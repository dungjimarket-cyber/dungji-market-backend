FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Chrome 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.asc https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver 설치
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver*

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