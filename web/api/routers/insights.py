"""Insights API — 발행 데이터 기반 통계 분석 + 키워드 단위 행 뷰."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from application import insights_orchestrator, insights_view
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/insights",
    tags=["insights"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/summary")
def get_summary(
    publication_limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """난이도/검색량 × Top10 진입율 + D+N 진입 비율 등 통계."""
    try:
        return insights_orchestrator.get_insights_summary(publication_limit=publication_limit)
    except Exception as exc:
        logger.error("insights.summary.failed exc=%s", exc, exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"insights 집계 실패: {type(exc).__name__}: {exc}"
        ) from exc


@router.get("/keywords")
def get_keyword_insights(
    status: list[str] | None = Query(default=None),
    failure_category: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """키워드 1행 = 분석/발행/순위/진단 통합. /insights "키워드별" 탭이 사용.

    필터:
      - status: 여러 status OR 조건 (queued/running/succeeded/needs_review/failed/skipped/...)
      - failure_category: 단일 enum 값
      - batch_id: 특정 배치 한정
    """
    try:
        page_result = insights_view.list_keyword_insights(
            statuses=status,
            failure_category=failure_category,
            batch_id=batch_id,
            page=page,
            limit=limit,
        )
        return page_result.model_dump()
    except Exception as exc:
        logger.error("insights.keywords.failed exc=%s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"insights 키워드 행 뷰 실패: {type(exc).__name__}: {exc}",
        ) from exc
