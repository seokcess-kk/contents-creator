"""순위 추적 API. SPEC-RANKING.md §3 [조회] 참조.

엔드포인트:
- POST   /rankings/publications        — URL 등록
- GET    /rankings/publications        — 등록 목록 (keyword 필터, limit)
- GET    /rankings/publications/{id}   — 단건 + timeline
- PATCH  /rankings/publications/{id}   — keyword/URL/slug/published_at 부분 수정
- DELETE /rankings/publications/{id}   — 삭제 (snapshots 동반 cascade)
- GET    /rankings/publications/{id}/diagnoses  — 진단 시계열 조회
- POST   /rankings/publications/{id}/diagnose   — 진단 즉시 실행
- POST   /rankings/diagnoses/{id}/action        — 사용자 액션 기록
- GET    /rankings/calendar            — 월별 캘린더 매트릭스 (KST 기준)
- POST   /rankings/check/{publication_id}  — 즉시 SERP 체크
- GET    /rankings/{publication_id}    — RankingSnapshot 시계열
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

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
    url: str | None = None  # null = draft 생성, str = 정식 등록 (네이버 블로그)
    slug: str | None = Field(default=None, min_length=1)
    job_id: str | None = None
    published_at: datetime | None = None

    @field_validator("url")
    @classmethod
    def reject_empty_url(cls, v: str | None) -> str | None:
        """빈 문자열은 모호한 입력 — 400. draft 생성 시 명시적으로 null 사용."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("url 이 비어있습니다 (draft 생성은 null 사용)")
        return v


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


class DiagnosisActionRequest(BaseModel):
    user_action: str = Field(min_length=1, max_length=50)


@router.get("/publications/{publication_id}/diagnoses")
def list_diagnoses(
    publication_id: str, limit: int = Query(default=30, ge=1, le=200)
) -> dict[str, Any]:
    """publication 의 진단 시계열 (diagnosed_at desc)."""
    from domain.diagnosis import storage as diagnosis_storage

    items = diagnosis_storage.list_diagnoses_by_publication(publication_id, limit=limit)
    return {
        "publication_id": publication_id,
        "count": len(items),
        "items": [d.model_dump(mode="json") for d in items],
    }


@router.post("/publications/{publication_id}/diagnose")
def trigger_diagnose(publication_id: str) -> dict[str, Any]:
    """publication 진단 즉시 실행 (수동 트리거). 룰 평가 후 저장된 진단 반환."""
    from application.diagnosis_orchestrator import diagnose_publication

    diagnoses = diagnose_publication(publication_id)
    return {
        "publication_id": publication_id,
        "count": len(diagnoses),
        "items": [d.model_dump(mode="json") for d in diagnoses],
    }


@router.post("/diagnoses/{diagnosis_id}/action")
def record_diagnosis_action(diagnosis_id: str, req: DiagnosisActionRequest) -> dict[str, Any]:
    """사용자 액션 기록 (republished | held | dismissed | marked_competitor_strong)."""
    from datetime import UTC, datetime

    from domain.diagnosis import storage as diagnosis_storage

    updated = diagnosis_storage.update_user_action(
        diagnosis_id,
        user_action=req.user_action,
        user_action_at=datetime.now(tz=UTC).isoformat(),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="diagnosis 미존재")
    return updated.model_dump(mode="json")


@router.get("/calendar")
def get_calendar(
    month: str = Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM (KST 기준)"),
) -> dict[str, Any]:
    """월별 publication × 일자 캘린더 (KST). 같은 일 다회 측정은 마지막 측정 사용."""
    try:
        year_str, month_str = month.split("-")
        calendar = ranking_orchestrator.get_monthly_calendar(int(year_str), int(month_str))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return calendar.model_dump(mode="json")


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
