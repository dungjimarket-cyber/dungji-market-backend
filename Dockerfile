FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 및 파이썬 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# gunicorn 설정
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 실행 명령어
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "dungji_market_backend.wsgi:application"]