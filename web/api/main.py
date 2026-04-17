"""FastAPI 앱 진입점.

uvicorn web.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from web.api.job_manager import JobManager
from config.settings import settings
from web.api.routers import jobs, results, usage, ws

logger = logging.getLogger(__name__)

job_manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작/종료 시 리소스 관리."""
    loop = asyncio.get_running_loop()
    job_manager.set_loop(loop)
    logger.info("Contents Creator API started")
    yield
    job_manager.shutdown()
    logger.info("Contents Creator API stopped")


app = FastAPI(
    title="Contents Creator API",
    description="네이버 SEO 원고 생성 파이프라인 웹 UI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — Next.js 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터
app.include_router(jobs.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(usage.router, prefix="/api")

# output/ 정적 파일 (폴백 접근)
try:
    app.mount("/output", StaticFiles(directory="output"), name="output")
except RuntimeError:
    logger.warning("output/ directory not found, static mount skipped")
