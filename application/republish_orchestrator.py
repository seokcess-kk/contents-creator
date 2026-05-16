"""재발행 use case — 파이프라인 트리거 + DB 잠금. 부모 상태는 active 유지.

흐름:
1. 부모 publication 의 active republish job 존재 시 RuntimeError (DB unique 제약)
2. draft publication 자동 생성 (url=None, parent 연결, workflow=draft)
3. job_manager 에 pipeline job 제출 (12-hex job_id)
4. republish_jobs row INSERT — 위 두 단계 연결
5. publication_actions.republished 히스토리 기록 (실패 시 raise)

부모는 별도 URL 로 계속 추적되어야 하므로 workflow_status 를 변경하지 않는다.
재발행 진행 컨텍스트는 republish_jobs 테이블 + 자식 draft + parent_publication_id
조합으로 표현된다.

🔴 데이터 정합성:
- 같은 source_publication_id 에 active(queued/running) job 1개만 — DB partial unique
- republish_jobs INSERT 실패 → draft publication cleanup (구현됨)
- 진정한 atomicity 는 Supabase RPC 로만 가능 — P1 에서 RPC 도입 검토
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from config.supabase import get_client
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication
from domain.ranking.publication_actions import PublicationAction

logger = logging.getLogger(__name__)

_REPUBLISH_JOBS_TABLE = "republish_jobs"


def start_republish(
    source_publication_id: str,
    *,
    strategy: str = "full_rewrite",
    diagnosis_id: str | None = None,
) -> dict[str, Any]:
    """재발행 트리거. 정상 종료 시 dict 반환 (job_id, new_publication_id, ...).

    Raises:
        ValueError: source publication 미존재 또는 keyword 비어있음.
        RuntimeError: 동일 source 에 active(queued/running) job 충돌.
    """
    if strategy not in ("full_rewrite", "light", "cluster"):
        raise ValueError(f"strategy 는 full_rewrite/light/cluster 중 하나: {strategy!r}")

    parent = ranking_storage.get_publication(source_publication_id)
    if parent is None:
        raise ValueError(f"publication 미존재: {source_publication_id}")
    if not parent.keyword:
        raise ValueError(f"publication 의 keyword 가 비어있음: {source_publication_id}")

    # 1) draft publication 생성 (url=None, parent 연결)
    new_pub = ranking_storage.insert_publication(
        Publication(
            keyword=parent.keyword,
            url=None,
            slug=parent.slug,  # 동일 slug 그대로 (재발행 트래킹용)
            parent_publication_id=parent.id,
            workflow_status="draft",
            visibility_status="not_measured",
        )
    )
    if new_pub.id is None:
        raise RuntimeError("draft publication insert 실패")

    # 2) pipeline job 제출
    pipeline_job_id = _submit_pipeline_job(parent.keyword, strategy)

    # 3) republish_jobs INSERT — DB partial unique 가 동시 실행 차단
    try:
        _insert_republish_job(
            source_publication_id=source_publication_id,
            source_diagnosis_id=diagnosis_id,
            pipeline_job_id=pipeline_job_id,
            strategy=strategy,
            new_publication_id=new_pub.id,
        )
    except Exception as exc:
        # active job 충돌 — 위에서 만든 draft publication 정리
        if _is_unique_violation(exc):
            ranking_storage.delete_publication(new_pub.id)
            raise RuntimeError(
                f"이미 진행 중인 재발행 작업이 있습니다: {source_publication_id}"
            ) from exc
        raise

    # 5) publication_actions 히스토리 — 실패 시 raise
    _record_republished_action(
        source_publication_id=source_publication_id,
        diagnosis_id=diagnosis_id,
        new_publication_id=new_pub.id,
        pipeline_job_id=pipeline_job_id,
        strategy=strategy,
    )

    # 6) draft publication 의 job_id 백필 (best-effort) — unified queue 의
    # job_id 1순위 매칭 정확성 확보. 실패해도 본 흐름 영향 X.
    # 2026-05-15 부평 사고: 자식 draft 의 slug 가 부모와 동일하거나 null 일 때
    # frontend slug fallback 매칭이 자식·부모를 구분하지 못해 hide 되는 사고
    # 후속. job_id 가 채워지면 1순위 매칭으로 정확히 자식과 연결된다.
    try:
        ranking_storage.update_publication(new_pub.id, job_id=pipeline_job_id)
    except Exception as exc:  # noqa: BLE001 — best-effort, raise 시 본 흐름 영향
        logger.warning(
            "republish.draft_job_id_backfill_failed new_pub=%s job=%s err=%s",
            new_pub.id,
            pipeline_job_id,
            exc,
        )

    started_at = datetime.now(tz=UTC)
    logger.info(
        "republish.started source=%s new=%s job=%s strategy=%s",
        source_publication_id,
        new_pub.id,
        pipeline_job_id,
        strategy,
    )
    return {
        "source_publication_id": source_publication_id,
        "new_publication_id": new_pub.id,
        "pipeline_job_id": pipeline_job_id,
        "strategy": strategy,
        "started_at": started_at.isoformat(),
    }


# ── 내부 헬퍼 ──


def _submit_pipeline_job(keyword: str, strategy: str) -> str:
    """job_manager 에 pipeline job 제출 → 12-hex job_id 반환.

    strategy 별 파이프라인 옵션 차등은 차후 확장. v1 은 모두 기본 full pipeline.
    """
    from web.api.main import job_manager  # 런타임 lazy import (테스트 격리)

    params = {"keyword": keyword, "strategy": strategy}
    job = job_manager.submit_pipeline(params)
    return job.id


def _insert_republish_job(
    *,
    source_publication_id: str,
    source_diagnosis_id: str | None,
    pipeline_job_id: str,
    strategy: str,
    new_publication_id: str,
) -> None:
    """republish_jobs INSERT. 동시 active job 있으면 unique 위반 에러."""
    client = get_client()
    payload: dict[str, Any] = {
        "source_publication_id": source_publication_id,
        "pipeline_job_id": pipeline_job_id,
        "strategy": strategy,
        "new_publication_id": new_publication_id,
        "status": "queued",
    }
    if source_diagnosis_id is not None:
        payload["source_diagnosis_id"] = source_diagnosis_id
    client.table(_REPUBLISH_JOBS_TABLE).insert(payload).execute()


def _is_unique_violation(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "duplicate key" in text or "23505" in text or "unique" in text


def _record_republished_action(
    *,
    source_publication_id: str,
    diagnosis_id: str | None,
    new_publication_id: str,
    pipeline_job_id: str,
    strategy: str,
) -> None:
    """publication_actions 히스토리 — 실패 시 raise (single source of truth)."""
    from domain.ranking import publication_actions as actions_storage

    actions_storage.insert_action(
        PublicationAction(
            publication_id=source_publication_id,
            diagnosis_id=diagnosis_id,
            action="republished",
            note=f"재발행 시작 ({strategy})",
            metadata={
                "new_publication_id": new_publication_id,
                "pipeline_job_id": pipeline_job_id,
                "strategy": strategy,
            },
        )
    )


def update_republish_job_status(
    pipeline_job_id: str,
    status: str,
    *,
    completed_at: datetime | None = None,
) -> int:
    """파이프라인 job 상태 변화를 republish_jobs 에 동기화.

    job_manager 의 finished 콜백(`on_pipeline_job_finished`)에서 호출.
    영향 행 수 반환 (해당 pipeline_job_id 가 republish 가 아니면 0).
    """
    if status not in ("queued", "running", "completed", "failed"):
        raise ValueError(f"status 는 queued/running/completed/failed: {status!r}")
    client = get_client()
    payload: dict[str, Any] = {"status": status}
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    elif status in ("completed", "failed"):
        payload["completed_at"] = datetime.now(tz=UTC).isoformat()
    result = (
        client.table(_REPUBLISH_JOBS_TABLE)
        .update(payload)
        .eq("pipeline_job_id", pipeline_job_id)
        .execute()
    )
    return len(cast("list[Any]", result.data or []))


# job 상태(succeeded/failed/cancelled/timed_out) → republish_jobs 상태 매핑
_JOB_STATUS_TO_REPUBLISH_STATUS = {
    "succeeded": "completed",
    "failed": "failed",
    "cancelled": "failed",
    "timed_out": "failed",
}


def on_pipeline_job_finished(job: Any) -> None:
    """job_manager 의 종료 훅. pipeline job 이 republish 와 연결되어 있으면 동기화.

    1. republish_jobs status 갱신 (queued/running → completed/failed)
    2. failed/cancelled/timed_out 인 경우 부모 publication 을 자동 큐 복귀
       (workflow_status: republishing → action_required) — 사용자가 다시
       시도하거나 다른 액션을 취할 수 있도록.
    """
    if job.type != "pipeline":
        return
    new_status = _JOB_STATUS_TO_REPUBLISH_STATUS.get(job.status)
    if new_status is None:
        return  # pending/running 등 종료 외 상태는 무시
    affected = update_republish_job_status(job.id, new_status)
    if affected == 0:
        return  # 일반 파이프라인 job (재발행 아님) — 종료
    if new_status == "failed":
        _auto_requeue_failed_republish(job.id)


def _auto_requeue_failed_republish(pipeline_job_id: str) -> None:
    """실패한 재발행 job 의 부모를 큐로 복귀시킨다."""
    from application.publication_actions_orchestrator import auto_requeue

    client = get_client()
    result = (
        client.table(_REPUBLISH_JOBS_TABLE)
        .select("source_publication_id")
        .eq("pipeline_job_id", pipeline_job_id)
        .limit(1)
        .execute()
    )
    rows = cast("list[dict[str, Any]]", result.data or [])
    if not rows:
        return
    source_id = rows[0].get("source_publication_id")
    if not source_id:
        return
    try:
        auto_requeue(
            source_id,
            trigger="republish_job_failed",
            note=f"재발행 파이프라인 실패 (job={pipeline_job_id})",
        )
    except Exception:
        logger.exception(
            "auto_requeue.failed_after_republish source=%s job=%s",
            source_id,
            pipeline_job_id,
        )


def recover_stuck_republish_jobs() -> int:
    """서버 재시작 시 in-memory job_manager 와 끊긴 republish_jobs 회수.

    queued/running 상태로 남아있는 모든 republish_jobs 를 failed 처리하고,
    부모 publication 을 action_required 로 복귀시킨다. job_manager 가
    in-memory 라 재시작 후엔 모든 active republish 는 정의상 stuck.

    Lifespan startup 에서 1회 호출. 영향 행 수 반환.
    """
    client = get_client()
    result = (
        client.table(_REPUBLISH_JOBS_TABLE)
        .select("pipeline_job_id, source_publication_id")
        .in_("status", ["queued", "running"])
        .execute()
    )
    rows = cast("list[dict[str, Any]]", result.data or [])
    recovered = 0
    for row in rows:
        pipeline_job_id = row.get("pipeline_job_id")
        if not pipeline_job_id:
            continue
        try:
            update_republish_job_status(pipeline_job_id, "failed")
            _auto_requeue_failed_republish(pipeline_job_id)
            recovered += 1
        except Exception:
            logger.exception("recover_stuck_republish.failed pipeline_job_id=%s", pipeline_job_id)
    if recovered > 0:
        logger.warning("recover_stuck_republish.summary recovered=%d", recovered)
    return recovered
