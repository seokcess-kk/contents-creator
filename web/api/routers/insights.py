"""Insights API — 발행 데이터 기반 통계 분석."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from application import insights_orchestrator
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
