"""P0-2: republish_jobs 라이프사이클 finalizer 시나리오 테스트.

job_manager 종료 훅에서 호출되는 `on_pipeline_job_finished` 와 서버 재시작 시
호출되는 `recover_stuck_republish_jobs` 를 검증한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from application import republish_orchestrator as ro


def _job(
    job_id: str = "job-1",
    *,
    type: str = "pipeline",
    status: str = "succeeded",
) -> SimpleNamespace:
    """job_manager.Job 의 필요한 속성만 흉내 — 도메인 격리."""
    return SimpleNamespace(id=job_id, type=type, status=status)


class TestOnPipelineJobFinished:
    def test_succeeded_pipeline_marks_republish_completed(self) -> None:
        with (
            patch.object(ro, "update_republish_job_status", return_value=1) as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            ro.on_pipeline_job_finished(_job(status="succeeded"))
        upd.assert_called_once_with("job-1", "completed")
        requeue.assert_not_called()

    @pytest.mark.parametrize("job_status", ["failed", "cancelled", "timed_out"])
    def test_failure_marks_republish_failed_and_requeues(self, job_status: str) -> None:
        with (
            patch.object(ro, "update_republish_job_status", return_value=1) as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            ro.on_pipeline_job_finished(_job(status=job_status))
        upd.assert_called_once_with("job-1", "failed")
        requeue.assert_called_once_with("job-1")

    def test_non_pipeline_job_ignored(self) -> None:
        with (
            patch.object(ro, "update_republish_job_status") as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            ro.on_pipeline_job_finished(_job(type="analyze", status="succeeded"))
        upd.assert_not_called()
        requeue.assert_not_called()

    def test_pipeline_job_unrelated_to_republish_no_requeue(self) -> None:
        """update 가 0행 영향 → 일반 파이프라인 job, requeue 호출 안 함."""
        with (
            patch.object(ro, "update_republish_job_status", return_value=0) as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            ro.on_pipeline_job_finished(_job(status="failed"))
        upd.assert_called_once_with("job-1", "failed")
        requeue.assert_not_called()

    def test_running_job_no_finalize(self) -> None:
        """종료가 아닌 상태(running/pending)는 finalize 호출 안 함."""
        with (
            patch.object(ro, "update_republish_job_status") as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            ro.on_pipeline_job_finished(_job(status="running"))
        upd.assert_not_called()
        requeue.assert_not_called()


class TestRecoverStuckRepublishJobs:
    def test_marks_queued_running_as_failed_and_requeues_parent(self) -> None:
        # 재시작 후 queued/running 으로 남은 republish_jobs 2건
        rows = [
            {"pipeline_job_id": "j-1", "source_publication_id": "p-1"},
            {"pipeline_job_id": "j-2", "source_publication_id": "p-2"},
        ]
        client = MagicMock()
        client.table.return_value.select.return_value.in_.return_value.execute.return_value = SimpleNamespace(
            data=rows
        )
        with (
            patch.object(ro, "get_client", return_value=client),
            patch.object(ro, "update_republish_job_status", return_value=1) as upd,
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            recovered = ro.recover_stuck_republish_jobs()
        assert recovered == 2
        assert upd.call_count == 2
        assert requeue.call_count == 2

    def test_zero_stuck_returns_zero(self) -> None:
        client = MagicMock()
        client.table.return_value.select.return_value.in_.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )
        with (
            patch.object(ro, "get_client", return_value=client),
            patch.object(ro, "update_republish_job_status") as upd,
        ):
            recovered = ro.recover_stuck_republish_jobs()
        assert recovered == 0
        upd.assert_not_called()

    def test_partial_failure_continues(self) -> None:
        """1건 실패해도 나머지는 회수 시도."""
        rows = [
            {"pipeline_job_id": "j-1", "source_publication_id": "p-1"},
            {"pipeline_job_id": "j-2", "source_publication_id": "p-2"},
        ]
        client = MagicMock()
        client.table.return_value.select.return_value.in_.return_value.execute.return_value = SimpleNamespace(
            data=rows
        )
        with (
            patch.object(ro, "get_client", return_value=client),
            patch.object(
                ro,
                "update_republish_job_status",
                side_effect=[RuntimeError("DB hiccup"), 1],
            ),
            patch.object(ro, "_auto_requeue_failed_republish") as requeue,
        ):
            recovered = ro.recover_stuck_republish_jobs()
        # 1건 성공, 1건 실패. 성공한 것만 requeue.
        assert recovered == 1
        assert requeue.call_count == 1


class TestUpdateRepublishJobStatus:
    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValueError, match="status"):
            ro.update_republish_job_status("j-1", "invalid")

    def test_completed_at_auto_filled_on_terminal_status(self) -> None:
        client = MagicMock()
        captured: dict[str, dict[str, object]] = {}

        def capture_update(payload: dict[str, object]) -> MagicMock:
            captured["payload"] = payload
            chain = MagicMock()
            chain.eq.return_value.execute.return_value = SimpleNamespace(data=[{}])
            return chain

        client.table.return_value.update.side_effect = capture_update
        with patch.object(ro, "get_client", return_value=client):
            ro.update_republish_job_status("j-1", "completed")
        assert "completed_at" in captured["payload"]

    def test_explicit_completed_at_used(self) -> None:
        ts = datetime(2026, 4, 28, 9, 0, tzinfo=UTC)
        client = MagicMock()
        captured: dict[str, dict[str, object]] = {}

        def capture_update(payload: dict[str, object]) -> MagicMock:
            captured["payload"] = payload
            chain = MagicMock()
            chain.eq.return_value.execute.return_value = SimpleNamespace(data=[{}])
            return chain

        client.table.return_value.update.side_effect = capture_update
        with patch.object(ro, "get_client", return_value=client):
            ro.update_republish_job_status("j-1", "completed", completed_at=ts)
        assert captured["payload"]["completed_at"] == ts.isoformat()
