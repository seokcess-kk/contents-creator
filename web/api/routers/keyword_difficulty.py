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
    # 통합검색 스마트블록 (UGC 블록) — 운영자 판단용 보조 지표 (점수 무영향)
    smartblock_present: bool = False
    smartblock_count: int = 0
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
        smartblock_present=diff.composition.smartblock.present,
        smartblock_count=diff.composition.smartblock.count,
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
    """최근 분석된 unique 키워드 limit 개 (키워드별 최신 1개).

    grade 지정 시 해당 등급으로 필터링. limit 는 키워드(=row) 기준이라
    snapshot 히스토리가 깊은 키워드도 1개씩만 반환된다.
    """
    if grade:
        try:
            grade_enum = DifficultyGrade(grade)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="grade 는 missing/high/medium/low 중 하나",
            ) from exc
        snapshots = storage.list_latest_per_keyword_by_grade(grade_enum, limit=limit)
    else:
        snapshots = storage.list_latest_per_keyword(limit=limit)
    return [_to_response(s) for s in snapshots]


@router.delete("")
def delete_by_keyword(keyword: str = Query(min_length=1, max_length=120)) -> dict[str, int]:
    """단일 키워드의 모든 스냅샷 삭제 — 히스토리 전체 제거."""
    deleted = storage.delete_by_keyword(keyword.strip())
    logger.info("keyword_difficulty.deleted keyword=%s rows=%d", keyword, deleted)
    return {"deleted": deleted}


@router.get("/diagnose")
def diagnose() -> dict[str, object]:
    """검색광고 API 환경 변수 + 라이브 호출 진단.

    민감 정보(키 전체)는 반환하지 않고 prefix 4자 + 길이 + 호출 결과만 반환.
    실제 호출도 1건 수행해 status code + 응답 본문 일부를 노출한다.
    """
    import time as _time

    import httpx as _httpx

    from config.settings import settings as _s
    from domain.keyword_difficulty.naver_ad_client import _sign

    api_key = _s.naver_ad_api_key or ""
    secret_key = _s.naver_ad_secret_key or ""
    customer_id = _s.naver_ad_customer_id or ""

    info: dict[str, object] = {
        "naver_ad_api_key_set": bool(api_key),
        "naver_ad_api_key_len": len(api_key),
        "naver_ad_api_key_head": api_key[:4] + "..." if api_key else None,
        # 끝 공백/개행 흔적 — 환경 변수 입력 실수 검출용
        "naver_ad_api_key_endswith_ws": bool(api_key) and api_key != api_key.strip(),
        "naver_ad_secret_key_set": bool(secret_key),
        "naver_ad_secret_key_len": len(secret_key),
        "naver_ad_secret_key_endswith_ws": bool(secret_key) and secret_key != secret_key.strip(),
        "naver_ad_customer_id": customer_id,
        "naver_ad_customer_id_endswith_ws": bool(customer_id)
        and customer_id != customer_id.strip(),
    }

    if not (api_key and secret_key and customer_id):
        info["live_call_error"] = "환경 변수 누락"
        return info

    # 직접 HTTP 호출하여 status + body 노출
    timestamp = str(int(_time.time() * 1000))
    signature = _sign(timestamp, "GET", "/keywordstool", secret_key.strip())
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key.strip(),
        "X-Customer": customer_id.strip(),
        "X-Signature": signature,
    }
    params = {"hintKeywords": "다이어트한의원", "showDetail": "1"}
    try:
        with _httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.searchad.naver.com/keywordstool",
                params=params,
                headers=headers,
            )
        info["live_status_code"] = resp.status_code
        info["live_body_head"] = resp.text[:500]
    except Exception as exc:
        info["live_call_error"] = f"{type(exc).__name__}: {exc}"

    return info
