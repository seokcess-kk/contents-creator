"""state_calculator 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domain.ranking.model import Publication, RankingSnapshot
from domain.ranking.state_calculator import (
    OFF_RADAR_NULL_STREAK,
    PERSISTENT_OFF_NULL_STREAK,
    REPUBLISH_URL_PENDING_DAYS,
    REPUBLISHING_JOB_STUCK_DAYS,
    calculate_visibility_status,
    calculate_workflow_status,
)

_NOW = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)


def _snap(position: int | None, days_ago: int) -> RankingSnapshot:
    return RankingSnapshot(
        publication_id="pub-1",
        position=position,
        captured_at=_NOW - timedelta(days=days_ago),
    )


def _pub(**overrides: object) -> Publication:
    base: dict[str, object] = {
        "id": "pub-1",
        "keyword": "kw",
        "url": "https://m.blog.naver.com/u/123456789",
        "workflow_status": "active",
        "visibility_status": "not_measured",
    }
    base.update(overrides)
    return Publication(**base)  # type: ignore[arg-type]


# ── visibility_status ──


class TestVisibilityStatus:
    def test_no_snapshots_is_not_measured(self) -> None:
        assert calculate_visibility_status([]) == "not_measured"

    def test_latest_exposed_returns_exposed(self) -> None:
        assert calculate_visibility_status([_snap(5, 0)]) == "exposed"

    def test_recovered_when_previous_off_radar(self) -> None:
        assert calculate_visibility_status([_snap(5, 0)], previous="off_radar") == "recovered"

    def test_off_radar_at_streak_threshold(self) -> None:
        snaps = [_snap(None, i) for i in range(OFF_RADAR_NULL_STREAK)]
        assert calculate_visibility_status(snaps) == "off_radar"

    def test_persistent_off_at_long_streak(self) -> None:
        snaps = [_snap(None, i) for i in range(PERSISTENT_OFF_NULL_STREAK)]
        assert calculate_visibility_status(snaps) == "persistent_off"

    def test_one_null_after_exposure_keeps_previous(self) -> None:
        # null 1회만 — 일시적, exposed 유지
        snaps = [_snap(None, 0), _snap(5, 1)]
        assert calculate_visibility_status(snaps, previous="exposed") == "exposed"


# ── workflow_status ──


class TestWorkflowStatus:
    def test_active_unchanged(self) -> None:
        status, reason = calculate_workflow_status(_pub(), None, _NOW)
        assert status == "active"
        assert reason is None

    def test_held_until_expired_releases(self) -> None:
        pub = _pub(
            workflow_status="held",
            held_until=_NOW - timedelta(days=1),
        )
        status, reason = calculate_workflow_status(pub, None, _NOW)
        assert status == "action_required"
        assert reason == "hold_expired"

    def test_held_until_future_stays_held(self) -> None:
        pub = _pub(workflow_status="held", held_until=_NOW + timedelta(days=3))
        status, _ = calculate_workflow_status(pub, None, _NOW)
        assert status == "held"

    def test_republishing_with_no_active_job(self) -> None:
        pub = _pub(workflow_status="republishing")
        status, reason = calculate_workflow_status(pub, None, _NOW)
        assert status == "action_required"
        assert reason == "republish_job_missing"

    def test_republishing_job_stuck(self) -> None:
        started = _NOW - timedelta(days=REPUBLISHING_JOB_STUCK_DAYS + 1)
        pub = _pub(workflow_status="republishing", republishing_started_at=started)
        job = {"status": "running", "created_at": started}
        status, reason = calculate_workflow_status(pub, job, _NOW)
        assert status == "action_required"
        assert reason == "republish_job_stuck"

    def test_republishing_url_pending(self) -> None:
        completed = _NOW - timedelta(days=REPUBLISH_URL_PENDING_DAYS + 1)
        started = completed - timedelta(days=1)
        pub = _pub(workflow_status="republishing", republishing_started_at=started)
        job = {
            "status": "completed",
            "created_at": started,
            "completed_at": completed,
            "new_publication_id": "new-pub-1",
            "new_publication_url": None,  # URL 미등록
        }
        status, reason = calculate_workflow_status(pub, job, _NOW)
        assert status == "action_required"
        assert reason == "republish_url_pending"

    def test_republishing_completed_with_url_stays(self) -> None:
        # URL 등록 완료 — 정상 케이스 (큐 복귀 X, 호출자가 active 로 전이 결정)
        completed = _NOW - timedelta(days=REPUBLISH_URL_PENDING_DAYS + 1)
        started = completed - timedelta(days=1)
        pub = _pub(workflow_status="republishing", republishing_started_at=started)
        job = {
            "status": "completed",
            "created_at": started,
            "completed_at": completed,
            "new_publication_id": "new-pub-1",
            "new_publication_url": "https://m.blog.naver.com/u/9999",
        }
        status, _ = calculate_workflow_status(pub, job, _NOW)
        assert status == "republishing"  # 자동 전이 X — 호출자가 결정

    def test_republishing_failed(self) -> None:
        pub = _pub(workflow_status="republishing", republishing_started_at=_NOW)
        job = {"status": "failed", "created_at": _NOW}
        status, reason = calculate_workflow_status(pub, job, _NOW)
        assert status == "action_required"
        assert reason == "republish_job_failed"
