"""BatchJobManager — fan-out worker pool 테스트."""

from __future__ import annotations

import threading
import time

import pytest

from application.batch_job_manager import BatchJobManager


def test_submit_runs_function_in_thread() -> None:
    """submit 한 함수가 thread pool 에서 실행."""
    called = threading.Event()

    def task() -> None:
        called.set()

    manager = BatchJobManager(max_workers=2)
    manager.submit(task)
    assert called.wait(timeout=2.0), "task 가 2초 안에 실행 안 됨"
    manager.shutdown(wait=True)


def test_max_workers_bounds_concurrency() -> None:
    """max_workers=2 → 3개 task 동시 던져도 동시 실행은 2 이하."""
    in_progress = 0
    peak = 0
    lock = threading.Lock()
    started = threading.Event()
    release = threading.Event()

    def task() -> None:
        nonlocal in_progress, peak
        with lock:
            in_progress += 1
            peak = max(peak, in_progress)
        started.set()
        release.wait(timeout=2.0)
        with lock:
            in_progress -= 1

    manager = BatchJobManager(max_workers=2)
    for _ in range(3):
        manager.submit(task)
    started.wait(timeout=1.0)
    time.sleep(0.1)  # 다른 task 들이 acquire 시도할 시간
    assert peak <= 2  # 동시 실행 2 이하
    release.set()
    manager.shutdown(wait=True)


def test_exception_in_worker_does_not_kill_pool(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """task 가 raise 해도 다른 task 는 계속 실행 + ERROR 로그 기록."""
    completed = threading.Event()

    def boom() -> None:
        raise RuntimeError("simulated worker crash")

    def survivor() -> None:
        completed.set()

    manager = BatchJobManager(max_workers=2)
    with caplog.at_level("ERROR", logger="application.batch_job_manager"):
        manager.submit(boom)
        manager.submit(survivor)
        assert completed.wait(timeout=2.0), "survivor 가 실행 안 됨"
    manager.shutdown(wait=True)
    error_logs = [r for r in caplog.records if "batch_job_manager.worker_failed" in r.getMessage()]
    assert len(error_logs) >= 1


def test_shutdown_then_resubmit_creates_new_executor() -> None:
    """shutdown 후 재submit — 새 executor 가 lazily 생성되어 동작."""
    manager = BatchJobManager(max_workers=1)
    first = threading.Event()
    second = threading.Event()
    manager.submit(first.set)
    assert first.wait(timeout=1.0)
    manager.shutdown(wait=True)
    manager.submit(second.set)
    assert second.wait(timeout=1.0)
    manager.shutdown(wait=True)


def test_default_manager_is_singleton() -> None:
    """get_default_manager 가 동일 인스턴스 반환."""
    from application.batch_job_manager import get_default_manager, shutdown_default_manager

    a = get_default_manager()
    b = get_default_manager()
    assert a is b
    shutdown_default_manager()
