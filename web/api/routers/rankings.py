"""순위 추적 API. SPEC-RANKING.md §3 [조회] 참조.

엔드포인트:
- POST   /rankings/publications        — URL 등록
- GET    /rankings/publications        — 등록 목록 (keyword 필터, limit)
- GET    /rankings/publications/{id}   — 단건 + timeline
- PATCH  /rankings/publications/{id}   — keyword/URL/slug/published_at 부분 수정
- DELETE /rankings/publications/{id}   — 삭제 (snapshots 동반 cascade)
- POST   /rankings/check/{publication_id}  — 즉시 SERP 체크
- GET    /rankings/{publication_id}    — RankingSnapshot 시계열
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from application import ranking_orchestrator
from domain.ranking.model import RankingDuplicateUrlError, RankingMatchError
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rankings",
    tags=["rankings"],
    dependencies=[Depends(require_api_key)],
)


# ── Request/Response 스키마 ──


class PublicationCreateRequest(BaseModel):
    keyword: str = Field(min_length=1)
    url: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    job_id: str | None = None
    published_at: datetime | None = None


class PublicationUpdateRequest(BaseModel):
    """부분 수정. 전달된 필드만 적용."""

    keyword: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    published_at: datetime | None = None


# ── 엔드포인트 ──


@router.post("/publications")
def create_publication(req: PublicationCreateRequest) -> dict[str, Any]:
    """발행 URL 등록 (멱등). 동일 url 재호출은 기존 publication 반환."""
    try:
        publication = ranking_orchestrator.register_publication(
            keyword=req.keyword,
            slug=req.slug,
            url=req.url,
            job_id=req.job_id,
            published_at=req.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return publication.model_dump(mode="json")


@router.get("/publications")
def list_publications(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """등록 목록 조회. keyword 지정 시 필터."""
    from domain.ranking import storage

    publications = storage.list_publications(keyword=keyword, limit=limit)
    return {
        "count": len(publications),
        "items": [p.model_dump(mode="json") for p in publications],
    }


@router.get("/publications/{publication_id}")
def get_publication_with_timeline(publication_id: str) -> dict[str, Any]:
    """단건 publication + 최근 90개 snapshot timeline."""
    timeline = ranking_orchestrator.get_publication_timeline(publication_id, limit=90)
    if timeline is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return timeline.model_dump(mode="json")


@router.patch("/publications/{publication_id}")
def update_publication(publication_id: str, req: PublicationUpdateRequest) -> dict[str, Any]:
    """publication 부분 수정. 전달된 필드만 갱신."""
    try:
        updated = ranking_orchestrator.update_publication(
            publication_id,
            keyword=req.keyword,
            url=req.url,
            slug=req.slug,
            published_at=req.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RankingDuplicateUrlError as exc:
        raise HTTPException(status_code=409, detail=f"이미 등록된 URL 입니다: {exc}") from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return updated.model_dump(mode="json")


@router.delete("/publications/{publication_id}", status_code=204)
def delete_publication(publication_id: str) -> Response:
    """publication 삭제. snapshots 도 cascade 로 함께 삭제."""
    deleted = ranking_orchestrator.delete_publication(publication_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return Response(status_code=204)


@router.post("/check/{publication_id}")
def trigger_check(publication_id: str) -> dict[str, Any]:
    """단일 publication 즉시 SERP 체크 (수동 트리거)."""
    try:
        snapshot = ranking_orchestrator.check_rankings_for_publication(publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RankingMatchError as exc:
        raise HTTPException(status_code=502, detail=f"SERP 측정 실패: {exc}") from exc
    return snapshot.model_dump(mode="json")


@router.get("/{publication_id}")
def list_snapshots(
    publication_id: str,
    limit: int = Query(default=90, ge=1, le=365),
) -> dict[str, Any]:
    """publication 의 RankingSnapshot 시계열 (captured_at desc)."""
    from domain.ranking import storage

    publication = storage.get_publication(publication_id)
    if publication is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    snapshots = storage.list_snapshots(publication_id, limit=limit)
    return {
        "publication_id": publication_id,
        "count": len(snapshots),
        "items": [s.model_dump(mode="json") for s in snapshots],
    }
