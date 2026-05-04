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
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from application import batch_job_manager, orchestrator
from application.job_context import current_job_id
from application.models import AnalyzeResult, GenerateResult, PipelineResult, StageStatus
from config.settings import settings
from domain.batch import csv_parser, storage
from domain.batch.model import (
    BatchEnqueueResult,
    KeywordBatch,
    KeywordBatchItem,
    NotSupportedYetError,
)

logger = logging.getLogger(__name__)

# DifficultyGrade 의 우선순위 dict — string enum 직접 비교 불가하므로 정수로 매핑.
# 큰 값이 더 어려움 (LOW < MEDIUM < HIGH < MISSING).
_DIFFICULTY_RANK: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "missing": 3,
}


def enqueue_from_csv(
    csv_text: str,
    *,
    mode: str = "now",
    name: str | None = None,
    auto_dispatch: bool = True,
    min_search_volume: int | None = None,
    max_difficulty: str | None = None,
    cluster_dedupe: bool = False,
) -> BatchEnqueueResult:
    """CSV 텍스트 → batch + items insert. 검증 + 중복 분류.

    auto_dispatch=True 면 즉시 worker pool 에 dispatch (Phase 1 mode='now' 한정).

    Phase 2 PR2 추가:
        min_search_volume / max_difficulty: 사전 필터 임계값. None 이면 필터 안 함.
        cluster_dedupe: 같은 cluster_id 의 primary→member PatternCard 재사용 활성.
            **default False** (본문 유사도로 인한 1페이지 노출 리스크 방지).

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
        min_search_volume=min_search_volume,
        max_difficulty=max_difficulty,
        cluster_dedupe=cluster_dedupe,
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
    """단일 item dispatch — 사전 필터 → 클러스터 재사용 → operation 분기.

    이미 succeeded/failed/skipped 상태면 no-op (idempotent).
    retry 시도 시 retry_count +1, max_retries 초과 시 failed 확정.

    Phase 2 PR2 — `running` 마킹 직후:
      1. 사전 필터 (batch 의 임계값 설정 시) — 미달 시 즉시 skipped 종료
      2. 클러스터 재사용 (batch.cluster_dedupe AND member) — primary 의
         PatternCard 를 재사용해 분석 단계 압축
    """
    item = storage.get_item(item_id)
    if item is None:
        logger.warning("batch.dispatch.item_missing item_id=%s", item_id)
        return
    if item.status in ("succeeded", "failed", "skipped"):
        logger.info("batch.dispatch.skip_done item_id=%s status=%s", item_id, item.status)
        return

    batch = storage.get_batch(item.batch_id)
    if batch is None:
        logger.warning(
            "batch.dispatch.batch_missing item_id=%s batch_id=%s", item_id, item.batch_id
        )
        return

    job_id = f"batch-{item_id[:8]}-{uuid.uuid4().hex[:6]}"
    storage.update_item_status(
        item_id,
        "running",
        job_id=job_id,
        started_at=datetime.now(UTC),
    )

    # Phase 2 PR2 — 사전 필터 (임계값 설정된 batch 만).
    if _has_prefilter(batch) and not _apply_prefilter(item, batch):
        return  # _apply_prefilter 가 skipped 마킹 후 반환.

    # Phase 2 PR2 — cluster 재사용 (cluster_dedupe ON + member 만).
    primary = (
        _resolve_cluster_primary(item, batch)
        if (batch.cluster_dedupe and item.cluster_id and item.cluster_role == "member")
        else None
    )

    try:
        if primary is not None:
            _run_member_with_primary(item, primary)
        else:
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
    """operation 별 분기 — 단일 흐름 함수 호출 + Supabase id 회수.

    Phase B7 — 단일 흐름의 결과 모델에서 pattern_card_id / generated_content_id 를
    캡처해 storage.update_item_result() 로 keyword_batch_items FK 컬럼을 채움.
    회수 실패 (id None) 또는 update 실패 시에도 succeeded 마킹은 진행 (graceful).
    """
    pattern_card_id: str | None = None
    generated_content_id: str | None = None
    compliance_passed: bool | None = None

    if item.operation == "analyze":
        analyze_result: AnalyzeResult = orchestrator.run_analyze_only(item.keyword)
        if analyze_result.status == "failed":
            raise RuntimeError(analyze_result.error or "analyze 실패")
        pattern_card_id = analyze_result.pattern_card_id
    elif item.operation == "generate":
        result: GenerateResult = orchestrator.run_generate_only(keyword=item.keyword)
        if result.status == "failed":
            raise RuntimeError(result.error or "generate 실패")
        pattern_card_id = result.pattern_card_id
        generated_content_id = result.generated_content_id
        compliance_passed = result.compliance_passed
    elif item.operation == "pipeline":
        pipeline_result: PipelineResult = orchestrator.run_pipeline(item.keyword)
        if pipeline_result.status == "failed":
            raise RuntimeError(pipeline_result.error or "pipeline 실패")
        pattern_card_id = pipeline_result.pattern_card_id
        generated_content_id = pipeline_result.generated_content_id
    else:  # pragma: no cover — Pydantic Literal 로 미리 차단
        raise ValueError(f"알 수 없는 operation: {item.operation}")

    if item.id is not None:
        _record_item_result(
            item.id,
            pattern_card_id=pattern_card_id,
            generated_content_id=generated_content_id,
            compliance_passed=compliance_passed,
        )

    # job_id 는 logger 식별용 (current_job_id() 와는 별개 — single-flow 의 job_context 영향 X)
    logger.debug(
        "batch.operation_done item_id=%s job_id=%s operation=%s pc_id=%s gen_id=%s",
        item.id,
        job_id,
        item.operation,
        pattern_card_id,
        generated_content_id,
    )


def _record_item_result(
    item_id: str,
    *,
    pattern_card_id: str | None,
    generated_content_id: str | None,
    compliance_passed: bool | None,
) -> None:
    """결과 메타 graceful update. 모든 인자 None 이면 호출 자체 스킵.

    Supabase 미설정/실패 시 logger.warning + 무시 — succeeded 마킹은 차단되지 않음.
    """
    if pattern_card_id is None and generated_content_id is None and compliance_passed is None:
        return
    try:
        storage.update_item_result(
            item_id,
            pattern_card_id=pattern_card_id,
            generated_content_id=generated_content_id,
            compliance_passed=compliance_passed,
        )
    except Exception as exc:
        logger.warning(
            "batch.fk_link_failed item_id=%s err=%s",
            item_id,
            exc,
            exc_info=True,
        )


# ── Phase 2 PR2: 사전 필터 + 클러스터 재사용 ──


def _has_prefilter(batch: KeywordBatch) -> bool:
    """batch 에 사전 필터 임계값이 하나라도 설정되었으면 True."""
    return batch.min_search_volume is not None or batch.max_difficulty is not None


def _apply_prefilter(item: KeywordBatchItem, batch: KeywordBatch) -> bool:
    """사전 필터 — KeywordDifficulty 호출 후 임계값 검사.

    반환 True 면 통과 (caller 가 정상 흐름 계속), False 면 미달 (skipped 마킹 후
    caller 즉시 return). 사전 필터 자체가 raise 하면 graceful 통과 (warning 후 True).
    """
    if item.id is None:
        return True

    try:
        from application.keyword_difficulty_orchestrator import analyze_keyword

        diff = analyze_keyword(item.keyword, persist=False)
    except Exception:
        logger.warning(
            "batch.prefilter_failed item_id=%s keyword=%s — graceful pass",
            item.id,
            item.keyword,
            exc_info=True,
        )
        return True

    sv_total = diff.search_volume.monthly_total if diff.search_volume else None
    grade = diff.grade.value

    # 결과 메타는 통과·미달 무관하게 저장 (검수 큐 PR3 가 사용).
    _record_prefilter_meta(item.id, search_volume=sv_total, difficulty_grade=grade)

    reasons: list[str] = []
    if (
        batch.min_search_volume is not None
        and sv_total is not None
        and sv_total < batch.min_search_volume
    ):
        reasons.append(f"search_volume={sv_total}<{batch.min_search_volume}")
    if batch.max_difficulty is not None and _exceeds_difficulty(grade, batch.max_difficulty):
        reasons.append(f"difficulty={grade}>{batch.max_difficulty}")

    if not reasons:
        return True

    error_msg = "prefilter: " + ", ".join(reasons)
    storage.update_item_status(
        item.id,
        "skipped",
        error=error_msg,
        completed_at=datetime.now(UTC),
    )
    logger.info(
        "batch.prefilter_skipped item_id=%s keyword=%s reasons=%s",
        item.id,
        item.keyword,
        reasons,
    )
    return False


def _exceeds_difficulty(grade: str, max_grade: str) -> bool:
    """grade 가 max_grade 보다 어려우면 True.

    LOW(0) < MEDIUM(1) < HIGH(2) < MISSING(3). 알 수 없는 값은 통과 (graceful).
    """
    g = _DIFFICULTY_RANK.get(grade.lower())
    m = _DIFFICULTY_RANK.get(max_grade.lower())
    if g is None or m is None:
        return False
    return g > m


def _record_prefilter_meta(
    item_id: str, *, search_volume: int | None, difficulty_grade: str | None
) -> None:
    """사전 필터 결과 메타 graceful 저장. 모든 None 또는 raise 는 무시."""
    try:
        storage.update_item_result(
            item_id,
            search_volume=search_volume,
            difficulty_grade=difficulty_grade,
        )
    except Exception:
        logger.warning("batch.prefilter_meta_save_failed item_id=%s", item_id, exc_info=True)


def _resolve_cluster_primary(
    item: KeywordBatchItem, batch: KeywordBatch
) -> KeywordBatchItem | None:
    """cluster member 가 자기 cluster 의 primary 를 폴링하며 대기.

    반환:
        KeywordBatchItem: primary 가 succeeded + pattern_card_id 보유 → 재사용
        None: primary 부재 / 실패 / 타임아웃 → 자체 분석 폴백 (caller 가 _run_operation)
    """
    if item.cluster_id is None or item.batch_id is None:
        return None

    timeout = settings.batch_cluster_primary_timeout_sec
    interval = settings.batch_cluster_poll_interval_sec
    deadline = time.monotonic() + timeout

    while True:
        primary = storage.find_primary_in_cluster(item.batch_id, item.cluster_id)
        if primary is None:
            logger.warning(
                "batch.cluster.primary_missing item_id=%s cluster_id=%s — fallback",
                item.id,
                item.cluster_id,
            )
            return None
        if primary.status == "succeeded" and primary.pattern_card_id:
            return primary
        if primary.status in ("failed", "skipped"):
            logger.warning(
                "batch.cluster.primary_terminal item_id=%s primary=%s status=%s — fallback",
                item.id,
                primary.id,
                primary.status,
            )
            return None
        if time.monotonic() >= deadline:
            logger.warning(
                "batch.cluster.primary_timeout item_id=%s primary=%s status=%s — fallback",
                item.id,
                primary.id,
                primary.status,
            )
            return None
        time.sleep(interval)


def _run_member_with_primary(item: KeywordBatchItem, primary: KeywordBatchItem) -> None:
    """cluster member 의 operation 별 재사용 분기.

    analyze: 분석 단계 0회, primary.pattern_card_id 즉시 복사 → succeeded.
    generate / pipeline: primary 의 PatternCard disk path 주입해 [6]~[10] 만 실행.
    """
    if item.id is None or primary.pattern_card_id is None:
        # 가드 — _resolve_cluster_primary 가 통과시키지 않을 케이스지만 안전망.
        raise RuntimeError("cluster member dispatch precondition not met")

    if item.operation == "analyze":
        _record_item_result(
            item.id,
            pattern_card_id=primary.pattern_card_id,
            generated_content_id=None,
            compliance_passed=None,
        )
        logger.info(
            "batch.cluster.reuse_analyze item_id=%s primary=%s pc_id=%s",
            item.id,
            primary.id,
            primary.pattern_card_id,
        )
        return

    pc_path = _resolve_primary_card_path(primary)
    if pc_path is None:
        raise RuntimeError(
            f"cluster primary 의 PatternCard 파일 부재: primary={primary.id} pc_id={primary.pattern_card_id}"
        )

    if item.operation == "generate":
        result = orchestrator.run_generate_only(keyword=item.keyword, pattern_card_path=pc_path)
        if result.status == StageStatus.FAILED:
            raise RuntimeError(result.error or "generate 실패 (cluster 재사용)")
        _record_item_result(
            item.id,
            pattern_card_id=result.pattern_card_id or primary.pattern_card_id,
            generated_content_id=result.generated_content_id,
            compliance_passed=result.compliance_passed,
        )
    elif item.operation == "pipeline":
        result = orchestrator.run_pipeline(keyword=item.keyword, pattern_card_path=pc_path)
        if result.status == StageStatus.FAILED:
            raise RuntimeError(result.error or "pipeline 실패 (cluster 재사용)")
        _record_item_result(
            item.id,
            pattern_card_id=result.pattern_card_id or primary.pattern_card_id,
            generated_content_id=result.generated_content_id,
            compliance_passed=None,
        )
    else:  # pragma: no cover — Pydantic Literal 로 미리 차단
        raise ValueError(f"알 수 없는 operation: {item.operation}")


def _resolve_primary_card_path(primary: KeywordBatchItem) -> Path | None:
    """primary 의 pattern_card_id 로 디스크의 pattern-card.json 경로 조회.

    `pattern_cards` 테이블의 `output_path` 컬럼 + `analysis/pattern-card.json`.
    파일 미존재 시 fallback — `data` jsonb 를 임시 파일에 쓰기. 둘 다 실패 → None.
    """
    if primary.pattern_card_id is None:
        return None
    try:
        from config.supabase import get_client

        result = (
            get_client()
            .table("pattern_cards")
            .select("output_path, data")
            .eq("id", primary.pattern_card_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "batch.cluster.pc_lookup_failed pc_id=%s",
            primary.pattern_card_id,
            exc_info=True,
        )
        return None

    rows = result.data or []
    if not rows:
        return None
    row = rows[0]
    output_path = row.get("output_path")
    if output_path:
        candidate = Path(str(output_path)) / "analysis" / "pattern-card.json"
        if candidate.exists():
            return candidate
    # fallback — data jsonb 를 임시 파일로
    data = row.get("data")
    if not isinstance(data, dict):
        return None
    import json
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="cluster-pc-"))
    tmp_path = tmp_dir / "pattern-card.json"
    tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "batch.cluster.pc_fallback_to_tmp pc_id=%s path=%s", primary.pattern_card_id, tmp_path
    )
    return tmp_path


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
