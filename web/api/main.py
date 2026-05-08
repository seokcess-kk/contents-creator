"""FastAPI 앱 진입점.

uvicorn web.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application import notifier
from config.settings import settings
from web.api import job_store
from web.api.job_manager import JobManager
from web.api.routers import (
    batches,
    blog_channels,
    brand_studio,
    insights,
    jobs,
    keyword_difficulty,
    pattern_cards,
    performance,
    pipeline,
    rankings,
    results,
    usage,
    ws,
)

# uvicorn 의 기본 로깅은 자기 logger 만 INFO 로 설정하고 root 는 WARNING 으로 둔다.
# 그래서 application.* / web.* 의 logger.info(...) 가 silent 가 되어 cron tick·
# lifespan 시작 로그가 모두 안 보이는 사고가 있었다(2026-04-30/05-01 사후 분석).
# basicConfig 를 명시 호출해 INFO 가 stdout 으로 나가도록 강제한다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

job_manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작/종료 시 리소스 관리.

    순위 수집은 외부 cron(GitHub Actions → POST /api/rankings/check-all)이 정식 경로.
    in-process APScheduler 는 default off, 로컬 개발용으로만 settings 로 토글 가능.
    """
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
        # default False — 로컬 개발자가 명시적으로 켤 때만 in-process cron 동작.
        # 운영(Render)에서는 외부 GitHub Actions cron 을 사용한다.
        from application.scheduler import start_scheduler

        ranking_scheduler = start_scheduler()
        logger.info("ranking.scheduler.in_process_enabled — local dev mode")

    # Phase J1.4 + J2 PR4 — 백엔드 재시작 감지 알림 (orphaned 카운트 통합).
    # in-memory JobManager 가 휘발하면 진행 중 job 상태가 사라지므로 Slack 으로 1회
    # push. webhook 미설정 시 notifier.send_text 가 noop. flag on 이면 자기
    # instance 의 stale running 모두 orphaned 로 마킹하고 그 결과를 같은 메시지에
    # 묶어 알림 dedupe (J1.4 단독 + J2.5 단독으로 2건 발송 회피).
    instance_id = os.environ.get("RENDER_INSTANCE_ID") or socket.gethostname()
    logger.info("startup.restart_detected instance=%s", instance_id)
    orphaned_count = 0
    if settings.job_persistence_enabled:
        try:
            orphaned_count = job_store.mark_running_as_orphaned(instance_id=instance_id)
            if orphaned_count > 0:
                logger.warning(
                    "startup.mark_orphaned instance=%s count=%d", instance_id, orphaned_count
                )
        except Exception:
            logger.exception("startup.mark_orphaned_failed")
    try:
        if orphaned_count > 0:
            notifier.send_text(
                f":arrows_clockwise: *백엔드 재시작 감지* — instance={instance_id} / "
                f"orphaned={orphaned_count}"
            )
        else:
            notifier.send_text(f":arrows_clockwise: *백엔드 재시작 감지* — instance={instance_id}")
    except Exception:
        logger.exception("startup.restart_notify_failed")

    # Phase J2 PR4 — 5분 주기 sweep. flag on 일 때만 task 시작. shutdown 시 cancel.
    sweep_task: asyncio.Task[None] | None = None
    if settings.job_persistence_enabled:
        sweep_task = asyncio.create_task(_orphaned_sweep_loop(), name="job-orphaned-sweep")
        logger.info(
            "startup.orphaned_sweep_started interval=%ss grace=%ss",
            settings.job_sweep_interval_seconds,
            settings.job_orphaned_grace_seconds,
        )

    logger.info("Contents Creator API started")
    yield
    if sweep_task is not None:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task
    job_manager.shutdown()
    # 배치 worker pool 도 정리 — 진행 중 worker 는 wait=False 로 즉시 종료.
    # 진행 중 item 은 DB 에 'running' 으로 남고, 다음 startup 시 stuck 회수가 처리.
    from application.batch_job_manager import shutdown_default_manager

    shutdown_default_manager()
    if ranking_scheduler is not None:
        from application.scheduler import stop_scheduler

        stop_scheduler(ranking_scheduler)
    logger.info("Contents Creator API stopped")


async def _orphaned_sweep_loop() -> None:
    """Phase J2 PR4 — settings.job_sweep_interval_seconds 마다 stale heartbeat
    조회 후 orphaned 마킹. count > 0 시 notifier 알림.

    주의: lifespan 내에서만 시작되므로 설정값은 startup 시점 snapshot 이지만,
    매 tick 마다 settings 재평가 — 운영 중 flag 가 false 로 토글되면 자연 종료.
    Supabase 장애 시 mark_stale_running_as_orphaned 가 0 반환 (graceful) →
    sweep 자체는 계속 동작.
    """
    while True:
        interval = max(60, int(settings.job_sweep_interval_seconds))
        await asyncio.sleep(interval)
        if not settings.job_persistence_enabled:
            logger.info("orphaned_sweep_loop exiting (flag turned off)")
            return
        try:
            count = job_store.mark_stale_running_as_orphaned(
                grace_seconds=settings.job_orphaned_grace_seconds,
            )
        except Exception:
            logger.exception("orphaned_sweep.mark_failed")
            continue
        if count > 0:
            logger.warning("orphaned_sweep.marked count=%d", count)
            try:
                notifier.send_text(
                    f":mag: *orphaned sweep* — {count} job(s) marked orphaned "
                    f"(stale heartbeat > {settings.job_orphaned_grace_seconds}s)"
                )
            except Exception:
                logger.exception("orphaned_sweep.notify_failed")


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
app.include_router(keyword_difficulty.router, prefix="/api")
app.include_router(batches.router, prefix="/api")
app.include_router(pattern_cards.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(performance.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(blog_channels.router, prefix="/api")

# /output 정적 마운트는 인증 우회 통로가 되어 제거. 결과물은 인증된 /api/results/* 로만 접근.


@app.get("/health")
def health() -> dict[str, str]:
    """Render health check / UptimeRobot ping 용. 인증 없이 200 OK.

    DB·외부 API 상태는 의도적으로 확인하지 않는다 — 일시적 외부 장애로 컨테이너가
    재시작되면 in-memory job 상태와 republish 라이프사이클이 끊기므로 liveness 만 본다.
    """
    return {"status": "ok"}
