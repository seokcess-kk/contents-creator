"""P1-#3: 측정 루프 ↔ 상태 재계산 통합 테스트.

state_calculator 가 측정 사이클 + workflow sweep 에 실제로 연결되는지 검증.
4개 핵심 시나리오:
1. 측정 → off_radar 자동 분류
2. 회복 판정 (off_radar → recovered when found)
3. 보류 만료 (held_until 지난 publication 자동 큐 복귀)
4. 재발행 타임아웃 (republishing job stuck 7일 초과 → action_required)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from application import ranking_state
from domain.ranking.model import Publication, RankingSnapshot


def _pub(**kwargs: object) -> Publication:
    defaults: dict[str, object] = {
        "id": "p-1",
        "keyword": "다이어트한의원",
        "url": "https://m.blog.naver.com/u/123",
        "visibility_status": "not_measured",
        "workflow_status": "active",
    }
    defaults.update(kwargs)
    return Publication(**defaults)  # type: ignore[arg-type]


def _snap(position: int | None, captured_at: datetime) -> RankingSnapshot:
    return RankingSnapshot(
        publication_id="p-1",
        section="VIEW" if position else None,
        position=position,
        captured_at=captured_at,
    )


class TestRecalculateVisibility:
    """측정 직후 visibility 재산출."""

    def test_first_exposure_sets_exposed(self) -> None:
        """이전 not_measured + 측정 결과 found → exposed."""
        pub = _pub(visibility_status="not_measured")
        snaps = [_snap(5, datetime.now(tz=UTC))]
        with (
            patch.object(ranking_state.storage, "get_publication", return_value=pub),
            patch.object(ranking_state.storage, "list_snapshots", return_value=snaps),
            patch.object(ranking_state.storage, "update_publication_workflow_state") as upd,
        ):
            result = ranking_state.recalculate_visibility_after_measurement("p-1")
        assert result == "exposed"
        upd.assert_called_once_with("p-1", visibility_status="exposed")

    def test_recovery_after_off_radar(self) -> None:
        """이전 off_radar + 측정 결과 found → recovered."""
        pub = _pub(visibility_status="off_radar")
        snaps = [_snap(8, datetime.now(tz=UTC))]
        with (
            patch.object(ranking_state.storage, "get_publication", return_value=pub),
            patch.object(ranking_state.storage, "list_snapshots", return_value=snaps),
            patch.object(ranking_state.storage, "update_publication_workflow_state") as upd,
        ):
            result = ranking_state.recalculate_visibility_after_measurement("p-1")
        assert result == "recovered"
        upd.assert_called_once_with("p-1", visibility_status="recovered")

    def test_off_radar_after_3_consecutive_nulls(self) -> None:
        """이전 exposed + 최근 3회 연속 미노출 → off_radar."""
        pub = _pub(visibility_status="exposed")
        now = datetime.now(tz=UTC)
        snaps = [
            _snap(None, now),
            _snap(None, now - timedelta(days=1)),
            _snap(None, now - timedelta(days=2)),
        ]
        with (
            patch.object(ranking_state.storage, "get_publication", return_value=pub),
            patch.object(ranking_state.storage, "list_snapshots", return_value=snaps),
            patch.object(ranking_state.storage, "update_publication_workflow_state") as upd,
        ):
            result = ranking_state.recalculate_visibility_after_measurement("p-1")
        assert result == "off_radar"
        upd.assert_called_once_with("p-1", visibility_status="off_radar")

    def test_no_change_skips_update(self) -> None:
        """이미 exposed + 또 노출 → update 호출 안 함."""
        pub = _pub(visibility_status="exposed")
        snaps = [_snap(3, datetime.now(tz=UTC))]
        with (
            patch.object(ranking_state.storage, "get_publication", return_value=pub),
            patch.object(ranking_state.storage, "list_snapshots", return_value=snaps),
            patch.object(ranking_state.storage, "update_publication_workflow_state") as upd,
        ):
            result = ranking_state.recalculate_visibility_after_measurement("p-1")
        assert result is None
        upd.assert_not_called()

    def test_publication_not_found_returns_none(self) -> None:
        with patch.object(ranking_state.storage, "get_publication", return_value=None):
            result = ranking_state.recalculate_visibility_after_measurement("p-x")
        assert result is None


class TestSweepWorkflowTransitions:
    """workflow sweep — held 만료 + republishing 타임아웃."""

    def test_hold_expired_triggers_auto_requeue(self) -> None:
        """held_until 이 과거 → action_required 자동 전이."""
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        expired_pub = _pub(
            id="p-held",
            workflow_status="held",
            held_until=now - timedelta(days=1),
        )
        with (
            patch.object(ranking_state.storage, "list_publications", return_value=[expired_pub]),
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=None),
            patch.object(ranking_state.actions_orch, "auto_requeue") as requeue,
        ):
            counts = ranking_state.sweep_workflow_transitions(now=now)
        assert counts["hold_expired"] == 1
        assert counts["scanned"] == 1
        requeue.assert_called_once()
        kwargs = requeue.call_args.kwargs
        assert kwargs["trigger"] == "hold_expired"

    def test_hold_not_yet_expired_no_transition(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        future_pub = _pub(
            id="p-held",
            workflow_status="held",
            held_until=now + timedelta(days=5),
        )
        with (
            patch.object(ranking_state.storage, "list_publications", return_value=[future_pub]),
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=None),
            patch.object(ranking_state.actions_orch, "auto_requeue") as requeue,
        ):
            counts = ranking_state.sweep_workflow_transitions(now=now)
        assert counts["hold_expired"] == 0
        requeue.assert_not_called()

    def test_republish_job_stuck_7_days(self) -> None:
        """republishing publication + queued job 7일 초과 → action_required."""
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        stuck_pub = _pub(
            id="p-rep",
            workflow_status="republishing",
            republishing_started_at=now - timedelta(days=8),
        )
        active_job = {
            "status": "queued",
            "created_at": now - timedelta(days=8),
            "completed_at": None,
            "new_publication_id": None,
        }
        with (
            patch.object(ranking_state.storage, "list_publications", return_value=[stuck_pub]),
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=active_job),
            patch.object(ranking_state.actions_orch, "auto_requeue") as requeue,
        ):
            counts = ranking_state.sweep_workflow_transitions(now=now)
        assert counts["republish_timeout"] == 1
        kwargs = requeue.call_args.kwargs
        assert kwargs["trigger"] == "republish_job_stuck"

    def test_republish_job_failed_triggers_requeue(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        failed_pub = _pub(
            id="p-rep",
            workflow_status="republishing",
            republishing_started_at=now - timedelta(hours=2),
        )
        active_job = {
            "status": "failed",
            "created_at": now - timedelta(hours=2),
            "completed_at": now - timedelta(hours=1),
            "new_publication_id": None,
        }
        with (
            patch.object(ranking_state.storage, "list_publications", return_value=[failed_pub]),
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=active_job),
            patch.object(ranking_state.actions_orch, "auto_requeue") as requeue,
        ):
            counts = ranking_state.sweep_workflow_transitions(now=now)
        assert counts["republish_timeout"] == 1
        kwargs = requeue.call_args.kwargs
        assert kwargs["trigger"] == "republish_job_failed"

    def test_republish_url_pending_after_completion(self) -> None:
        """job completed 후 7일 + new_publication URL 미등록 → action_required."""
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        pending_pub = _pub(
            id="p-rep",
            workflow_status="republishing",
            republishing_started_at=now - timedelta(days=10),
        )
        active_job = {
            "status": "completed",
            "created_at": now - timedelta(days=10),
            "completed_at": now - timedelta(days=8),
            "new_publication_id": "new-1",
            "new_publication_url": None,  # URL 미등록
        }
        with (
            patch.object(ranking_state.storage, "list_publications", return_value=[pending_pub]),
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=active_job),
            patch.object(ranking_state.actions_orch, "auto_requeue") as requeue,
        ):
            counts = ranking_state.sweep_workflow_transitions(now=now)
        assert counts["republish_timeout"] == 1
        kwargs = requeue.call_args.kwargs
        assert kwargs["trigger"] == "republish_url_pending"

    def test_active_publication_not_in_sweep(self) -> None:
        """active 상태는 sweep 대상 아님 (held + republishing 만 list)."""
        now = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        with (
            patch.object(ranking_state.storage, "list_publications") as list_pubs,
            patch.object(ranking_state, "_lookup_active_republish_job", return_value=None),
        ):
            list_pubs.return_value = []
            ranking_state.sweep_workflow_transitions(now=now)
        # list_publications 호출 시 workflow_status=["held","republishing"] 필터 사용
        list_pubs.assert_called_once_with(limit=10_000, workflow_status=["held", "republishing"])


class TestLookupActiveRepublishJob:
    """republish_jobs 조회 헬퍼 — datetime 정규화 + new_publication_url join."""

    def test_iso_string_dates_normalized_to_datetime(self) -> None:
        client = MagicMock()
        rows = [
            {
                "status": "queued",
                "created_at": "2026-04-20T10:00:00+00:00",
                "completed_at": None,
                "new_publication_id": None,
                "pipeline_job_id": "j-1",
            }
        ]
        client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=rows
        )
        with patch.object(ranking_state, "get_client", return_value=client):
            job = ranking_state._lookup_active_republish_job("p-1")
        assert job is not None
        assert isinstance(job["created_at"], datetime)
        assert job["completed_at"] is None

    def test_no_active_job_returns_none(self) -> None:
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )
        with patch.object(ranking_state, "get_client", return_value=client):
            job = ranking_state._lookup_active_republish_job("p-1")
        assert job is None
