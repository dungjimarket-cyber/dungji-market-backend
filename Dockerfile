FROM python:3.11.5
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 필요한 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/mediafiles /app/static

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 모든 파일 복사
COPY . /app/

# 정적 파일 수집을 위한 환경 변수 설정
# 빌드 시점에서는 임시 설정 사용
ENV SECRET_KEY=temp_secret_key_for_collectstatic
ENV DEBUG=False
ENV DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ENV DJANGO_SETTINGS_MODULE=dungji_market_backend.settings

# 정적 파일 수집 (빌드 시점에 실행)
RUN python manage.py collectstatic --noinput