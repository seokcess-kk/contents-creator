FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 먼저 (캐시 활용)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[web]"

# 소스 코드
COPY domain/ domain/
COPY application/ application/
COPY config/ config/
COPY web/api/ web/api/
COPY web/__init__.py web/__init__.py

# output 디렉토리 생성
RUN mkdir -p output

EXPOSE 8000

CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
