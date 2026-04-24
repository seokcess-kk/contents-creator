"""scheduler 단위 테스트.

AsyncIOScheduler 는 running event loop 가 필요하므로 asyncio 컨텍스트에서 실행.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from application import scheduler


def test_start_scheduler_registers_cron_job() -> None:
    """매일 09:00 KST cron 트리거가 등록되는지 검증."""

    async def _run() -> None:
        sched = scheduler.start_scheduler()
        try:
            jobs = sched.get_jobs()
            assert len(jobs) == 1
            job = jobs[0]
            assert job.id == "ranking_daily_check"
            assert str(job.trigger.timezone) == "Asia/Seoul"
            assert job.coalesce is True
            assert job.max_instances == 1
        finally:
            scheduler.stop_scheduler(sched)

    asyncio.run(_run())


def test_stop_scheduler_does_not_raise() -> None:
    """shutdown(wait=False) 가 예외 없이 호출되는지만 확인.

    AsyncIOScheduler.running flag 는 shutdown 비동기 처리 후 갱신되므로
    동기 검증 어려움. SPEC-RANKING.md §10 8 참조.
    """

    async def _run() -> None:
        sched = scheduler.start_scheduler()
        scheduler.stop_scheduler(sched)  # 예외 없으면 통과

    asyncio.run(_run())


def test_run_daily_check_invokes_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """_run_daily_check 가 check_all_active_rankings 를 호출하는지."""
    mock_check = MagicMock()
    mock_check.return_value = MagicMock(checked_count=2, found_count=1, errors_count=0)
    monkeypatch.setattr(scheduler, "check_all_active_rankings", mock_check)
    scheduler._run_daily_check()
    mock_check.assert_called_once()


def test_run_daily_check_swallows_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """orchestrator 예외가 스케줄러를 죽이지 않도록 광범위 catch."""

    def boom() -> None:
        raise RuntimeError("test boom")

    monkeypatch.setattr(scheduler, "check_all_active_rankings", boom)
    # 예외가 raise 되지 않아야 함
    scheduler._run_daily_check()
