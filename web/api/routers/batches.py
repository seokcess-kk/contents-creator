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
from domain.batch import storage
from domain.batch.model import NotSupportedYetError
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/batches",
    tags=["batches"],
    dependencies=[Depends(require_api_key)],
)


class BatchCreateJsonRequest(BaseModel):
    """JSON 본문으로 enqueue. CSV 텍스트를 직접 담아 전송."""

    csv_text: str = Field(min_length=1)
    mode: str = Field(default="now")
    name: str | None = None


@router.post("", status_code=202)
async def create_batch(request: Request) -> dict[str, Any]:
    """CSV 업로드 → 배치 enqueue. multipart 또는 JSON 둘 다 허용.

    Content-Type 으로 분기 — `multipart/form-data` 면 csv_file/mode/name form 필드,
    `application/json` 이면 BatchCreateJsonRequest 본문. Phase 1 은 mode='now' 만.
    """
    csv_text, mode, name = await _extract_csv_input(request)

    try:
        result = batch_orchestrator.enqueue_from_csv(
            csv_text,
            mode=mode,
            name=name,
        )
    except NotSupportedYetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


async def _extract_csv_input(request: Request) -> tuple[str, str, str | None]:
    """Content-Type 별로 csv_text/mode/name 추출. 잘못된 입력은 400."""
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
        return csv_text, str(form.get("mode") or "now"), _form_str(form.get("name"))

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"JSON 파싱 실패: {exc}") from exc
        try:
            parsed = BatchCreateJsonRequest(**body)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"본문 형식 오류: {exc}") from exc
        return parsed.csv_text, parsed.mode, parsed.name

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


@router.get("")
def list_batches(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    """배치 목록 — created_at desc."""
    batches = storage.list_batches(limit=limit)
    return {
        "count": len(batches),
        "items": [b.model_dump(mode="json") for b in batches],
    }


@router.get("/{batch_id}")
def get_batch(batch_id: str) -> dict[str, Any]:
    """단건 + 실시간 counters 재계산."""
    batch = storage.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch 미존재")
    counters = storage.count_items_by_status(batch_id)
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
    batch = storage.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch 미존재")
    items = storage.list_items(batch_id, status=status, limit=limit)
    return {
        "batch_id": batch_id,
        "count": len(items),
        "items": [it.model_dump(mode="json") for it in items],
    }


@router.post("/{batch_id}/cancel", status_code=200)
def cancel_batch(batch_id: str) -> dict[str, Any]:
    """진행 중 batch 의 queued items 를 모두 cancelled 로. running 은 그대로 진행."""
    try:
        cancelled = batch_orchestrator.cancel_batch(batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"batch_id": batch_id, "cancelled_count": cancelled}


@router.post("/{batch_id}/items/{item_id}/retry", status_code=202)
def retry_item(batch_id: str, item_id: str) -> dict[str, Any]:
    """단건 수동 재시도 — failed/succeeded/needs_review 만 가능."""
    try:
        batch_orchestrator.retry_item(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": batch_id, "item_id": item_id, "status": "queued"}


@router.post("/{batch_id}/recompute-status", status_code=200)
def recompute_status(batch_id: str) -> dict[str, Any]:
    """모든 item 처리 후 batch.status + counters 재계산 (운영 도구).

    주로 worker 가 종료 직전 race 로 batch.status 갱신을 못 한 경우 회복용.
    """
    batch = batch_orchestrator.recompute_batch_status(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch 미존재")
    return batch.model_dump(mode="json")
