"""APScheduler 래퍼 — 매일 09:00 KST SERP 재크롤.

FastAPI lifespan 에서 시작/종료. SPEC-RANKING.md §3 [수집-스케줄] 참조.

🔴 단일 인스턴스 전제. 멀티 인스턴스 운영 전환 시 advisory lock 필수
(tasks/lessons.md).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from application.ranking_orchestrator import check_all_active_rankings
from config.settings import settings

logger = logging.getLogger(__name__)

_JOB_ID = "ranking_daily_check"


def start_scheduler() -> AsyncIOScheduler:
    """AsyncIOScheduler 시작 + 매일 09:00 KST cron job 등록.

    coalesce=True: 백엔드 재시작으로 누락된 잡은 1회만 보충 실행.
    max_instances=1: 동일 잡 동시 실행 방지 (in-process 한정).
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    trigger = CronTrigger(
        hour=settings.ranking_scheduler_hour,
        minute=settings.ranking_scheduler_minute,
        timezone="Asia/Seoul",
    )
    scheduler.add_job(
        _run_daily_check,
        trigger=trigger,
        id=_JOB_ID,
        name="Ranking daily SERP re-crawl",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "ranking.scheduler.started cron=%02d:%02d KST",
        settings.ranking_scheduler_hour,
        settings.ranking_scheduler_minute,
    )
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    """스케줄러 정지 (lifespan 종료 시 호출). 진행 중 잡은 기다리지 않음."""
    scheduler.shutdown(wait=False)
    logger.info("ranking.scheduler.stopped")


def _run_daily_check() -> None:
    """cron job 본체. 동기 함수 — APScheduler 가 thread executor 로 실행."""
    logger.info("ranking.scheduler.tick — starting daily check")
    try:
        summary = check_all_active_rankings()
        logger.info(
            "ranking.scheduler.tick_done checked=%d found=%d errors=%d",
            summary.checked_count,
            summary.found_count,
            summary.errors_count,
        )
    except Exception:
        # 스케줄러가 중단되지 않도록 광범위 catch + 로깅
        logger.exception("ranking.scheduler.tick_failed — continuing")
