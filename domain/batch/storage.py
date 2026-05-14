"""batch 도메인 Supabase CRUD. SPEC-BATCH.md §4 매핑."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from config.supabase import get_client
from domain.batch.model import (
    BatchStatus,
    FailureCategory,
    ItemStatus,
    KeywordBatch,
    KeywordBatchItem,
    ReviewStatus,
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


_FAILURE_STATUSES: set[ItemStatus] = {"failed", "skipped", "needs_review"}


def update_item_status(
    item_id: str,
    status: ItemStatus,
    *,
    error: str | None = None,
    failure_category: FailureCategory | None = None,
    job_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    retry_count: int | None = None,
) -> None:
    """item status + 메타 갱신. None 인 인자는 변경 안 함.

    error 컬럼은 예외 — status 가 'failed' 외 다른 상태로 전환될 때 자동으로
    NULL 로 clear 한다. 재시도 후 정상 발행 시 옛 실패 메시지(예: 'SERP 수집
    실패...')가 운영 화면에 잔존하던 사고 차단. failed 로 전환 시에만 error 가
    None 이면 옛 메시지 보존 (호출자가 명시 전달 안 한 경우).

    failure_category 도 동일 — failed/skipped/needs_review 외 상태로 전환되면
    NULL 로 clear. /insights 집계의 정합성 보장 (success row 에 잔존 카테고리 X).
    failure_category 컬럼이 DB 에 없는 환경(구버전 스키마)에서는 graceful — 한 번
    실패하면 컬럼 빼고 retry.
    """
    payload: dict[str, Any] = {"status": status}
    if error is not None:
        payload["error"] = error
    elif status != "failed":
        payload["error"] = None
    if failure_category is not None:
        payload["failure_category"] = failure_category
    elif status not in _FAILURE_STATUSES:
        payload["failure_category"] = None
    if job_id is not None:
        payload["job_id"] = job_id
    if started_at is not None:
        payload["started_at"] = started_at.isoformat()
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    if retry_count is not None:
        payload["retry_count"] = retry_count
    try:
        get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()
    except Exception:
        if "failure_category" in payload:
            logger.warning(
                "batch.update_item_status.failure_category_column_missing item_id=%s — fallback",
                item_id,
            )
            del payload["failure_category"]
            get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()
        else:
            raise


def update_item_result(
    item_id: str,
    *,
    pattern_card_id: str | None = None,
    generated_content_id: str | None = None,
    compliance_passed: bool | None = None,
    quality_score: float | None = None,
    search_volume: int | None = None,
    difficulty_grade: str | None = None,
    compliance_violations: list[str] | None = None,
) -> None:
    """item 결과 메타 partial update. 모든 인자 None 이면 noop (Supabase 호출 0).

    SPEC-BATCH §3 Phase 2 PR1 — `_run_operation` 이 회수한 id 를 batch item 에
    반영해 BatchProgressTable 의 결과 직링크를 가능하게 한다. status 머신은
    `update_item_status` 가 담당 — 책임 분리.

    PR2 추가 — `search_volume`/`difficulty_grade` 는 사전 필터 결과 메타 (통과·미달
    무관하게 저장되어 검수 큐에서 운영자가 확인).

    Phase B14 추가 — `compliance_violations` 는 위반된 의료법 카테고리 리스트
    (검수 큐 tooltip 용). DB jsonb 컬럼이 미적용 환경에서는 graceful 처리 — Supabase
    오류 시 violations 만 빼고 retry.
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
    if compliance_violations is not None:
        payload["compliance_violations"] = compliance_violations
    if not payload:
        return
    try:
        get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()
    except Exception as exc:
        # Phase B14 — compliance_violations 컬럼 미적용 환경 graceful: 빼고 retry.
        if "compliance_violations" in payload:
            logger.warning(
                "batch.update_item_result.violations_column_missing item_id=%s — fallback",
                item_id,
            )
            del payload["compliance_violations"]
            if payload:
                get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()
            return
        raise exc


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


def find_pattern_card_by_triple(slug: str, keyword: str) -> str | None:
    """slug + keyword 로 pattern_cards 의 가장 최근 row id 조회.

    SPEC-BATCH §3 Phase 2 PR4 — fire-and-forget id 회수 실패 시 사후 백필.
    Supabase 미설정/실패/부재 시 None.
    """
    try:
        result = (
            get_client()
            .table("pattern_cards")
            .select("id")
            .eq("slug", slug)
            .eq("keyword", keyword)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "batch.find_pattern_card.failed slug=%s keyword=%s", slug, keyword, exc_info=True
        )
        return None
    rows = result.data or []
    if not rows:
        return None
    raw = cast("dict[str, Any]", rows[0]).get("id")
    return str(raw) if raw is not None else None


def find_generated_content_by_triple(job_id: str | None, slug: str, keyword: str) -> str | None:
    """generated_contents 의 id 사후 매칭. job_id 우선 + slug+keyword fallback.

    SPEC-BATCH §3 Phase 2 PR4 — 백필. job_id None 이면 1차 매칭 스킵.
    """
    client = get_client()

    # 1차: job_id + slug + keyword (job_id 있을 때만)
    if job_id is not None:
        try:
            result = (
                client.table("generated_contents")
                .select("id")
                .eq("job_id", job_id)
                .eq("slug", slug)
                .eq("keyword", keyword)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                raw = cast("dict[str, Any]", rows[0]).get("id")
                if raw is not None:
                    return str(raw)
        except Exception:
            logger.warning(
                "batch.find_gen_content.primary_failed job_id=%s slug=%s",
                job_id,
                slug,
                exc_info=True,
            )

    # 2차 fallback: slug + keyword (가장 최근)
    try:
        result = (
            client.table("generated_contents")
            .select("id")
            .eq("slug", slug)
            .eq("keyword", keyword)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "batch.find_gen_content.fallback_failed slug=%s keyword=%s",
            slug,
            keyword,
            exc_info=True,
        )
        return None
    rows = result.data or []
    if not rows:
        return None
    raw = cast("dict[str, Any]", rows[0]).get("id")
    return str(raw) if raw is not None else None


def update_item_review(
    item_id: str,
    *,
    review_status: ReviewStatus,
    status: ItemStatus | None = None,
    reviewer: str | None = None,
) -> None:
    """검수 액션 메타 갱신. status 가 None 아니면 동시에 status 도 전환 (approve 시 사용).

    SPEC-BATCH §3 Phase 2 PR3 — 검수 액션:
      - approve: review_status='approved', status='ready_to_publish'
      - needs_fix: review_status='needs_fix' (status 그대로)
      - reject: review_status='rejected' (status 그대로, 예외 상태)
    reviewed_at 은 항상 now() 로 갱신. reviewer None 이면 payload 미포함.
    """
    payload: dict[str, Any] = {
        "review_status": review_status,
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    if status is not None:
        payload["status"] = status
        payload["completed_at"] = datetime.now(UTC).isoformat()
    if reviewer is not None:
        payload["reviewer"] = reviewer
    get_client().table(_ITEM_TABLE).update(payload).eq("id", item_id).execute()


def list_review_pending_items(
    batch_id: str,
    limit: int = 200,
    *,
    review_status: str | None = "pending",
    item_status: str | None = "needs_review",
) -> list[KeywordBatchItem]:
    """검수 큐 — review_status / item_status 필터 지원 (Phase B9 fix #4 확장).

    탭 별 의미 (frontend BatchReviewQueue 가 호출):
      - pending  : review_status=pending  + status=needs_review  (검수 대기, default)
      - needs_fix: review_status=needs_fix + status=needs_review (수정 필요 마킹됨)
      - approved : review_status=approved + status=ready_to_publish (승인됨)
      - rejected : review_status=rejected + status=needs_review (거부 예외)
    None 인자는 해당 필터 적용 안 함.
    """
    query = get_client().table(_ITEM_TABLE).select("*").eq("batch_id", batch_id)
    if item_status is not None:
        query = query.eq("status", item_status)
    if review_status is not None:
        query = query.eq("review_status", review_status)
    result = query.order("created_at", desc=False).limit(limit).execute()
    rows = result.data or []
    return [_row_to_item(cast("dict[str, Any]", r)) for r in rows]


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
        # Phase 2 PR3 — ready_to_publish_count 는 DB 컬럼 미존재. payload 에서 제외.
        # in-memory 응답에만 포함되며 매번 count_items_by_status 가 재집계.
        payload.update({k: v for k, v in counters.items() if k != "ready_to_publish_count"})
    get_client().table(_BATCH_TABLE).update(payload).eq("id", batch_id).execute()


def count_items_by_status(batch_id: str) -> dict[str, int]:
    """batch 의 status 별 카운터 — counters 갱신용 집계.

    Phase 2 PR3 — `ready_to_publish_count` 추가 (succeeded 와 의미 분리).
    DB 컬럼은 succeeded_count/failed_count/skipped_count/needs_review_count 4개만 저장.
    ready_to_publish_count 는 in-memory 응답에만 포함 (GET /batches/{id} 가 매번 재집계).
    """
    items = list_items(batch_id, limit=10_000)
    counters: dict[str, int] = {
        "succeeded_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "needs_review_count": 0,
        "ready_to_publish_count": 0,
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
        elif it.status == "ready_to_publish":
            counters["ready_to_publish_count"] += 1
    return counters


def aggregate_pipeline_counts(batch_limit: int = 100) -> dict[str, int]:
    """모든 최근 batch 의 status 별 합산 카운트.

    Phase B11 (Keyword Pipeline 통합 대시보드) — 사용자 운영 철학 §9 의 첫 화면.
    candidate→generated→ready_to_publish→published 단계별 가시성 제공.

    `batch_limit`: 가장 최근 N batch 만 집계 (성능 보호, default 100).
    """
    batches = list_batches(limit=batch_limit)
    aggregated: dict[str, int] = {
        "queued": 0,
        "running": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "needs_review": 0,
        "ready_to_publish": 0,
        "published": 0,
        "total": 0,
    }
    for b in batches:
        if b.id is None:
            continue
        try:
            counters = count_items_by_status(b.id)
        except Exception:
            logger.warning("aggregate_pipeline.batch_failed batch_id=%s", b.id, exc_info=True)
            continue
        aggregated["succeeded"] += counters.get("succeeded_count", 0)
        aggregated["failed"] += counters.get("failed_count", 0)
        aggregated["skipped"] += counters.get("skipped_count", 0)
        aggregated["needs_review"] += counters.get("needs_review_count", 0)
        aggregated["ready_to_publish"] += counters.get("ready_to_publish_count", 0)
        aggregated["total"] += b.total_count
    # published 카운트는 별도 — keyword_batch_items.publication_id 가 채워진 row.
    aggregated["published"] = _count_published_items()
    # queued / running 은 batch.status='running' 인 batch 의 item 만 카운트하면 정확하지만,
    # 단순 집계로 total - 종결합으로 추정.
    terminal = (
        aggregated["succeeded"]
        + aggregated["failed"]
        + aggregated["skipped"]
        + aggregated["needs_review"]
        + aggregated["ready_to_publish"]
    )
    aggregated["queued"] = max(0, aggregated["total"] - terminal)
    return aggregated


def _count_published_items() -> int:
    """publication_id 가 채워진 keyword_batch_items 카운트.

    SPEC-BATCH 의 운영 흐름 §9 — published → tracking 단계 가시화.
    Supabase 부재/실패 시 0.
    """
    try:
        result = (
            get_client()
            .table(_ITEM_TABLE)
            .select("id", count="exact")
            .not_.is_("publication_id", "null")
            .limit(1)
            .execute()
        )
        return int(getattr(result, "count", 0) or 0)
    except Exception:
        logger.warning("aggregate_pipeline.published_count_failed", exc_info=True)
        return 0


def list_items_by_global_status(status: str, limit: int = 50) -> list[KeywordBatchItem]:
    """모든 batch 통합 status 별 item 목록 (created_at desc).

    Pipeline 페이지의 status 별 keyword 목록 표시용. batch_id 무관.
    """
    result = (
        get_client()
        .table(_ITEM_TABLE)
        .select("*")
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    return [_row_to_item(cast("dict[str, Any]", r)) for r in rows]


def list_items_filtered(
    *,
    statuses: list[str] | None = None,
    failure_category: str | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[KeywordBatchItem], int]:
    """글로벌 item 목록 + 총 count (insights 키워드 행 뷰용).

    statuses: 빈 리스트/None 이면 필터 없음 (전체). 여러 status OR 조건.
    failure_category: 단일 값 필터.
    batch_id: 단일 batch 한정 (선택).
    limit/offset: 페이지네이션 (PostgREST range).
    """
    query = (
        get_client().table(_ITEM_TABLE).select("*", count="exact")  # type: ignore[arg-type]
    )
    if statuses:
        query = query.in_("status", statuses)
    if failure_category:
        query = query.eq("failure_category", failure_category)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    result = (
        query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    rows = result.data or []
    items = [_row_to_item(cast("dict[str, Any]", r)) for r in rows]
    total = int(getattr(result, "count", None) or 0)
    return items, total


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


def claim_item_for_dispatch(item_id: str, *, job_id: str) -> KeywordBatchItem | None:
    """status='queued' 인 item 을 atomic 하게 'running' 으로 claim (Phase 3 PR2).

    PostgREST 의 `.eq("status", "queued")` 필터가 update 의 WHERE 절에 합성되어
    "status=queued AND id=?" 한 row 만 atomic update. 두 worker 가 동시에 호출해도
    한쪽만 1 row 반환받고 다른 쪽은 0 row → None 반환.

    멀티 워커 진입 (`scripts/run_batch.py --dispatch-overnight` 외부 cron + web
    process) 시 동일 item 중복 실행 차단. SPEC-BATCH §3 Phase 3 PR2.

    반환:
        KeywordBatchItem: claim 성공 (이 worker 만 처리할 권한 획득)
        None: 이미 다른 worker 가 잡았거나 status≠queued 또는 row 부재
    """
    payload: dict[str, Any] = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "job_id": job_id,
    }
    result = (
        get_client()
        .table(_ITEM_TABLE)
        .update(payload)
        .eq("id", item_id)
        .eq("status", "queued")
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return _row_to_item(cast("dict[str, Any]", rows[0]))


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
        "blog_channel_id": item.blog_channel_id,
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
        blog_channel_id=row.get("blog_channel_id"),
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
        compliance_violations=row.get("compliance_violations") or [],
        review_status=row.get("review_status") or "pending",
        reviewer=row.get("reviewer"),
        reviewed_at=row.get("reviewed_at"),
        publication_id=row.get("publication_id"),
        published_at=row.get("published_at"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
    )
