"""FastAPI 앱 진입점.

uvicorn web.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from web.api.job_manager import JobManager
from web.api.routers import brand_studio, jobs, rankings, results, usage, ws

logger = logging.getLogger(__name__)

job_manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작/종료 시 리소스 관리. APScheduler 도 lifecycle 에 통합."""
    loop = asyncio.get_running_loop()
    job_manager.set_loop(loop)

    # P0-2: republish_jobs 라이프사이클 동기화 — job 종료 시 자동 finalize
    from application.republish_orchestrator import (
        on_pipeline_job_finished,
        recover_stuck_republish_jobs,
    )

    job_manager.register_on_finished(on_pipeline_job_finished)
    # 서버 재시작 시 in-memory job_manager 와 끊긴 stuck republish_jobs 회수
    try:
        recovered = recover_stuck_republish_jobs()
        if recovered:
            logger.warning("startup.recover_stuck_republish recovered=%d", recovered)
    except Exception:
        logger.exception("startup.recover_stuck_republish failed")

    ranking_scheduler = None
    if settings.ranking_scheduler_enabled:
        from application.scheduler import start_scheduler

        ranking_scheduler = start_scheduler()

    logger.info("Contents Creator API started")
    yield
    job_manager.shutdown()
    if ranking_scheduler is not None:
        from application.scheduler import stop_scheduler

        stop_scheduler(ranking_scheduler)
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
app.include_router(rankings.router, prefix="/api")
app.include_router(brand_studio.router, prefix="/api")

# /output 정적 마운트는 인증 우회 통로가 되어 제거. 결과물은 인증된 /api/results/* 로만 접근.
