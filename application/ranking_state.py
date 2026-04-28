"""publication 상태 재계산 — measurement loop 와 state_calculator 의 결합점.

P1-#3: 외부 검토 지적 — `state_calculator` 의 순수 함수가 측정 루프와 결합되어
있지 않아 dead code 였음. 본 모듈이 그 결합을 제공한다.

3 entry point:
1. `recalculate_visibility_after_measurement(publication_id)`
   — 측정 직후 호출. snapshot 시계열로부터 visibility 재산출 + 변경 시 update.
2. `sweep_workflow_transitions()`
   — 일괄 호출 (스케줄러 daily). held_until 만료 + republishing 타임아웃 4종.
3. `_lookup_active_republish_job(publication_id)` — 내부 헬퍼.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from application import publication_actions_orchestrator as actions_orch
from config.supabase import get_client
from domain.ranking import state_calculator, storage

logger = logging.getLogger(__name__)

_REPUBLISH_JOBS_TABLE = "republish_jobs"
_VISIBILITY_SNAPSHOT_LIMIT = 30  # state_calculator 가 streak 판정에 사용


def recalculate_visibility_after_measurement(publication_id: str) -> str | None:
    """측정 직후 호출 — visibility_status 재산출 + 변경 시 update.

    Returns: 새 visibility_status (변경된 경우) 또는 None (변경 없음/대상 없음).
    """
    pub = storage.get_publication(publication_id)
    if pub is None:
        return None
    snapshots = storage.list_snapshots(publication_id, limit=_VISIBILITY_SNAPSHOT_LIMIT)
    new_visibility = state_calculator.calculate_visibility_status(
        snapshots, previous=pub.visibility_status
    )
    if new_visibility == pub.visibility_status:
        return None
    storage.update_publication_workflow_state(
        publication_id,
        visibility_status=new_visibility,
    )
    logger.info(
        "state.visibility_changed publication_id=%s %s → %s",
        publication_id,
        pub.visibility_status,
        new_visibility,
    )
    return new_visibility


def sweep_workflow_transitions(now: datetime | None = None) -> dict[str, int]:
    """held_until 만료 + republishing 타임아웃 일괄 처리.

    스케줄러 daily 호출 권장. 각 자동 전이는 publication_actions 에 기록되며
    트랜잭션 보장(P0-1)에 따라 INSERT 실패 시 status 도 안 바뀐다.

    Returns: {"hold_expired": N, "republish_timeout": N, "scanned": N}
    """
    now = now or datetime.now(tz=UTC)
    publications = storage.list_publications(
        limit=10_000,
        workflow_status=["held", "republishing"],
    )
    counts = {"hold_expired": 0, "republish_timeout": 0, "scanned": len(publications)}

    for pub in publications:
        if pub.id is None:
            continue
        active_job = _lookup_active_republish_job(pub.id)
        new_status, reason = state_calculator.calculate_workflow_status(pub, active_job, now)
        if new_status == pub.workflow_status:
            continue
        if reason is None:
            continue  # state_calculator 가 사유를 못 주면 자동 전이 안 함
        try:
            actions_orch.auto_requeue(
                pub.id,
                trigger=reason,
                note=f"자동 전이: {pub.workflow_status} → {new_status} ({reason})",
            )
        except Exception:
            logger.exception(
                "sweep.auto_requeue_failed publication_id=%s reason=%s",
                pub.id,
                reason,
            )
            continue
        if reason == "hold_expired":
            counts["hold_expired"] += 1
        else:
            counts["republish_timeout"] += 1
    if counts["hold_expired"] or counts["republish_timeout"]:
        logger.info(
            "sweep.workflow_transitions hold_expired=%d republish_timeout=%d scanned=%d",
            counts["hold_expired"],
            counts["republish_timeout"],
            counts["scanned"],
        )
    return counts


def _lookup_active_republish_job(publication_id: str) -> dict[str, Any] | None:
    """republish_jobs 에서 source_publication_id 매칭하는 active job 1건 (없으면 None).

    'active' = status in (queued/running/completed)
    completed 도 포함하는 이유: completed 후 7일 URL 미등록 시나리오 처리.
    """
    client = get_client()
    result = (
        client.table(_REPUBLISH_JOBS_TABLE)
        .select("status, completed_at, created_at, new_publication_id, pipeline_job_id")
        .eq("source_publication_id", publication_id)
        .in_("status", ["queued", "running", "completed"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast("list[dict[str, Any]]", result.data or [])
    if not rows:
        return None
    job = rows[0]
    # state_calculator 는 datetime 타입 기대 — ISO string → datetime 정규화
    for key in ("created_at", "completed_at"):
        val = job.get(key)
        if isinstance(val, str):
            try:
                job[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                job[key] = None
    # url 미등록 판정용으로 new_publication 의 url 도 join (간략화: 별도 조회)
    new_pub_id = job.get("new_publication_id")
    if new_pub_id:
        new_pub = storage.get_publication(new_pub_id)
        job["new_publication_url"] = new_pub.url if new_pub else None
    return job
