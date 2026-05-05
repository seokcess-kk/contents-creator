"""키워드 배치 운영 API. SPEC-BATCH.md §3 Phase 1.

엔드포인트:
- POST   /batches                          — CSV 또는 JSON 으로 배치 enqueue
- GET    /batches?limit=20                 — 배치 목록 (recent)
- GET    /batches/{id}                     — 단건 + 진행 요약
- GET    /batches/{id}/items?status=...    — item 페이지네이션
- POST   /batches/{id}/cancel              — 진행 중 batch 의 queued items 모두 cancelled
- POST   /batches/{id}/items/{item_id}/retry — 단건 재시도 (failed/succeeded/needs_review)
- POST   /batches/{id}/recompute-status    — counters + status 재계산 (운영 도구)

Phase 1 한정:
- mode 'overnight'/'auto' 는 400 Not Supported Yet (NotSupportedYetError → HTTPException)
- WebSocket 진행 보고는 Phase 2 검토 (지금은 GET polling 으로 충분)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from application import batch_orchestrator
from application.orchestrator import _slugify
from config.settings import settings
from domain.batch import storage
from domain.batch.model import NotSupportedYetError
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/batches",
    tags=["batches"],
    dependencies=[Depends(require_api_key)],
)


def _supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


def _supabase_error_response(exc: Exception, op: str) -> HTTPException:
    """Supabase 호출 실패 → 503 + 운영자 친화적 메시지.

    가장 흔한 원인: keyword_batches/keyword_batch_items 테이블 미생성.
    `config/schema.sql` 의 마이그레이션 SQL 을 Supabase SQL Editor 에 적용 필요.
    """
    msg = str(exc)
    is_missing_table = "relation" in msg.lower() and "does not exist" in msg.lower()
    detail = (
        "Supabase 의 keyword_batches / keyword_batch_items 테이블이 없습니다. "
        "config/schema.sql 의 마이그레이션 SQL 을 Supabase SQL Editor 에 적용하세요."
        if is_missing_table
        else f"Supabase 호출 실패 ({op}): {type(exc).__name__}: {msg}"
    )
    logger.error("batches.%s.failed exc=%s", op, msg, exc_info=True)
    return HTTPException(status_code=503, detail=detail)


class BatchCreateJsonRequest(BaseModel):
    """JSON 본문으로 enqueue. CSV 텍스트를 직접 담아 전송.

    Phase 2 PR2 추가:
        min_search_volume / max_difficulty: 사전 필터 임계값 (None 이면 필터 안 함).
        cluster_dedupe: cluster_id 의 primary→member PatternCard 재사용. **default False**
            — 본문 유사도로 인한 1페이지 노출 리스크 방지. 운영자가 의도적으로 켤 때만 ON.
    """

    csv_text: str = Field(min_length=1)
    mode: str = Field(default="now")
    name: str | None = None
    min_search_volume: int | None = None
    max_difficulty: str | None = None  # "LOW"/"MEDIUM"/"HIGH"/"MISSING"
    cluster_dedupe: bool = False
    # Phase 4 PR3 — opt-in publication 자동 등록. default False (운영 철학 §0).
    auto_publish_enabled: bool = False


@router.post("", status_code=202)
async def create_batch(request: Request) -> dict[str, Any]:
    """CSV 업로드 → 배치 enqueue. multipart 또는 JSON 둘 다 허용.

    Content-Type 으로 분기 — `multipart/form-data` 면 csv_file/mode/name form 필드,
    `application/json` 이면 BatchCreateJsonRequest 본문. Phase 1 은 mode='now' 만.
    """
    if not _supabase_configured():
        raise HTTPException(
            status_code=503, detail="Supabase 미설정 — SUPABASE_URL/SUPABASE_KEY 확인"
        )

    csv_text, opts = await _extract_csv_input(request)

    try:
        result = batch_orchestrator.enqueue_from_csv(
            csv_text,
            mode=opts["mode"],
            name=opts["name"],
            min_search_volume=opts["min_search_volume"],
            max_difficulty=opts["max_difficulty"],
            cluster_dedupe=opts["cluster_dedupe"],
            auto_publish_enabled=opts["auto_publish_enabled"],
        )
    except NotSupportedYetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _supabase_error_response(exc, "enqueue") from exc

    return result.model_dump(mode="json")


async def _extract_csv_input(request: Request) -> tuple[str, dict[str, Any]]:
    """Content-Type 별로 csv_text + 옵션 dict 추출. 잘못된 입력은 400.

    옵션 dict 키: mode, name, min_search_volume, max_difficulty, cluster_dedupe.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        csv_file = form.get("csv_file")
        if csv_file is None or not hasattr(csv_file, "read"):
            raise HTTPException(
                status_code=400, detail="multipart 요청에 csv_file 필드가 필요합니다."
            )
        csv_bytes = await csv_file.read()  # type: ignore[union-attr]
        csv_text = csv_bytes.decode("utf-8-sig")  # BOM 제거
        opts = {
            "mode": str(form.get("mode") or "now"),
            "name": _form_str(form.get("name")),
            "min_search_volume": _form_int(form.get("min_search_volume")),
            "max_difficulty": _form_str(form.get("max_difficulty")),
            "cluster_dedupe": _form_bool(form.get("cluster_dedupe")),
            "auto_publish_enabled": _form_bool(form.get("auto_publish_enabled")),
        }
        return csv_text, opts

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"JSON 파싱 실패: {exc}") from exc
        try:
            parsed = BatchCreateJsonRequest(**body)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"본문 형식 오류: {exc}") from exc
        opts = {
            "mode": parsed.mode,
            "name": parsed.name,
            "min_search_volume": parsed.min_search_volume,
            "max_difficulty": parsed.max_difficulty,
            "cluster_dedupe": parsed.cluster_dedupe,
            "auto_publish_enabled": parsed.auto_publish_enabled,
        }
        return parsed.csv_text, opts

    raise HTTPException(
        status_code=400,
        detail=(
            "Content-Type 은 'multipart/form-data' (CSV 파일 업로드) 또는 "
            "'application/json' (csv_text 본문) 이어야 합니다."
        ),
    )


