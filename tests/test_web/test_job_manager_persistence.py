"""Phase J2 PR2 — JobManager write-through 회귀.

검증 대상:
1. flag off (default) → DB 호출 0 (in-memory only). 기존 동작 100% 보존
2. flag on + submit → insert_job 호출
3. flag on + 4지점 (running/succeeded/failed/timed_out/cancelled) → update_job_status 호출
4. Supabase 장애 mock → graceful degrade (logger.warning + 본 흐름 동작)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application.models import AnalyzeResult, PipelineResult, StageStatus, ValidateResult
from web.api.job_manager import JobManager


def _ok_analyze() -> AnalyzeResult:
    return AnalyzeResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="t",
        analyzed_count=1,
        pattern_card_path=Path("/tmp/p.json"),
    )


def _ok_pipeline() -> PipelineResult:
    return PipelineResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="t",
    )


def _ok_validate() -> ValidateResult:
    return ValidateResult(
        status=StageStatus.SUCCEEDED,
        content_path=Path("/tmp/dummy.md"),
        passed=True,
    )


@pytest.fixture
def manager() -> JobManager:
    """매 테스트 새 manager — _executor / _jobs 격리."""
    return JobManager()


def _wait_until_terminal(mgr: JobManager, job_id: str, timeout_s: float = 5.0) -> str:
    """job 이 succeeded/failed/cancelled/timed_out 까지 대기 후 status 반환."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = mgr.get_job(job_id)
        if job is None:
            time.sleep(0.05)
            continue
        if job.status in ("succeeded", "failed", "cancelled", "timed_out"):
            return job.status
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach terminal state within {timeout_s}s")


# ── flag off (default) — DB 호출 0 ─────────────────────────────────────


