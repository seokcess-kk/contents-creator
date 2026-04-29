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
    # 2026-04-29 F1: 상한 5 → 10. 기본 8 (orchestrator 와 동일).
    parallel: int = Field(default=8, ge=1, le=10)


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


@router.get("/diagnose")
def diagnose() -> dict[str, object]:
    """검색광고 API 환경 변수 + 라이브 호출 진단.

    민감 정보(키 전체)는 반환하지 않고 prefix 4자 + 길이 + 호출 결과만 반환.
    실제 호출도 1건 수행해 응답 코드를 확인한다.
    """
    from config.settings import settings as _s
    from domain.keyword_difficulty.naver_ad_client import get_search_volume

    info: dict[str, object] = {
        "naver_ad_api_key_set": bool(_s.naver_ad_api_key),
        "naver_ad_api_key_len": len(_s.naver_ad_api_key) if _s.naver_ad_api_key else 0,
        "naver_ad_api_key_head": (_s.naver_ad_api_key[:4] + "...") if _s.naver_ad_api_key else None,
        "naver_ad_secret_key_set": bool(_s.naver_ad_secret_key),
        "naver_ad_secret_key_len": len(_s.naver_ad_secret_key) if _s.naver_ad_secret_key else 0,
        "naver_ad_customer_id": _s.naver_ad_customer_id,
    }
    try:
        result = get_search_volume("다이어트한의원")
        info["live_call_result"] = (
            {
                "monthly_pc": result.monthly_pc,
                "monthly_mobile": result.monthly_mobile,
                "competition_idx": result.competition_idx,
            }
            if result is not None
            else None
        )
    except Exception as exc:
        info["live_call_error"] = f"{type(exc).__name__}: {exc}"
    return info