def _form_str(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _form_int(value: object) -> int | None:
    """multipart form 의 빈 문자열·None 은 None, 정수 변환 실패도 None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _form_bool(value: object) -> bool:
    """multipart form 의 truthy 문자열을 bool 로. default False (PR2 보수적)."""
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "on")


@router.get("")
def list_batches(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    """배치 목록 — created_at desc.

    Supabase 미설정 또는 마이그레이션 미적용 시 빈 결과 + warning. 페이지 진입
    경험을 깨뜨리지 않도록 graceful 처리 (운영자는 detail 메시지로 인지).

    Phase B9 fix — `ready_to_publish_count` 가 DB 컬럼이 아닌 in-memory 집계라
    각 batch 마다 `count_items_by_status` 재집계해 응답 dict 에 merge. 목록
    UI 가 발행 준비 카운터를 정확히 표시. limit 20 기준 N+1 쿼리 비용 허용.
    """
    if not _supabase_configured():
        return {"count": 0, "items": [], "warning": "Supabase 미설정"}
    try:
        batches = storage.list_batches(limit=limit)
        items: list[dict[str, Any]] = []
        for b in batches:
            body = b.model_dump(mode="json")
            if b.id is not None:
                try:
                    body.update(storage.count_items_by_status(b.id))
                except Exception:
                    logger.warning(
                        "list_batches.counters_recompute_failed batch_id=%s",
                        b.id,
                        exc_info=True,
                    )
            items.append(body)
    except Exception as exc:
        raise _supabase_error_response(exc, "list_batches") from exc
    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{batch_id}")
def get_batch(batch_id: str) -> dict[str, Any]:
    """단건 + 실시간 counters 재계산."""
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        batch = storage.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch 미존재")
        counters = storage.count_items_by_status(batch_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise _supabase_error_response(exc, "get_batch") from exc
    body = batch.model_dump(mode="json")
    body.update(counters)
    return body


@router.get("/{batch_id}/items")
def list_batch_items(
    batch_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """item 페이지네이션. status 필터 선택."""
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        batch = storage.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch 미존재")
        items = storage.list_items(batch_id, status=status, limit=limit)
    except HTTPException:
        raise
    except Exception as exc:
        raise _supabase_error_response(exc, "list_items") from exc
    return {
        "batch_id": batch_id,
        "count": len(items),
        "items": [_item_with_slug(it) for it in items],
    }


def _item_with_slug(item: Any) -> dict[str, Any]:
    """item 직렬화 + keyword_slug enrich.

    Phase B7 — frontend BatchProgressTable 이 결과 페이지로 직링크 시 slug 가 필요.
    backend `_slugify` 단일 출처 사용 (NFC 정규화 + 한글 보존 regex 일관성 보장,
    frontend mirror 작성 시 한글 NFD 입력 등 미세 차이 발생 위험 회피).
    """
    body = item.model_dump(mode="json")
    body["keyword_slug"] = _slugify(item.keyword)
    return body


_REVIEW_TAB_FILTER: dict[str, dict[str, str | None]] = {
    "pending": {"review_status": "pending", "item_status": "needs_review"},
    "needs_fix": {"review_status": "needs_fix", "item_status": "needs_review"},
    "approved": {"review_status": "approved", "item_status": "ready_to_publish"},
    "rejected": {"review_status": "rejected", "item_status": "needs_review"},
}


@router.get("/{batch_id}/publish")
def list_publish_queue(batch_id: str) -> dict[str, Any]:
    """발행 준비 큐 — `status='ready_to_publish'` 만.

    Phase B9 fix #2 — 운영자가 ready_to_publish 항목을 별도 page 에서 일괄 확인 +
    URL 등록 다음 단계 동선 제공. /batches/[id]/publish 페이지의 데이터 소스.
    target_url 부재 / publication_id 부재 인 row 가 핵심 운영 대상.
    """
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        batch = storage.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch 미존재")
        items = storage.list_items(batch_id, status="ready_to_publish", limit=500)
    except HTTPException:
        raise
    except Exception as exc:
        raise _supabase_error_response(exc, "list_publish_queue") from exc
    return {
        "batch_id": batch_id,
        "count": len(items),
        "items": [_item_with_slug(it) for it in items],
    }


@router.get("/{batch_id}/review")
def list_review_queue(
    batch_id: str,
    tab: str = Query(default="pending"),
) -> dict[str, Any]:
    """검수 큐 — review_status 탭 별 조회 (Phase B9 fix #4).

    tab 파라미터:
      - pending (default): 검수 대기 (review_status=pending + status=needs_review)
      - needs_fix: 수정 필요 마킹됨
      - approved: 승인 완료 (status=ready_to_publish)
      - rejected: 거부 (예외)
    """
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    spec = _REVIEW_TAB_FILTER.get(tab)
    if spec is None:
        raise HTTPException(
            status_code=400,
            detail=f"invalid tab: {tab!r} (allowed: {', '.join(_REVIEW_TAB_FILTER)})",
        )
    try:
        batch = storage.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="batch 미존재")
        items = storage.list_review_pending_items(
            batch_id,
            review_status=spec["review_status"],
            item_status=spec["item_status"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _supabase_error_response(exc, "list_review_queue") from exc
    return {
        "batch_id": batch_id,
        "tab": tab,
        "count": len(items),
        "items": [_item_with_slug(it) for it in items],
    }


class ReviewActionRequest(BaseModel):
    """검수 액션 본문 — approve / needs_fix / reject."""

    action: str = Field(min_length=1)  # "approve" | "needs_fix" | "reject"
    reviewer: str | None = None


_REVIEW_ACTION_MAP: dict[str, dict[str, Any]] = {
    "approve": {"review_status": "approved", "status": "ready_to_publish"},
    "needs_fix": {"review_status": "needs_fix", "status": None},
    "reject": {"review_status": "rejected", "status": None},
    # Phase B9 fix — Undo: 검수 액션 후 5초 내 실행 취소. 검수 큐로 복귀.
    "revert": {"review_status": "pending", "status": "needs_review"},
}


@router.post("/{batch_id}/items/{item_id}/review", status_code=200)
def review_item(batch_id: str, item_id: str, body: ReviewActionRequest) -> dict[str, Any]:
    """검수 액션 — 운영자가 needs_review item 을 처리.

    Phase 2 PR3 — approve 시 status=ready_to_publish 로 동시 전환. needs_fix/reject 는
    review_status 만 갱신 (status 그대로 needs_review 유지).

    Phase B9 fix — batch_id 와 item.batch_id 소속 일치 검증 (다른 batch 의 item 변경 차단).
    """
    spec = _REVIEW_ACTION_MAP.get(body.action)
    if spec is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"invalid action: {body.action!r} (allowed: approve / needs_fix / reject / revert)"
            ),
        )
    try:
        item = storage.get_item(item_id)
    except Exception as exc:
        raise _supabase_error_response(exc, "review") from exc
    if item is None:
        raise HTTPException(status_code=404, detail=f"item 미존재: {item_id}")
    if item.batch_id != batch_id:
        raise HTTPException(
            status_code=404,
            detail=f"item {item_id} 가 batch {batch_id} 에 속하지 않습니다.",
        )
    try:
        storage.update_item_review(
            item_id,
            review_status=spec["review_status"],
            status=spec["status"],
            reviewer=body.reviewer,
        )
    except Exception as exc:
        raise _supabase_error_response(exc, "review") from exc
    return {
        "batch_id": batch_id,
        "item_id": item_id,
        "review_status": spec["review_status"],
        "status": spec["status"],
    }


@router.post("/{batch_id}/cancel", status_code=200)
def cancel_batch(batch_id: str) -> dict[str, Any]:
    """진행 중 batch 의 queued items 를 모두 cancelled 로. running 은 그대로 진행."""
    try:
        cancelled = batch_orchestrator.cancel_batch(batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _supabase_error_response(exc, "cancel") from exc
    return {"batch_id": batch_id, "cancelled_count": cancelled}


@router.post("/{batch_id}/items/{item_id}/retry", status_code=202)
def retry_item(batch_id: str, item_id: str) -> dict[str, Any]:
    """단건 수동 재시도 — failed/succeeded/needs_review/ready_to_publish 만 가능.

    Phase B9 fix — batch_id 와 item.batch_id 소속 일치 검증 (review API 와 동일 패턴).
    다른 batch 의 item 재시도 차단.
    """
    try:
        item = storage.get_item(item_id)
    except Exception as exc:
        raise _supabase_error_response(exc, "retry") from exc
    if item is None:
        raise HTTPException(status_code=404, detail=f"item 미존재: {item_id}")
    if item.batch_id != batch_id:
        raise HTTPException(
            status_code=404,
            detail=f"item {item_id} 가 batch {batch_id} 에 속하지 않습니다.",
        )
    try:
        batch_orchestrator.retry_item(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _supabase_error_response(exc, "retry") from exc
    return {"batch_id": batch_id, "item_id": item_id, "status": "queued"}


@router.post("/dispatch-overnight", status_code=200)
def dispatch_overnight(batch_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Phase 3 PR1 — 야간 cron / 운영자가 호출해 overnight batch 일괄 dispatch.

    batch_id 없으면 모든 mode='overnight' AND status='queued' batch 처리.
    batch_id 지정 시 그 batch 만 (운영자 명시 트리거).
    """
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        result = batch_orchestrator.dispatch_overnight_batches(batch_id=batch_id)
    except Exception as exc:
        raise _supabase_error_response(exc, "dispatch_overnight") from exc
    return result


@router.post("/{batch_id}/backfill-fk", status_code=200)
def backfill_fk(batch_id: str) -> dict[str, Any]:
    """SPEC-BATCH §3 Phase 2 PR4 — fire-and-forget FK 회수 실패 사후 백필.

    `(job_id, slug, keyword)` triple 매칭으로 pattern_card_id / generated_content_id
    None 인 item 들을 채움. idempotent. 동기 응답 (보통 5~50 item, 빠름).
    """
    try:
        result = batch_orchestrator.backfill_unlinked_items(batch_id)
    except Exception as exc:
        raise _supabase_error_response(exc, "backfill") from exc
    return {"batch_id": batch_id, **result}


@router.post("/{batch_id}/auto-publish", status_code=200)
def auto_publish(batch_id: str) -> dict[str, Any]:
    """SPEC-BATCH §3 Phase 4 PR2 — publication 자동 등록 (opt-in).

    `keyword_batches.auto_publish_enabled=True` 인 batch 의 ready_to_publish +
    target_url 채워진 item 을 publications 자동 등록 → /rankings 추적 진입.
    멱등 — 이미 publication_id 채워진 item 은 자동 skip.
    `auto_publish_enabled=False` 면 200 + skipped_reason='auto_publish_disabled'.
    """
    from application import auto_publisher

    try:
        result = auto_publisher.auto_publish_ready_items(batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _supabase_error_response(exc, "auto_publish") from exc
    return {"batch_id": batch_id, **result}


@router.post("/{batch_id}/recompute-status", status_code=200)
def recompute_status(batch_id: str) -> dict[str, Any]:
    """모든 item 처리 후 batch.status + counters 재계산 (운영 도구).

    주로 worker 가 종료 직전 race 로 batch.status 갱신을 못 한 경우 회복용.
    """
    try:
        batch = batch_orchestrator.recompute_batch_status(batch_id)
    except Exception as exc:
        raise _supabase_error_response(exc, "recompute") from exc
    if batch is None:
        raise HTTPException(status_code=404, detail="batch 미존재")
    return batch.model_dump(mode="json")
