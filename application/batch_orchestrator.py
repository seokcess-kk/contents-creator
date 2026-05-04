"""키워드 배치 운영 use case. SPEC-BATCH.md §3 Phase 1.

도메인 격리: domain/batch 는 단일 흐름을 호출하지 않으므로 본 오케스트레이터가
    domain/batch (CSV/storage/모델)
+   application/orchestrator (run_pipeline / run_analyze_only / run_generate_only)
+   application/batch_job_manager (worker pool)
을 합성한다.

Phase 1 범위:
- mode='now' 만 처리. 'overnight'/'auto' 는 NotSupportedYetError.
- operation='analyze' 가 default.
- 상태 머신 단순: queued → running → succeeded / needs_review / failed.
- FK 회수 보강 전 — (job_id, slug, keyword) triple link 만.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from application import batch_job_manager, orchestrator
from application.job_context import current_job_id
from application.models import GenerateResult, PipelineResult
from domain.batch import csv_parser, storage
from domain.batch.model import (
    BatchEnqueueResult,
    KeywordBatch,
    KeywordBatchItem,
    NotSupportedYetError,
)

logger = logging.getLogger(__name__)


def enqueue_from_csv(
    csv_text: str,
    *,
    mode: str = "now",
    name: str | None = None,
    auto_dispatch: bool = True,
) -> BatchEnqueueResult:
    """CSV 텍스트 → batch + items insert. 검증 + 중복 분류.

    auto_dispatch=True 면 즉시 worker pool 에 dispatch (Phase 1 mode='now' 한정).

    Raises:
        NotSupportedYetError: mode 가 'overnight'/'auto'.
        ValueError: CSV 형식 오류 (헤더 누락 등) — API 가 400 으로 변환.
    """
    if mode != "now":
        raise NotSupportedYetError(
            f"Phase 1 은 mode='now' 만 지원합니다. 'overnight'/'auto' 는 Phase 3 예정. (요청: {mode!r})"
        )

    parsed_items, skipped, failed = csv_parser.parse_csv(
        csv_text, batch_id="pending", default_mode=mode
    )

    batch = KeywordBatch(
        name=name,
        mode=mode,  # type: ignore[arg-type]
        total_count=len(parsed_items),
    )
    inserted_batch = storage.insert_batch(batch)
    if inserted_batch.id is None:
        raise RuntimeError("batch insert: id 없음")

    # 파싱된 items 의 batch_id 를 진짜 id 로 갱신
    for it in parsed_items:
        it.batch_id = inserted_batch.id

    inserted_items = storage.insert_items(parsed_items)

    if auto_dispatch and inserted_items:
        manager = batch_job_manager.get_default_manager()
        for it in inserted_items:
            if it.id is not None:
                manager.submit(_dispatch_item_safely, it.id)

    logger.info(
        "batch.enqueued batch_id=%s total=%d created=%d skipped=%d failed=%d "
        "mode=%s auto_dispatch=%s",
        inserted_batch.id,
        len(parsed_items),
        len(inserted_items),
        len(skipped),
        len(failed),
        mode,
        auto_dispatch,
    )

    return BatchEnqueueResult(
        batch_id=inserted_batch.id,
        total=len(parsed_items) + len(skipped) + len(failed),
        created=len(inserted_items),
        skipped=skipped,
        failed=failed,
    )


def _dispatch_item_safely(item_id: str) -> None:
    """worker thread 진입점 — _dispatch_item 의 모든 예외를 흡수해 status='failed'."""
    try:
        _dispatch_item(item_id)
    except Exception as exc:
        logger.exception("batch.dispatch_failed item_id=%s", item_id)
        try:
            storage.update_item_status(
                item_id,
                "failed",
                error=f"dispatcher 예외: {type(exc).__name__}: {exc}",
                completed_at=datetime.now(UTC),
            )
        except Exception:
            logger.exception("batch.dispatch_failed_status_update item_id=%s", item_id)


def _dispatch_item(item_id: str) -> None:
    """단일 item dispatch — operation 분기 → 단일 흐름 호출 → 상태 갱신.

    이미 succeeded/failed/skipped 상태면 no-op (idempotent).
    retry 시도 시 retry_count +1, max_retries 초과 시 failed 확정.
    """
    item = storage.get_item(item_id)
    if item is None:
        logger.warning("batch.dispatch.item_missing item_id=%s", item_id)
        return
    if item.status in ("succeeded", "failed", "skipped"):
        logger.info("batch.dispatch.skip_done item_id=%s status=%s", item_id, item.status)
        return

    job_id = f"batch-{item_id[:8]}-{uuid.uuid4().hex[:6]}"
    storage.update_item_status(
        item_id,
        "running",
        job_id=job_id,
        started_at=datetime.now(UTC),
    )

    try:
        _run_operation(item, job_id)
    except Exception as exc:
        _handle_item_failure(item, exc)
        return

    storage.update_item_status(
        item_id,
        "succeeded",
        completed_at=datetime.now(UTC),
    )
    logger.info(
        "batch.item_succeeded item_id=%s keyword=%s operation=%s",
        item_id,
        item.keyword,
        item.operation,
    )


def _run_operation(item: KeywordBatchItem, job_id: str) -> None:
    """operation 별 분기 — 단일 흐름 함수를 그대로 호출 (시그니처 불변)."""
    if item.operation == "analyze":
        orchestrator.run_analyze_only(item.keyword)
    elif item.operation == "generate":
        result: GenerateResult = orchestrator.run_generate_only(keyword=item.keyword)
        if result.status == "failed":
            raise RuntimeError(result.error or "generate 실패")
    elif item.operation == "pipeline":
        pipeline_result: PipelineResult = orchestrator.run_pipeline(item.keyword)
        if pipeline_result.status == "failed":
            raise RuntimeError(pipeline_result.error or "pipeline 실패")
    else:  # pragma: no cover — Pydantic Literal 로 미리 차단
        raise ValueError(f"알 수 없는 operation: {item.operation}")
    # job_id 는 logger 식별용 (current_job_id() 와는 별개 — single-flow 의 job_context 영향 X)
    logger.debug(
        "batch.operation_done item_id=%s job_id=%s operation=%s",
        item.id,
        job_id,
        item.operation,
    )


def _handle_item_failure(item: KeywordBatchItem, exc: Exception) -> None:
    """실패 후 retry 또는 failed 확정."""
    if item.id is None:
        return
    next_retry = item.retry_count + 1
    err_msg = f"{type(exc).__name__}: {exc}"
    if next_retry <= item.max_retries:
        # 재시도 — 같은 worker pool 에 재투입
        storage.update_item_status(
            item.id,
            "queued",
            error=f"[retry {next_retry}/{item.max_retries}] {err_msg}",
            retry_count=next_retry,
        )
        logger.warning(
            "batch.item_retry item_id=%s keyword=%s retry=%d/%d err=%s",
            item.id,
            item.keyword,
            next_retry,
            item.max_retries,
            err_msg,
        )
        batch_job_manager.get_default_manager().submit(_dispatch_item_safely, item.id)
    else:
        storage.update_item_status(
            item.id,
            "failed",
            error=err_msg,
            completed_at=datetime.now(UTC),
            retry_count=next_retry,
        )
        logger.error(
            "batch.item_failed item_id=%s keyword=%s retries_exhausted err=%s",
            item.id,
            item.keyword,
            err_msg,
        )


def retry_item(item_id: str) -> None:
    """수동 재시도 — failed item 을 queued 로 복귀 + dispatch.

    max_retries 무시하고 1회 강제 재시도. 사용자가 운영 중 트리거.
    """
    item = storage.get_item(item_id)
    if item is None:
        raise ValueError(f"item 미존재: {item_id}")
    if item.status not in ("failed", "succeeded", "needs_review"):
        raise ValueError(
            f"재시도 가능 상태 아님 (현재: {item.status}). queued/running 은 자동 처리됩니다."
        )
    storage.update_item_status(
        item_id,
        "queued",
        error=None,
        retry_count=item.retry_count,  # 수동 재시도는 카운터 증가 X
    )
    batch_job_manager.get_default_manager().submit(_dispatch_item_safely, item_id)
    logger.info("batch.manual_retry item_id=%s keyword=%s", item_id, item.keyword)


def cancel_batch(batch_id: str) -> int:
    """batch 의 queued items 를 모두 cancelled 로 마킹.

    이미 running 인 item 은 그대로 진행 (worker 중단 메커니즘은 Phase 3 검토).
    Returns: cancelled 된 item 수.
    """
    batch = storage.get_batch(batch_id)
    if batch is None:
        raise ValueError(f"batch 미존재: {batch_id}")

    queued = storage.list_items(batch_id, status="queued", limit=10_000)
    cancelled = 0
    for it in queued:
        if it.id is None:
            continue
        storage.update_item_status(
            it.id,
            "skipped",
            error="cancelled by user",
            completed_at=datetime.now(UTC),
        )
        cancelled += 1

    if cancelled > 0:
        # batch counters + status 갱신
        counters = storage.count_items_by_status(batch_id)
        storage.update_batch_status(batch_id, "cancelled", counters=counters)

    logger.info("batch.cancelled batch_id=%s cancelled_items=%d", batch_id, cancelled)
    return cancelled


def recompute_batch_status(batch_id: str) -> KeywordBatch | None:
    """모든 item 처리 후 batch status + counters 재계산.

    호출 시점: 마지막 item dispatch 완료 후. Phase 1 은 worker 가 자체적으로
    호출 안 하고 (race 회피), 외부 polling 또는 cron 으로 트리거.
    """
    batch = storage.get_batch(batch_id)
    if batch is None:
        return None
    counters = storage.count_items_by_status(batch_id)
    finished = sum(counters.values())
    new_status: str
    if finished == 0:
        new_status = "queued"
    elif finished < batch.total_count:
        new_status = "running"
    else:
        new_status = "completed"
    storage.update_batch_status(
        batch_id,
        new_status,  # type: ignore[arg-type]
        counters=counters,
        completed_at=datetime.now(UTC) if new_status == "completed" else None,
    )
    return storage.get_batch(batch_id)


__all__ = [
    "enqueue_from_csv",
    "retry_item",
    "cancel_batch",
    "recompute_batch_status",
    "_dispatch_item_safely",  # tests
]


# unused import 회피 (job_context 는 향후 single-flow 와의 통합점)
_ = current_job_id
