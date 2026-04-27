"""publication 상태 계산 — visibility_status / workflow_status 자동 산출.

매일 09:00 KST 측정 사이클이 본 함수를 호출해 모든 publication 의 status 를
재산출한다. 룰 기반 결정적 함수.

🔴 도메인 격리: storage 직접 호출 안 함. 호출자가 publication + snapshots
+ active republish_job 을 인자로 전달.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from domain.ranking.model import Publication, RankingSnapshot

# 재발행 사이클 타임아웃 (사용자 미응답으로 큐 영구 잠금 방지)
REPUBLISHING_JOB_STUCK_DAYS = 7  # pipeline job queued/running 7일 초과 → action_required
REPUBLISH_URL_PENDING_DAYS = 7  # 생성 완료 후 7일 동안 새 URL 미등록 → action_required

# 미노출 분류 임계
OFF_RADAR_NULL_STREAK = 3  # 최근 3회 연속 null → off_radar
PERSISTENT_OFF_NULL_STREAK = 14  # 14회 이상 → persistent_off (영구 미노출 후보)


def calculate_visibility_status(
    snapshots: list[RankingSnapshot],
    previous: str = "not_measured",
) -> str:
    """측정 결과 기반 visibility_status 산출.

    snapshots 는 captured_at desc.
    not_measured | exposed | off_radar | recovered | persistent_off
    """
    if not snapshots:
        return "not_measured"

    latest = snapshots[0]
    if latest.position is not None:
        # 노출 중. 직전 상태가 off_radar/persistent_off 였다면 recovered (회복)
        if previous in ("off_radar", "persistent_off"):
            return "recovered"
        return "exposed"

    # 최근 측정 미노출 — null streak 길이로 분류
    streak = _count_leading_nulls(snapshots)
    if streak >= PERSISTENT_OFF_NULL_STREAK:
        return "persistent_off"
    if streak >= OFF_RADAR_NULL_STREAK:
        return "off_radar"
    # 1~2회 null 은 일시적 — 직전 상태 유지 (exposed 면 그대로)
    return previous if previous in ("exposed", "recovered") else "off_radar"


def calculate_workflow_status(
    publication: Publication,
    active_republish_job: dict[str, Any] | None,
    now: datetime,
) -> tuple[str, str | None]:
    """운영 액션 기반 workflow_status 산출.

    Returns: (new_status, transition_reason).
    transition_reason 은 자동 전이 시 publication_actions.metadata.trigger 에 기록.

    부모 publication 의 republishing 타임아웃 두 케이스 분리:
    - republish_job_stuck: pipeline job 이 queued/running 인데 N일 초과
    - republish_url_pending: pipeline job 은 completed 인데 새 URL 미등록 N일
    """
    current = publication.workflow_status

    # held_until 만료 자동 해제
    if (
        current == "held"
        and publication.held_until is not None
        and publication.held_until <= now
    ):
        return "action_required", "hold_expired"

    # republishing 타임아웃 룰
    if current == "republishing":
        return _calculate_republishing_state(publication, active_republish_job, now)

    return current, None


def _calculate_republishing_state(
    publication: Publication,
    active_job: dict[str, Any] | None,
    now: datetime,
) -> tuple[str, str | None]:
    """republishing 상태에서 비정상 시나리오 자동 큐 복귀."""
    if active_job is None:
        # 부모는 republishing 인데 active job 없음 — 데이터 이상
        return "action_required", "republish_job_missing"

    started = publication.republishing_started_at or active_job.get("created_at")
    if not isinstance(started, datetime):
        return "republishing", None

    age = now - started
    job_status = active_job.get("status")

    if job_status in ("queued", "running") and age > timedelta(days=REPUBLISHING_JOB_STUCK_DAYS):
        return "action_required", "republish_job_stuck"

    if job_status == "completed":
        completed_at = active_job.get("completed_at") or started
        if isinstance(completed_at, datetime):
            completed_age = now - completed_at
            new_pub_id = active_job.get("new_publication_id")
            new_pub_url = active_job.get("new_publication_url")  # 호출자가 join 해서 전달
            url_missing = not new_pub_id or not new_pub_url
            if url_missing and completed_age > timedelta(days=REPUBLISH_URL_PENDING_DAYS):
                return "action_required", "republish_url_pending"

    if job_status == "failed":
        return "action_required", "republish_job_failed"

    return "republishing", None


def _count_leading_nulls(snapshots: list[RankingSnapshot]) -> int:
    """captured_at desc 정렬된 snapshots 의 선행 null 길이."""
    n = 0
    for s in snapshots:
        if s.position is not None:
            return n
        n += 1
    return n
