"""PatternCard 보관함 API. SPEC-BATCH §3 Phase 2 PR1.

`/batches/{id}` BatchProgressTable 의 succeeded row 직링크 + 분석 산출물 단독 조회용.
GeneratedContent 보관함 (`/api/results/*`) 과는 격리 — PatternCard 는 분석 결과
(distributions, sections, DIA+, target_reader) 만 노출하고 본문/이미지 트리는 다루지 않는다.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query

from config.settings import settings
from config.supabase import get_client
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pattern-cards",
    tags=["pattern-cards"],
    dependencies=[Depends(require_api_key)],
)

_TABLE = "pattern_cards"


def _supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


def _supabase_error_response(exc: Exception, op: str) -> HTTPException:
    """Supabase 호출 실패 → 503 + 운영자 친화적 메시지."""
    msg = str(exc)
    is_missing_table = "relation" in msg.lower() and "does not exist" in msg.lower()
    detail = (
        "Supabase 의 pattern_cards 테이블이 없습니다. "
        "config/schema.sql 의 마이그레이션 SQL 을 Supabase SQL Editor 에 적용하세요."
        if is_missing_table
        else f"Supabase 호출 실패 ({op}): {type(exc).__name__}: {msg}"
    )
    logger.error("pattern_cards.%s.failed exc=%s", op, msg, exc_info=True)
    return HTTPException(status_code=503, detail=detail)


def _row_to_summary(row: dict[str, Any]) -> dict[str, Any]:
    """summary 직렬화 — data jsonb 는 제외 (목록 응답 가벼움 우선)."""
    return {
        "id": row.get("id"),
        "keyword": row.get("keyword"),
        "slug": row.get("slug"),
        "analyzed_count": row.get("analyzed_count"),
        "created_at": row.get("created_at"),
    }


def _row_to_detail(row: dict[str, Any]) -> dict[str, Any]:
    """detail 직렬화 — data jsonb 전체 포함."""
    return {
        "id": row.get("id"),
        "keyword": row.get("keyword"),
        "slug": row.get("slug"),
        "analyzed_count": row.get("analyzed_count"),
        "created_at": row.get("created_at"),
        "output_path": row.get("output_path"),
        "data": row.get("data") or {},
    }


@router.get("/recent")
def list_recent_pattern_cards(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """pattern_cards 테이블 최근 N건. data jsonb 는 제외."""
    if not _supabase_configured():
        return {"count": 0, "items": [], "warning": "Supabase 미설정"}
    try:
        result = (
            get_client()
            .table(_TABLE)
            .select("id, keyword, slug, analyzed_count, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        raise _supabase_error_response(exc, "list_recent") from exc
    rows = result.data or []
    return {
        "count": len(rows),
        "items": [_row_to_summary(cast("dict[str, Any]", r)) for r in rows],
    }


@router.get("/by-id/{card_id}")
def get_pattern_card_by_id(card_id: str) -> dict[str, Any]:
    """id 정확 조회. data jsonb 전체 + 메타."""
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        result = get_client().table(_TABLE).select("*").eq("id", card_id).limit(1).execute()
    except Exception as exc:
        raise _supabase_error_response(exc, "get_by_id") from exc
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"pattern_card 미존재: {card_id}")
    return _row_to_detail(cast("dict[str, Any]", rows[0]))


@router.get("/by-slug/{slug}/latest")
def get_latest_pattern_card_by_slug(slug: str) -> dict[str, Any]:
    """slug 기준 최신 row 1건. slug 가 unique 가 아니라 created_at desc 로 첫 row."""
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        result = (
            get_client()
            .table(_TABLE)
            .select("*")
            .eq("slug", slug)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise _supabase_error_response(exc, "get_by_slug_latest") from exc
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"pattern_card 미존재: slug={slug}")
    return _row_to_detail(cast("dict[str, Any]", rows[0]))
