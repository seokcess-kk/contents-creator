"""Keyword Pipeline 통합 대시보드 API.

사용자 운영 철학 §9 의 첫 화면 — 모든 batch 합산해서 후보 키워드 단계별 가시화.
candidate → generated → needs_review / ready_to_publish → published → tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from application.orchestrator import _slugify
from config.settings import settings
from domain.batch import storage
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipeline",
    tags=["pipeline"],
    dependencies=[Depends(require_api_key)],
)


def _supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


@router.get("/summary")
def get_pipeline_summary(
    batch_limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """모든 최근 batch 합산 status 별 카운트.

    응답 키:
      - total / queued / running / needs_review / ready_to_publish / published
      - succeeded (analyze 만 끝난) / failed / skipped
    """
    if not _supabase_configured():
        return {"warning": "Supabase 미설정", "counts": {}}
    try:
        counts = storage.aggregate_pipeline_counts(batch_limit=batch_limit)
    except Exception as exc:
        logger.error("pipeline.summary.failed exc=%s", exc, exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"파이프라인 집계 실패: {type(exc).__name__}: {exc}"
        ) from exc
    return {"counts": counts, "batch_limit": batch_limit}


@router.get("/items")
def list_pipeline_items(
    status: str = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """status 별 item 목록 (모든 batch 통합, 최근순).

    Pipeline 페이지에서 단계별 keyword 목록 표시용. keyword_slug enrich 동일 패턴.
    """
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        items = storage.list_items_by_global_status(status, limit=limit)
    except Exception as exc:
        logger.error("pipeline.items.failed status=%s exc=%s", status, exc, exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"item 조회 실패: {type(exc).__name__}: {exc}"
        ) from exc
    return {
        "status": status,
        "count": len(items),
        "items": [_item_with_slug(it) for it in items],
    }


def _item_with_slug(item: Any) -> dict[str, Any]:
    """item 직렬화 + keyword_slug enrich (PR1 패턴 재사용)."""
    body = item.model_dump(mode="json")
    body["keyword_slug"] = _slugify(item.keyword)
    return body
