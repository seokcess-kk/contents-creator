"""키워드 노출 난이도 분석 API. tasks/todo.md Phase K5 참조.

엔드포인트:
- POST /keyword-difficulty/analyze        — 단일 키워드 분석
- POST /keyword-difficulty/batch          — 다수 키워드 일괄 분석 (max 50)
- GET  /keyword-difficulty/snapshots      — 단일 키워드 히스토리
- GET  /keyword-difficulty/list           — 등급/최근순 목록
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application import keyword_difficulty_orchestrator
from domain.keyword_difficulty import storage
from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SerpFetchError,
)
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/keyword-difficulty",
    tags=["keyword_difficulty"],
    dependencies=[Depends(require_api_key)],
)

_BATCH_MAX = 50


class _AnalyzeRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)


class _BatchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=_BATCH_MAX)
    parallel: int = Field(default=3, ge=1, le=5)


class _DifficultyResponse(BaseModel):
    keyword: str
    grade: str
    score: float
    total_cards: int
    blog_slots: int
    spam_cards: int
    sections: dict[str, int]
    monthly_pc_search: int | None = None
    monthly_mobile_search: int | None = None
    monthly_total_search: int | None = None
    competition_idx: str | None = None
    sov_grade: str = "unknown"
    checked_at: datetime | None


def _to_response(diff: KeywordDifficulty) -> _DifficultyResponse:
    sv = diff.search_volume
    return _DifficultyResponse(
        keyword=diff.keyword,
        grade=diff.grade.value,
        score=diff.score,
        total_cards=diff.composition.total_cards,
        blog_slots=diff.composition.blog_slots,
        spam_cards=diff.composition.spam_cards,
        sections={s.value: c for s, c in diff.composition.section_counts.items()},
        monthly_pc_search=sv.monthly_pc if sv else None,
        monthly_mobile_search=sv.monthly_mobile if sv else None,
        monthly_total_search=sv.monthly_total if sv else None,
        competition_idx=sv.competition_idx if sv else None,
        sov_grade=diff.sov_grade.value,
        checked_at=diff.checked_at,
    )


@router.post("/analyze", response_model=_DifficultyResponse)
def analyze(req: _AnalyzeRequest) -> _DifficultyResponse:
    """단일 키워드 즉시 분석. Bright Data 호출 1회 + Supabase 저장."""
    try:
        diff = keyword_difficulty_orchestrator.analyze_keyword(req.keyword.strip())
    except SerpFetchError as exc:
        raise HTTPException(status_code=502, detail=f"SERP fetch 실패: {exc}") from exc
    return _to_response(diff)


@router.post("/batch", response_model=list[_DifficultyResponse])
def batch_analyze(req: _BatchRequest) -> list[_DifficultyResponse]:
    """다수 키워드 일괄 분석. 최대 50개. 일부 실패는 결과에서 제외."""
    cleaned = [k.strip() for k in req.keywords if k.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="keywords 가 비어 있음")
    if len(cleaned) > _BATCH_MAX:
        raise HTTPException(status_code=400, detail=f"최대 {_BATCH_MAX}개")

    results = keyword_difficulty_orchestrator.batch_analyze_keywords(cleaned, parallel=req.parallel)
    return [_to_response(r) for r in results]


@router.get("/snapshots", response_model=list[_DifficultyResponse])
def list_snapshots(
    keyword: str = Query(min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[_DifficultyResponse]:
    """단일 키워드의 분석 히스토리 (최근순)."""
    history = storage.list_keyword_history(keyword.strip(), limit=limit)
    return [_to_response(h) for h in history]


@router.get("/list", response_model=list[_DifficultyResponse])
def list_recent(
    grade: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[_DifficultyResponse]:
    """등록된 분석 스냅샷 최근순. grade 지정 시 해당 등급만."""
    if grade:
        try:
            grade_enum = DifficultyGrade(grade)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="grade 는 missing/high/medium/low 중 하나",
            ) from exc
        snapshots = storage.list_by_grade(grade_enum, limit=limit)
    else:
        snapshots = storage.list_recent(limit=limit)
    return [_to_response(s) for s in snapshots]
