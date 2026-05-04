"""batch 도메인 Supabase CRUD. SPEC-BATCH.md §4 매핑."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from config.supabase import get_client
from domain.batch.model import (
    BatchStatus,
    ItemStatus,
    KeywordBatch,
    KeywordBatchItem,
)

logger = logging.getLogger(__name__)

_BATCH_TABLE = "keyword_batches"
_ITEM_TABLE = "keyword_batch_items"


def insert_batch(batch: KeywordBatch) -> KeywordBatch:
    """batch row insert → id 채워서 반환."""
    payload = _batch_to_payload(batch)
    result = get_client().table(_BATCH_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("keyword_batches insert: no row returned")
    return _row_to_batch(cast("dict[str, Any]", rows[0]))


def insert_items(items: list[KeywordBatchItem]) -> list[KeywordBatchItem]:
    """items 일괄 insert → id 채워진 결과 반환. 빈 입력은 빈 리스트."""
    if not items:
        return []
    payloads = [_item_to_payload(it) for it in items]
    result = get_client().table(_ITEM_TABLE).insert(payloads).execute()
    rows = result.data or []
    return [_row_to_item(cast("dict[str, Any]", r)) for r in rows]


def get_batch(batch_id: str) -> KeywordBatch | None:
    result = get_client().table(_BATCH_TABLE).select("*").eq("id", batch_id).limit(1).execute()
    rows = result.data or []
    return _row_to_batch(cast("dict[str, Any]", rows[0])) if rows else None


def list_batches(limit: int = 20) -> list[KeywordBatch]:
    result = (
        get_client()
        .table(_BATCH_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    return [_row_to_batch(cast("dict[str, Any]", r)) for r in rows]


def list_items(
    batch_id: str, *, status: str | None = None, limit: int = 500
) -> list[KeywordBatchItem]:
    query = get_client().table(_ITEM_TABLE).select("*").eq("batch_id", batch_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=False).limit(limit).execute()
    rows = result.data or []
    return [_row_to_item(cast("dict[str, Any]", r)) for r in rows]


def get_item(item_id: str) -> KeywordBatchItem | None:
    result = get_client().table(_ITEM_TABLE).select("*").eq("id", item_id).limit(1).execute()
    rows = result.data or []
    return _row_to_item(cast("dict[str, Any]", rows[0])) if rows else None


def update_item_status(
    item_id: str,
    status: ItemStatus,
    *,
    error: str | None = None,
    job_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    retry_count: int | None = None,
) -> None:
    """item status + 메타 갱신. None 인 인자는 변경 안 함."""
    payload: dict[str, Any] = {"status": status}
    if error is not None:
        payload["error"] = error
    if job_id is not None:
        payload["job_id"] = job_id
    if started_at is not None:
        payload["started_at"] = started_at.isoformat()
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    if retry_count is not None:
        payload["retry_count"] = retry_count
    get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()


def update_item_result(
    item_id: str,
    *,
    pattern_card_id: str | None = None,
    generated_content_id: str | None = None,
    compliance_passed: bool | None = None,
    quality_score: float | None = None,
    search_volume: int | None = None,
    difficulty_grade: str | None = None,
) -> None:
    """item 결과 메타 partial update. 모든 인자 None 이면 noop (Supabase 호출 0).

    SPEC-BATCH §3 Phase 2 PR1 — `_run_operation` 이 회수한 id 를 batch item 에
    반영해 BatchProgressTable 의 결과 직링크를 가능하게 한다. status 머신은
    `update_item_status` 가 담당 — 책임 분리.

    PR2 추가 — `search_volume`/`difficulty_grade` 는 사전 필터 결과 메타 (통과·미달
    무관하게 저장되어 검수 큐에서 운영자가 확인).
    """
    payload: dict[str, Any] = {}
    if pattern_card_id is not None:
        payload["pattern_card_id"] = pattern_card_id
    if generated_content_id is not None:
        payload["generated_content_id"] = generated_content_id
    if compliance_passed is not None:
        payload["compliance_passed"] = compliance_passed
    if quality_score is not None:
        payload["quality_score"] = quality_score
    if search_volume is not None:
        payload["search_volume"] = search_volume
    if difficulty_grade is not None:
        payload["difficulty_grade"] = difficulty_grade
    if not payload:
        return
    get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()


def find_primary_in_cluster(batch_id: str, cluster_id: str) -> KeywordBatchItem | None:
    """같은 batch 안에서 cluster_id 의 primary item 1건 조회.

    PR2 cluster 재사용 — member 가 자기 cluster 의 primary 를 찾아 PatternCard 재사용.
    None: primary 부재 (잘못된 CSV) 또는 cluster_id 무효.
    """
    result = (
        get_client()
        .table(_ITEM_TABLE)
        .select("*")
        .eq("batch_id", batch_id)
        .eq("cluster_id", cluster_id)
        .eq("cluster_role", "primary")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return _row_to_item(cast("dict[str, Any]", rows[0])) if rows else None


def update_batch_status(
    batch_id: str,
    status: BatchStatus,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    counters: dict[str, int] | None = None,
) -> None:
    payload: dict[str, Any] = {"status": status}
    if started_at is not None:
        payload["started_at"] = started_at.isoformat()
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    if counters:
        payload.update(counters)
    get_client().table(_BATCH_TABLE).update(payload).eq("id", batch_id).execute()


def count_items_by_status(batch_id: str) -> dict[str, int]:
    """batch 의 status 별 카운터 — counters 갱신용 집계."""
    items = list_items(batch_id, limit=10_000)
    counters: dict[str, int] = {
        "succeeded_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "needs_review_count": 0,
    }
    for it in items:
        if it.status == "succeeded":
            counters["succeeded_count"] += 1
        elif it.status == "failed":
            counters["failed_count"] += 1
        elif it.status == "skipped":
            counters["skipped_count"] += 1
        elif it.status == "needs_review":
            counters["needs_review_count"] += 1
    return counters


def claim_next_queued_item(batch_id: str) -> KeywordBatchItem | None:
    """queued 상태 item 한 건을 가져와 running 으로 마킹.

    Phase 1 단일 프로세스 전제 — 같은 컨테이너 안의 worker 끼리는 SELECT 후 UPDATE
    사이 race 가 있을 수 있으나 BatchJobManager 가 in-process lock 으로 보호.
    멀티 워커 진입 시 advisory lock 또는 row-level lock 필요.
    """
    queued = list_items(batch_id, status="queued", limit=1)
    if not queued:
        return None
    item = queued[0]
    if item.id is None:
        return None
    update_item_status(
        item.id,
        "running",
        started_at=datetime.now(UTC),
    )
    return get_item(item.id)


# ── payload / row 변환 ──


def _batch_to_payload(b: KeywordBatch) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": b.name,
        "mode": b.mode,
        "status": b.status,
        "total_count": b.total_count,
        "succeeded_count": b.succeeded_count,
        "failed_count": b.failed_count,
        "skipped_count": b.skipped_count,
        "needs_review_count": b.needs_review_count,
        "estimated_cost_usd": b.estimated_cost_usd,
        "cluster_dedupe": b.cluster_dedupe,
        "auto_publish_enabled": b.auto_publish_enabled,
    }
    if b.min_search_volume is not None:
        payload["min_search_volume"] = b.min_search_volume
    if b.max_difficulty is not None:
        payload["max_difficulty"] = b.max_difficulty
    return payload


def _item_to_payload(item: KeywordBatchItem) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "batch_id": item.batch_id,
        "keyword": item.keyword,
        "operation": item.operation,
        "mode": item.mode,
        "priority": item.priority,
        "cluster_role": item.cluster_role,
        "status": item.status,
        "retry_count": item.retry_count,
        "max_retries": item.max_retries,
        "estimated_cost_usd": item.estimated_cost_usd,
        "review_status": item.review_status,
    }
    # nullable 필드는 값이 있을 때만
    for k, v in {
        "cluster_id": item.cluster_id,
        "intent": item.intent,
        "region": item.region,
        "brand_id": item.brand_id,
        "target_url": item.target_url,
        "memo": item.memo,
        "job_id": item.job_id,
        "error": item.error,
        "search_volume": item.search_volume,
        "difficulty_grade": item.difficulty_grade,
        "pattern_card_id": item.pattern_card_id,
        "generated_content_id": item.generated_content_id,
        "quality_score": item.quality_score,
        "compliance_passed": item.compliance_passed,
    }.items():
        if v is not None:
            payload[k] = v
    return payload


def _row_to_batch(row: dict[str, Any]) -> KeywordBatch:
    return KeywordBatch(
        id=row.get("id"),
        name=row.get("name"),
        mode=row.get("mode") or "now",
        status=row.get("status") or "queued",
        total_count=row.get("total_count") or 0,
        succeeded_count=row.get("succeeded_count") or 0,
        failed_count=row.get("failed_count") or 0,
        skipped_count=row.get("skipped_count") or 0,
        needs_review_count=row.get("needs_review_count") or 0,
        estimated_cost_usd=float(row.get("estimated_cost_usd") or 0),
        min_search_volume=row.get("min_search_volume"),
        max_difficulty=row.get("max_difficulty"),
        cluster_dedupe=bool(row.get("cluster_dedupe", True)),
        auto_publish_enabled=bool(row.get("auto_publish_enabled", False)),
        created_at=row.get("created_at"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
    )


def _row_to_item(row: dict[str, Any]) -> KeywordBatchItem:
    return KeywordBatchItem(
        id=row.get("id"),
        batch_id=row["batch_id"],
        keyword=row["keyword"],
        operation=row.get("operation") or "analyze",
        mode=row.get("mode") or "now",
        priority=row.get("priority") or 5,
        cluster_id=row.get("cluster_id"),
        cluster_role=row.get("cluster_role") or "member",
        intent=row.get("intent"),
        region=row.get("region"),
        brand_id=row.get("brand_id"),
        target_url=row.get("target_url"),
        memo=row.get("memo"),
        status=row.get("status") or "queued",
        retry_count=row.get("retry_count") or 0,
        max_retries=row.get("max_retries") or 2,
        job_id=row.get("job_id"),
        error=row.get("error"),
        estimated_cost_usd=float(row.get("estimated_cost_usd") or 0),
        search_volume=row.get("search_volume"),
        difficulty_grade=row.get("difficulty_grade"),
        pattern_card_id=row.get("pattern_card_id"),
        generated_content_id=row.get("generated_content_id"),
        quality_score=row.get("quality_score"),
        compliance_passed=row.get("compliance_passed"),
        review_status=row.get("review_status") or "pending",
        reviewer=row.get("reviewer"),
        reviewed_at=row.get("reviewed_at"),
        publication_id=row.get("publication_id"),
        published_at=row.get("published_at"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
    )
