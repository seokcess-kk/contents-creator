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

from application import batch_job_manager, notifier, orchestrator
from application.job_context import current_job_id
from application.models import AnalyzeResult, GenerateResult, PipelineResult, StageStatus
from config.settings import settings
from domain.batch import csv_parser, storage
from domain.batch.model import (
    BatchEnqueueResult,
    ItemStatus,
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

# Phase B9 fix — cluster primary 재사용 가능 status. PR3 의 ready_to_publish 도입 후
# generate/pipeline primary 가 succeeded 가 아닌 ready_to_publish 로 끝나는 케이스 보강.
# needs_review 도 PatternCard 자체는 만들어졌으니 재사용 OK (member 의 의료법 검수도 같은
# PatternCard 기반이라 일관됨).
_PRIMARY_REUSE_STATUSES = frozenset({"succeeded", "ready_to_publish", "needs_review"})

# Phase B9 fix — _dispatch_item terminal no-op set. 이미 종결된 status 는 재진입 시 중복
# 실행 방지. needs_review 는 retry_item() 명시 호출로만 queued 복귀 (직접 dispatch 차단).
_TERMINAL_STATUSES = frozenset(
    {"succeeded", "failed", "skipped", "ready_to_publish", "needs_review"}
)


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

    auto_dispatch=True 면 즉시 worker pool 에 dispatch (mode='now' 만 즉시 처리).

    Phase 2 PR2 추가:
        min_search_volume / max_difficulty: 사전 필터 임계값. None 이면 필터 안 함.
        cluster_dedupe: 같은 cluster_id 의 primary→member PatternCard 재사용 활성.
            **default False** (본문 유사도로 인한 1페이지 노출 리스크 방지).

    Phase 3 결정 (2026-05-05) — mode 의미 재정의:
        - mode='now': 즉시 dispatch (auto_dispatch=True 시 즉시 worker submit)
        - mode='overnight': DB 저장만, dispatch 보류. **Anthropic Batch API 아님**.
          운영자/cron 이 `dispatch_overnight_batches()` 호출 시 일괄 처리.
        - mode='auto': priority 라우팅. priority<=3 인 item 만 즉시 submit, priority>=4 는
          overnight 큐에 보류. dispatch_overnight 시 함께 처리됨.

    Anthropic Batch API adapter 는 운영 데이터 누적 후 별도 PR (Phase 5+).

    Raises:
        NotSupportedYetError: mode 가 알려지지 않은 값.
        ValueError: CSV 형식 오류 (헤더 누락 등) — API 가 400 으로 변환.
    """
    if mode not in ("now", "overnight", "auto"):
        raise NotSupportedYetError(
            f"지원되지 않는 mode: {mode!r} (allowed: now / overnight / auto)"
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

    # Phase 3 (2026-05-05) — mode 별 dispatch 정책:
    #   now: 모든 item 즉시 submit
    #   overnight: 즉시 submit 안 함 (운영자 시간대에 일괄 처리)
    #   auto: priority<=3 만 즉시 submit, 나머지는 overnight 큐에 보류
    if auto_dispatch and inserted_items and mode != "overnight":
        manager = batch_job_manager.get_default_manager()
        for it in inserted_items:
            if it.id is None:
                continue
            if mode == "auto" and it.priority >= 4:
                continue  # overnight 보류 — dispatch_overnight_batches() 가 처리
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
    if item.status in _TERMINAL_STATUSES:
        # ready_to_publish / needs_review 도 종결 상태 — 재진입 시 중복 실행 방지.
        # needs_review 는 retry_item() 명시 호출로만 queued 복귀 (운영 의도 분리).
        logger.info("batch.dispatch.skip_done item_id=%s status=%s", item_id, item.status)
        return

    batch = storage.get_batch(item.batch_id)
    if batch is None:
        logger.warning(
            "batch.dispatch.batch_missing item_id=%s batch_id=%s", item_id, item.batch_id
        )
        return

    # Phase 3 PR2 — atomic claim. 멀티 워커 (web process + 외부 cron) 진입 시
    # 동일 item 의 동시 dispatch 방지. claim 실패 = 이미 다른 worker 가 처리 중.
    job_id = f"batch-{item_id[:8]}-{uuid.uuid4().hex[:6]}"
    claimed = storage.claim_item_for_dispatch(item_id, job_id=job_id)
    if claimed is None:
        logger.info(
            "batch.dispatch.claim_failed item_id=%s — already taken by another worker", item_id
        )
        return
    item = claimed

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
        compliance_passed, compliance_violations = (
            _run_member_with_primary(item, primary)
            if primary is not None
            else _run_operation(item, job_id)
        )
    except Exception as exc:
        _handle_item_failure(item, exc)
        return

    # Phase B9 — operation 별 final status 분기 (사용자 운영 철학 반영).
    # analyze 는 발행할 본문 없음 → succeeded 유지.
    # generate/pipeline: compliance_passed=True → ready_to_publish, False/None → needs_review.
    new_status: ItemStatus
    if item.operation == "analyze":
        new_status = "succeeded"
    elif compliance_passed is True:
        new_status = "ready_to_publish"
    else:
        # False (의료법 위반 잔존) / None (결과 모델 누락 / 중간 실패) 둘 다 검수 필요.
        # 데이터 누락 방지 — 발행 준비 큐에서 빠지지 않도록 needs_review 안전망.
        new_status = "needs_review"
    storage.update_item_status(
        item_id,
        new_status,
        completed_at=datetime.now(UTC),
    )
    logger.info(
        "batch.item_done item_id=%s keyword=%s operation=%s status=%s cp=%s",
        item_id,
        item.keyword,
        item.operation,
        new_status,
        compliance_passed,
    )

    # Phase 4 PR1 — 의료법 위반 단건 알림 (generate/pipeline + compliance_passed=False).
    # webhook 미설정 또는 toggle off 면 notifier 가 자체 noop. 알림 실패도 본 흐름 영향 X.
    if compliance_passed is False and item.operation in ("generate", "pipeline"):
        try:
            notifier.send_compliance_violation(item, compliance_violations)
        except Exception:
            logger.warning(
                "batch.notify.compliance_violation_failed item_id=%s", item_id, exc_info=True
            )


def _run_operation(item: KeywordBatchItem, job_id: str) -> tuple[bool | None, list[str]]:
    """operation 별 분기 — 단일 흐름 함수 호출 + Supabase id 회수.

    Phase B7 — 단일 흐름의 결과 모델에서 pattern_card_id / generated_content_id 를
    캡처해 storage.update_item_result() 로 keyword_batch_items FK 컬럼을 채움.
    회수 실패 (id None) 또는 update 실패 시에도 succeeded 마킹은 진행 (graceful).

    Phase B9 — caller (`_dispatch_item`) 가 final status 분기를 결정할 수 있도록
    `compliance_passed: bool | None` 반환 (analyze 는 None, generate/pipeline 는 결과 모델의 값).

    Phase 4 PR1 — 의료법 위반 알림에 카테고리 노출을 위해 `compliance_violations`
    도 함께 반환. analyze 는 빈 리스트.
    """
    pattern_card_id: str | None = None
    generated_content_id: str | None = None
    compliance_passed: bool | None = None
    compliance_violations: list[str] = []

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
        compliance_violations = result.compliance_violations
    elif item.operation == "pipeline":
        pipeline_result: PipelineResult = orchestrator.run_pipeline(item.keyword)
        if pipeline_result.status == "failed":
            raise RuntimeError(pipeline_result.error or "pipeline 실패")
        pattern_card_id = pipeline_result.pattern_card_id
        generated_content_id = pipeline_result.generated_content_id
        compliance_passed = pipeline_result.compliance_passed
        compliance_violations = pipeline_result.compliance_violations
    else:  # pragma: no cover — Pydantic Literal 로 미리 차단
        raise ValueError(f"알 수 없는 operation: {item.operation}")

    if item.id is not None:
        _record_item_result(
            item.id,
            pattern_card_id=pattern_card_id,
            generated_content_id=generated_content_id,
            compliance_passed=compliance_passed,
            compliance_violations=compliance_violations,
        )

    # job_id 는 logger 식별용 (current_job_id() 와는 별개 — single-flow 의 job_context 영향 X)
    logger.debug(
        "batch.operation_done item_id=%s job_id=%s operation=%s pc_id=%s gen_id=%s cp=%s",
        item.id,
        job_id,
        item.operation,
        pattern_card_id,
        generated_content_id,
        compliance_passed,
    )
    return compliance_passed, compliance_violations


def _record_item_result(
    item_id: str,
    *,
    pattern_card_id: str | None,
    generated_content_id: str | None,
    compliance_passed: bool | None,
    compliance_violations: list[str] | None = None,
) -> None:
    """결과 메타 graceful update. 모든 인자 None 이면 호출 자체 스킵.

    Supabase 미설정/실패 시 logger.warning + 무시 — succeeded 마킹은 차단되지 않음.
    """
    if (
        pattern_card_id is None
        and generated_content_id is None
        and compliance_passed is None
        and not compliance_violations
    ):
        return
    try:
        storage.update_item_result(
            item_id,
            pattern_card_id=pattern_card_id,
            generated_content_id=generated_content_id,
            compliance_passed=compliance_passed,
            compliance_violations=compliance_violations,
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
        KeywordBatchItem: primary 가 PatternCard 보유 + 재사용 가능 status (succeeded /
            ready_to_publish / needs_review) → 재사용. 의료법 위반(needs_review) 이라도
            PatternCard 자체는 만들어졌으므로 member 분석 단계 압축에 활용 가능.
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
        if primary.status in _PRIMARY_REUSE_STATUSES and primary.pattern_card_id:
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


def _run_member_with_primary(
    item: KeywordBatchItem, primary: KeywordBatchItem
) -> tuple[bool | None, list[str]]:
    """cluster member 의 operation 별 재사용 분기.

    analyze: 분석 단계 0회, primary.pattern_card_id 즉시 복사 → caller 가 succeeded 마킹.
    generate / pipeline: primary 의 PatternCard disk path 주입해 [6]~[10] 만 실행.

    Phase B9 — caller (`_dispatch_item`) 가 final status 분기를 결정하도록
    `compliance_passed: bool | None` 반환 (analyze 는 None, generate/pipeline 는 결과 모델의 값).

    Phase 4 PR1 — 의료법 위반 알림 카테고리 노출을 위해 `compliance_violations` 도
    함께 반환.
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
        return None, []

    pc_path = _resolve_primary_card_path(primary)
    if pc_path is None:
        raise RuntimeError(
            f"cluster primary 의 PatternCard 파일 부재: primary={primary.id} pc_id={primary.pattern_card_id}"
        )

    if item.operation == "generate":
        gen_result: GenerateResult = orchestrator.run_generate_only(
            keyword=item.keyword, pattern_card_path=pc_path
        )
        if gen_result.status == StageStatus.FAILED:
            raise RuntimeError(gen_result.error or "generate 실패 (cluster 재사용)")
        _record_item_result(
            item.id,
            pattern_card_id=gen_result.pattern_card_id or primary.pattern_card_id,
            generated_content_id=gen_result.generated_content_id,
            compliance_passed=gen_result.compliance_passed,
            compliance_violations=gen_result.compliance_violations,
        )
        return gen_result.compliance_passed, gen_result.compliance_violations
    if item.operation == "pipeline":
        pipe_result: PipelineResult = orchestrator.run_pipeline(
            keyword=item.keyword, pattern_card_path=pc_path
        )
        if pipe_result.status == StageStatus.FAILED:
            raise RuntimeError(pipe_result.error or "pipeline 실패 (cluster 재사용)")
        _record_item_result(
            item.id,
            pattern_card_id=pipe_result.pattern_card_id or primary.pattern_card_id,
            generated_content_id=pipe_result.generated_content_id,
            compliance_passed=pipe_result.compliance_passed,
            compliance_violations=pipe_result.compliance_violations,
        )
        return pipe_result.compliance_passed, pipe_result.compliance_violations
    # pragma: no cover — Pydantic Literal 로 미리 차단
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
    if item.status not in ("failed", "succeeded", "needs_review", "ready_to_publish"):
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


def dispatch_overnight_batches(*, batch_id: str | None = None) -> dict[str, int]:
    """Phase 3 PR1 — 야간 cron / 운영자 트리거로 overnight batch 일괄 dispatch.

    `batch_id` None: 모든 mode='overnight' AND status='queued' batch 처리.
    `batch_id` 지정: 그 batch 만 처리 (운영자가 명시 트리거 시).

    각 batch 의 status='queued' item 만 worker pool 에 submit. 이미 진행 중/종결된
    item 은 skip. 반환: {dispatched_batches, dispatched_items, skipped_batches}.
    """
    overnight_batches = _list_overnight_queued_batches(batch_id=batch_id)
    if not overnight_batches:
        return {"dispatched_batches": 0, "dispatched_items": 0, "skipped_batches": 0}

    manager = batch_job_manager.get_default_manager()
    dispatched_batches = 0
    dispatched_items = 0
    skipped_batches = 0

    for b in overnight_batches:
        if b.id is None:
            skipped_batches += 1
            continue
        # 해당 batch 의 queued item 만 일괄 submit. running/succeeded/failed 등은 idempotent skip.
        try:
            queued_items = storage.list_items(b.id, status="queued", limit=10_000)
        except Exception:
            logger.warning("dispatch_overnight.list_items_failed batch_id=%s", b.id, exc_info=True)
            skipped_batches += 1
            continue
        if not queued_items:
            skipped_batches += 1
            continue
        try:
            storage.update_batch_status(
                b.id,
                "running",
                started_at=datetime.now(UTC),
            )
        except Exception:
            logger.warning(
                "dispatch_overnight.batch_status_update_failed batch_id=%s",
                b.id,
                exc_info=True,
            )
        for it in queued_items:
            if it.id is not None:
                manager.submit(_dispatch_item_safely, it.id)
                dispatched_items += 1
        dispatched_batches += 1

    logger.info(
        "dispatch_overnight.done dispatched_batches=%d dispatched_items=%d skipped=%d",
        dispatched_batches,
        dispatched_items,
        skipped_batches,
    )
    # Phase 4 PR1 — 야간 dispatch 시작 알림 (dispatched_items==0 이면 notifier 가 noop).
    try:
        notifier.send_overnight_dispatched(dispatched_batches, dispatched_items)
    except Exception:
        logger.warning("batch.notify.overnight_dispatched_failed", exc_info=True)
    return {
        "dispatched_batches": dispatched_batches,
        "dispatched_items": dispatched_items,
        "skipped_batches": skipped_batches,
    }


_DISPATCH_OVERNIGHT_MODES = frozenset({"overnight", "auto"})


def _list_overnight_queued_batches(*, batch_id: str | None = None) -> list[KeywordBatch]:
    """overnight 또는 auto + queued/running batch 목록. batch_id 지정 시 단건만.

    Phase 3 결정 (2026-05-05) — mode=auto 도 함께 처리. auto 의 priority>=4 인 item 이
    enqueue 시 보류된 상태로 status=queued 로 남아 있음. dispatch_overnight 트리거 시
    같이 처리. batch.status 는 queued/running 둘 다 (auto 의 priority<=3 이 즉시 실행되며
    batch 가 running 으로 전이된 경우 포함).
    """
    if batch_id is not None:
        b = storage.get_batch(batch_id)
        if b is None or b.mode not in _DISPATCH_OVERNIGHT_MODES:
            return []
        if b.status not in ("queued", "running"):
            return []
        return [b]
    # 전체 — list_batches 후 필터.
    all_batches = storage.list_batches(limit=200)
    return [
        b
        for b in all_batches
        if b.mode in _DISPATCH_OVERNIGHT_MODES and b.status in ("queued", "running")
    ]


def backfill_unlinked_items(batch_id: str) -> dict[str, int]:
    """SPEC-BATCH §3 Phase 2 PR4 — fire-and-forget 회수 실패 사후 백필.

    batch 의 모든 item 중 pattern_card_id / generated_content_id 가 None 인 item 을
    `(job_id, slug, keyword)` triple 로 사후 매칭해 채운다. idempotent — 이미 채워진
    FK 는 skip. 매칭 실패는 still_unlinked 에 카운트.

    반환: `{matched_pattern_cards, matched_generated_contents, still_unlinked}`.
    운영자가 명시적 호출 (CLI / Web API). 자동 cron 미사용.
    """
    from application.orchestrator import _slugify

    items = storage.list_items(batch_id, limit=10_000)
    matched_pc = 0
    matched_gen = 0
    still_unlinked = 0

    for item in items:
        if item.id is None:
            continue
        needs_pc = item.pattern_card_id is None
        needs_gen = item.operation in ("generate", "pipeline") and item.generated_content_id is None
        if not needs_pc and not needs_gen:
            continue  # idempotent — 이미 채워진 item

        slug = _slugify(item.keyword)
        new_pc_id: str | None = None
        new_gen_id: str | None = None

        if needs_pc:
            new_pc_id = storage.find_pattern_card_by_triple(slug, item.keyword)
            if new_pc_id is not None:
                matched_pc += 1

        if needs_gen:
            new_gen_id = storage.find_generated_content_by_triple(item.job_id, slug, item.keyword)
            if new_gen_id is not None:
                matched_gen += 1

        if new_pc_id is None and new_gen_id is None:
            # 한쪽도 매칭 못 함 — DB update 호출 자체 스킵.
            still_unlinked += 1
            logger.warning(
                "batch.backfill.unmatched item_id=%s keyword=%s slug=%s",
                item.id,
                item.keyword,
                slug,
            )
            continue

        update_failed = False
        try:
            storage.update_item_result(
                item.id,
                pattern_card_id=new_pc_id,
                generated_content_id=new_gen_id,
            )
        except Exception:
            logger.warning("batch.backfill.update_failed item_id=%s", item.id, exc_info=True)
            update_failed = True

        # Phase B9 fix — 백필 시도 후 최종 FK 누락 여부로 still_unlinked 판정.
        # update 실패 시 최종 상태는 백필 전과 동일. 부분 매칭 (한쪽만 채움) 도 카운트.
        final_pc_missing = needs_pc and (update_failed or new_pc_id is None)
        final_gen_missing = needs_gen and (update_failed or new_gen_id is None)
        if final_pc_missing or final_gen_missing:
            still_unlinked += 1

    logger.info(
        "batch.backfill.done batch_id=%s matched_pc=%d matched_gen=%d still_unlinked=%d",
        batch_id,
        matched_pc,
        matched_gen,
        still_unlinked,
    )
    return {
        "matched_pattern_cards": matched_pc,
        "matched_generated_contents": matched_gen,
        "still_unlinked": still_unlinked,
    }


def recompute_batch_status(batch_id: str) -> KeywordBatch | None:
    """모든 item 처리 후 batch status + counters 재계산.

    호출 시점: 마지막 item dispatch 완료 후. Phase 1 은 worker 가 자체적으로
    호출 안 하고 (race 회피), 외부 polling 또는 cron 으로 트리거.

    Phase 4 PR1 — status 가 'queued/running' → 'completed' 로 전이될 때 한 번만
    Slack 알림. 이미 'completed' 상태에서 재호출되면 알림 중복 방지를 위해 noop.
    failed_count == total_count 면 배치 전체 실패로 간주해 즉시 알림.
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
    previously_completed = batch.status == "completed"
    storage.update_batch_status(
        batch_id,
        new_status,  # type: ignore[arg-type]
        counters=counters,
        completed_at=datetime.now(UTC) if new_status == "completed" else None,
    )
    refreshed = storage.get_batch(batch_id)

    # Phase 4 PR1 — completed 첫 진입 시 1회 알림.
    if refreshed is not None and new_status == "completed" and not previously_completed:
        try:
            failed_total = counters.get("failed_count", 0)
            if failed_total >= batch.total_count and batch.total_count > 0:
                notifier.send_batch_failed(
                    refreshed,
                    f"all {failed_total} items failed",
                )
            else:
                notifier.send_batch_completed(refreshed, counters)
        except Exception:
            logger.warning("batch.notify.completed_failed batch_id=%s", batch_id, exc_info=True)

    # Phase 4 PR2 — completed 첫 진입 + auto_publish_enabled=True 시 자동 발행 등록.
    # 멱등 — 이미 publication_id 채워진 item 은 auto_publisher 가 자체 skip.
    # 실패해도 batch status 자체는 영향 없음 (graceful).
    if (
        refreshed is not None
        and new_status == "completed"
        and not previously_completed
        and refreshed.auto_publish_enabled
    ):
        try:
            from application import auto_publisher

            auto_publisher.auto_publish_ready_items(batch_id)
        except Exception:
            logger.warning(
                "batch.auto_publish.failed batch_id=%s — graceful", batch_id, exc_info=True
            )

    return refreshed


__all__ = [
    "enqueue_from_csv",
    "retry_item",
    "cancel_batch",
    "recompute_batch_status",
    "_dispatch_item_safely",  # tests
]


# unused import 회피 (job_context 는 향후 single-flow 와의 통합점)
_ = current_job_id
