FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 시스템 빌드 도구 (lxml 등 일부 패키지 컴파일 fallback 대비)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 의존성만 먼저 설치 — pyproject.toml 변경 없으면 이 레이어 캐시
# editable install 이 패키지 메타데이터를 만들 수 있도록 빈 디렉토리·__init__.py 선배치
COPY pyproject.toml ./
RUN mkdir -p domain application config web/api && \
    touch domain/__init__.py application/__init__.py config/__init__.py \
          web/__init__.py web/api/__init__.py && \
    pip install -e ".[web]"

# Playwright Chromium + 시스템 deps (브랜드 카드 PNG 렌더용)
RUN playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# 실제 코드 — 위 레이어들은 그대로 캐시 사용
COPY domain/ domain/
COPY application/ application/
COPY config/ config/
COPY web/__init__.py web/__init__.py
COPY web/api/ web/api/

# output 디렉토리 (휘발성 — Supabase Storage 가 영속 백업, results.py 가 fallback 처리)
RUN mkdir -p output

# Render 는 PORT 환경변수를 동적 주입. 로컬 실행 시 8000 fallback.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn web.api.main:app --host 0.0.0.0 --port ${PORT}"]