class TestFlagOff:
    def test_submit_does_not_call_insert_job(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        insert_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.insert_job", insert_mock)

        with patch("web.api.job_manager.run_validate_only", return_value=_ok_validate()):
            job = manager.submit_validate({"content_path": "/tmp/dummy.md"})
            _wait_until_terminal(manager, job.id)

        assert insert_mock.call_count == 0

    def test_run_does_not_call_update_status(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        assert update_mock.call_count == 0


# ── flag on — submit insert + 4지점 status update ──────────────────────


class TestFlagOnSubmit:
    def test_calls_insert_job(self, manager: JobManager, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        insert_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.insert_job", insert_mock)
        # update 는 부수 효과만, 본 테스트의 검증 대상 아님
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_job_status", MagicMock(return_value=True)
        )

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        assert insert_mock.call_count == 1
        kwargs = insert_mock.call_args.kwargs
        assert insert_mock.call_args.args[0] == job.id
        assert kwargs["job_type"] == "analyze"
        assert kwargs["keyword"] == "kw"
        assert kwargs["params"] == {"keyword": "kw"}
        assert kwargs["instance_id"]  # RENDER_INSTANCE_ID 또는 hostname

    def test_insert_failure_does_not_block_submission(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        # insert_job 가 raise 해도 submit 자체는 정상 완료 (graceful degrade)
        insert_mock = MagicMock(side_effect=RuntimeError("supabase down"))
        monkeypatch.setattr("web.api.job_manager.job_store.insert_job", insert_mock)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_job_status", MagicMock(return_value=True)
        )

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            terminal = _wait_until_terminal(manager, job.id)

        # in-memory 는 정상 — 사용자 흐름 무영향
        assert manager.get_job(job.id) is not None
        assert terminal == "succeeded"


class TestFlagOnRunSucceeded:
    def test_calls_running_then_succeeded(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        # PR3 — emit 가 progress_events 호출 시도하므로 mock 필요 (실제 DB 회피)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event", MagicMock(return_value=True)
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        statuses = [c.args[1] for c in update_mock.call_args_list]
        assert "running" in statuses
        assert "succeeded" in statuses
        assert statuses.index("running") < statuses.index("succeeded")


class TestFlagOnRunFailed:
    def test_calls_running_then_failed(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event", MagicMock(return_value=True)
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        with patch(
            "web.api.job_manager.run_analyze_only",
            side_effect=RuntimeError("brightdata 4xx"),
        ):
            job = manager.submit_analyze({"keyword": "kw"})
            terminal = _wait_until_terminal(manager, job.id)

        assert terminal == "failed"
        statuses = [c.args[1] for c in update_mock.call_args_list]
        assert "running" in statuses
        assert "failed" in statuses
        # failed 호출에 error 메시지 동반
        failed_call = next(c for c in update_mock.call_args_list if c.args[1] == "failed")
        assert "brightdata" in failed_call.kwargs.get("error", "")


class TestFlagOnCancel:
    def test_cancel_pending_job_calls_cancelled(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_job_status", update_mock)

        # dispatch 가 시작되기 전에 cancel 시도하기 위해 run 함수가 sleep
        def slow_run(*_a: Any, **_kw: Any) -> AnalyzeResult:
            time.sleep(0.5)
            return _ok_analyze()

        with patch("web.api.job_manager.run_analyze_only", side_effect=slow_run):
            job = manager.submit_analyze({"keyword": "kw"})
            cancelled = manager.cancel_job(job.id)
            assert cancelled is True

        statuses = [c.args[1] for c in update_mock.call_args_list]
        assert "cancelled" in statuses


class TestFlagOnPersistFailureGraceful:
    def test_update_failure_does_not_break_run(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        # update_job_status 가 매번 raise — graceful degrade 검증
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_job_status",
            MagicMock(side_effect=RuntimeError("supabase 503")),
        )

        with patch("web.api.job_manager.run_pipeline", return_value=_ok_pipeline()):
            job = manager.submit_pipeline({"keyword": "kw"})
            terminal = _wait_until_terminal(manager, job.id)

        # DB 업데이트가 매번 실패해도 in-memory 는 정상 종결
        assert terminal == "succeeded"


# ── Phase J2 PR3 — heartbeat thread ────────────────────────────────────


class TestHeartbeatThread:
    def test_flag_off_thread_not_started(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_heartbeat", update_mock)

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        # flag off → thread 미시작 → update_heartbeat 호출 0
        assert manager._heartbeat_thread is None
        assert update_mock.call_count == 0

    def test_flag_on_thread_lazily_started(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        # 짧은 interval — heartbeat tick 가 빠르게 발생
        monkeypatch.setattr("config.settings.settings.job_heartbeat_seconds", 5)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_job_status", MagicMock(return_value=True)
        )
        update_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.update_heartbeat", update_mock)

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        # flag on → thread 1회 시작
        assert manager._heartbeat_thread is not None
        assert manager._heartbeat_thread.is_alive()
        # job 이 빠르게 종결돼서 heartbeat tick 안 발생할 수 있음 — 호출 횟수
        # 자체는 검증 안 하고, thread 가 살아있다는 사실만 확인 (tick interval=5
        # 인데 job 종결이 그보다 빠르면 0회. 운영에서는 long-running job 만
        # tick 받음)

    def test_shutdown_stops_thread(
        self, manager: JobManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr("config.settings.settings.job_heartbeat_seconds", 5)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.insert_job", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_job_status", MagicMock(return_value=True)
        )
        monkeypatch.setattr(
            "web.api.job_manager.job_store.update_heartbeat", MagicMock(return_value=True)
        )

        with patch("web.api.job_manager.run_analyze_only", return_value=_ok_analyze()):
            job = manager.submit_analyze({"keyword": "kw"})
            _wait_until_terminal(manager, job.id)

        thread = manager._heartbeat_thread
        assert thread is not None and thread.is_alive()
        manager.shutdown()
        # stop event + join 으로 1초 안에 종료
        thread.join(timeout=2.0)
        assert not thread.is_alive()
