"""Performance Dashboard API.

사용자 운영 철학 §9 의 Performance Dashboard 데이터 — 발행된 publication 의
D+1/3/7/14/30 순위 궤적 + best/current + top10 유지 일수.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from application import performance_orchestrator
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/performance",
    tags=["performance"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/publications")
def list_performance(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """발행된 publication 의 D+N 순위 궤적 요약 목록."""
    try:
        items = performance_orchestrator.list_performance(limit=limit)
    except Exception as exc:
        logger.error("performance.list_failed exc=%s", exc, exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"performance 집계 실패: {type(exc).__name__}: {exc}"
        ) from exc
    return {"count": len(items), "items": items}


@router.get("/publications/{publication_id}/trajectory")
def get_trajectory(publication_id: str) -> dict[str, Any]:
    """단일 publication 의 D+N 순위 궤적 + 통계."""
    try:
        return performance_orchestrator.get_publication_trajectory(publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "performance.trajectory_failed pub_id=%s exc=%s",
            publication_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503, detail=f"trajectory 집계 실패: {type(exc).__name__}: {exc}"
        ) from exc
