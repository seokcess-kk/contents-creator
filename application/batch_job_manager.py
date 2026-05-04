"""키워드 배치 전용 worker pool. SPEC-BATCH.md §3 Phase 1.

단일 `JobManager` (web/api/job_manager.py) 와 분리해 자원 격리:
- 단일 JobManager: 사용자 즉시 단건 — 응답성 우선
- BatchJobManager: 배치 dequeue — 백그라운드 처리

Phase 1 MVP — in-process. 컨테이너 재시작 시 진행 상태는 DB 에 남고,
startup hook 이 30분 이상 갱신 없는 'running' item 을 'queued' 로 복귀.
Phase 3 부터 별도 worker process 로 분리.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from config.settings import settings

logger = logging.getLogger(__name__)


class BatchJobManager:
    """배치 처리 전용 worker pool.

    `submit(fn, *args)` 으로 task 던지고 fanout/완료 추적은 caller 책임.
    Phase 1 은 ThreadPoolExecutor 단순 wrap — 재시작 복구는 DB 가 보장.
    """

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers or settings.batch_max_workers
        self._executor: ThreadPoolExecutor | None = None
        self._lock = threading.Lock()

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def _ensure_executor(self) -> ThreadPoolExecutor:
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="batch-worker",
                )
                logger.info("batch_job_manager.started max_workers=%d", self._max_workers)
        return self._executor

    def submit(self, fn: Callable[..., None], *args: object, **kwargs: object) -> None:
        """sync 함수를 thread pool 에 던짐. 결과·예외는 caller 가 부담.

        본 manager 는 fan-out 만 책임 — 진행 상태는 DB(keyword_batch_items.status)
        가 단일 진실의 원천이라 future 추적 안 함.
        """
        executor = self._ensure_executor()
        executor.submit(_safe_invoke, fn, *args, **kwargs)

    def shutdown(self, wait: bool = False) -> None:
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=wait)
                self._executor = None
                logger.info("batch_job_manager.shutdown wait=%s", wait)


def _safe_invoke(fn: Callable[..., None], *args: object, **kwargs: object) -> None:
    """worker thread 의 모든 예외를 logger.exception 으로 흡수.

    fan-out 후 caller 가 future 를 기다리지 않으므로 raise 가 의미 없음.
    item 단위 실패는 batch_orchestrator 가 DB 의 status='failed' + error 로 기록.
    """
    try:
        fn(*args, **kwargs)
    except Exception:
        logger.exception(
            "batch_job_manager.worker_failed fn=%s args=%r",
            getattr(fn, "__name__", repr(fn)),
            args[:1] if args else (),
        )


# 모듈 레벨 싱글턴 — application 전반에서 재사용
_default_manager: BatchJobManager | None = None
_default_lock = threading.Lock()


def get_default_manager() -> BatchJobManager:
    global _default_manager
    with _default_lock:
        if _default_manager is None:
            _default_manager = BatchJobManager()
        return _default_manager


def shutdown_default_manager() -> None:
    """lifespan 종료 시 호출."""
    global _default_manager
    with _default_lock:
        if _default_manager is not None:
            _default_manager.shutdown(wait=False)
            _default_manager = None
