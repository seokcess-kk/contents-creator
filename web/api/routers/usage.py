"""API 사용량 조회 엔드포인트."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from config.settings import settings
from web.api.auth import require_api_key

router = APIRouter(prefix="/usage", tags=["usage"], dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)

_FREE_PROVIDERS = {"naver_searchad"}
_KST = ZoneInfo("Asia/Seoul")
# Supabase PostgREST 단일 응답 한도. 더 큰 페이지는 서버에서 잘려 위험.
_PAGE_SIZE = 1000
# 30일 + 다양한 작업이라도 이를 초과하면 무한루프 방지 차원에서 종료.
_MAX_ROWS = 100_000


def _get_supabase():  # type: ignore[no-untyped-def]
    from config.supabase import get_client

    return get_client()


def _fetch_all_usage(client: Any, *, since: str, provider: str | None) -> list[dict[str, Any]]:
    """api_usage 페이지네이션 — 30일 분량 row 가 _PAGE_SIZE 를 넘으면 잘리는 사고
    (2026-05-03 dashboard 부분 표시) 방지. range() 로 모두 수확."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while offset < _MAX_ROWS:
        q = client.table("api_usage").select("*").gte("created_at", since)
        if provider:
            q = q.eq("provider", provider)
        page = (
            q.order("created_at", desc=True).range(offset, offset + _PAGE_SIZE - 1).execute().data
            or []
        )
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    if offset >= _MAX_ROWS:
        logger.warning("usage._fetch_all 최대치 도달 — 범위·필터 검토 필요")
    return rows


@router.get("")
def get_usage_summary(
    days: int = Query(default=30, ge=1, le=365),
    provider: str | None = Query(default=None),
) -> dict[str, Any]:
    """기간별 API 사용량 요약."""
    if not settings.supabase_url or not settings.supabase_key:
        return {"error": "Supabase 미설정", "items": [], "totals": {}}

    try:
        client = _get_supabase()
        since = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()
        rows = _fetch_all_usage(client, since=since, provider=provider)

        totals = _aggregate(rows)
        by_provider = _aggregate_by_provider(rows)
        by_day = _aggregate_by_day(rows)

        return {
            "days": days,
            "count": len(rows),
            "totals": totals,
            "by_provider": by_provider,
            "by_day": by_day,
            "recent_jobs": _recent_jobs(rows),
        }
    except Exception:
        logger.warning("usage 조회 실패", exc_info=True)
        return {"error": "조회 실패", "items": [], "totals": {}}


@router.get("/jobs/{job_id}")
def get_job_usage(job_id: str) -> dict[str, Any]:
    """특정 작업의 사용량."""
    if not settings.supabase_url or not settings.supabase_key:
        return {"error": "Supabase 미설정", "items": []}

    try:
        client = _get_supabase()
        result = (
            client.table("api_usage").select("*").eq("job_id", job_id).order("created_at").execute()
        )
        rows = result.data or []
        return {"job_id": job_id, "items": rows, "totals": _aggregate(rows)}
    except Exception:
        logger.warning("job usage 조회 실패", exc_info=True)
        return {"error": "조회 실패", "items": []}


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(r.get("input_tokens", 0) or 0 for r in rows)
    total_output = sum(r.get("output_tokens", 0) or 0 for r in rows)
    total_requests = sum(r.get("requests", 0) or 0 for r in rows)
    billable_requests = sum(
        r.get("requests", 0) or 0 for r in rows if _is_billable_provider(r.get("provider"))
    )
    free_requests = total_requests - billable_requests
    total_cost = sum(float(r.get("estimated_cost_usd", 0) or 0) for r in rows)
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "requests": total_requests,
        "billable_requests": billable_requests,
        "free_requests": free_requests,
        "estimated_cost_usd": round(total_cost, 4),
    }


def _is_billable_provider(provider: object) -> bool:
    if not isinstance(provider, str):
        return True
    return provider not in _FREE_PROVIDERS


def _aggregate_by_provider(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        p = r.get("provider", "unknown")
        if p not in by:
            by[p] = {
                "provider": p,
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0,
                "billable_requests": 0,
                "free_requests": 0,
                "billing_type": "billable" if _is_billable_provider(p) else "free",
                "cost": 0.0,
            }
        requests = r.get("requests", 0) or 0
        by[p]["input_tokens"] += r.get("input_tokens", 0) or 0
        by[p]["output_tokens"] += r.get("output_tokens", 0) or 0
        by[p]["requests"] += requests
        if _is_billable_provider(p):
            by[p]["billable_requests"] += requests
        else:
            by[p]["free_requests"] += requests
        by[p]["cost"] += float(r.get("estimated_cost_usd", 0) or 0)
    for v in by.values():
        v["cost"] = round(v["cost"], 4)
    return list(by.values())


def _kst_date(created_at: object) -> str:
    """ISO timestamptz 문자열 → KST(YYYY-MM-DD).

    Supabase 가 UTC 로 저장하므로 그대로 [:10] 자르면 한국 사용자 기준 자정~오전 9시
    호출이 전날로 집계되는 사고가 있었다(2026-05-03 dashboard 검토).
    """
    if not isinstance(created_at, str) or len(created_at) < 10:
        return ""
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return created_at[:10]  # 폴백: 파싱 불가 시 원문 prefix
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(_KST).strftime("%Y-%m-%d")


def _aggregate_by_day(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        day = _kst_date(r.get("created_at"))
        if not day:
            continue
        if day not in by:
            by[day] = {
                "date": day,
                "requests": 0,
                "billable_requests": 0,
                "free_requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }
        requests = r.get("requests", 0) or 0
        by[day]["requests"] += requests
        if _is_billable_provider(r.get("provider")):
            by[day]["billable_requests"] += requests
        else:
            by[day]["free_requests"] += requests
        by[day]["tokens"] += (r.get("input_tokens", 0) or 0) + (r.get("output_tokens", 0) or 0)
        by[day]["cost"] += float(r.get("estimated_cost_usd", 0) or 0)
    for v in by.values():
        v["cost"] = round(v["cost"], 4)
    return sorted(by.values(), key=lambda x: x["date"], reverse=True)


def _recent_jobs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """최근 작업별 비용."""
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        jid = r.get("job_id") or r.get("keyword") or "cli"
        if jid not in by:
            by[jid] = {
                "job_id": r.get("job_id"),
                "keyword": r.get("keyword", ""),
                "requests": 0,
                "billable_requests": 0,
                "free_requests": 0,
                "cost": 0.0,
                "last_at": r.get("created_at", ""),
            }
        requests = r.get("requests", 0) or 0
        by[jid]["requests"] += requests
        if _is_billable_provider(r.get("provider")):
            by[jid]["billable_requests"] += requests
        else:
            by[jid]["free_requests"] += requests
        by[jid]["cost"] += float(r.get("estimated_cost_usd", 0) or 0)
    for v in by.values():
        v["cost"] = round(v["cost"], 4)
    items = sorted(by.values(), key=lambda x: x["last_at"], reverse=True)
    return items[:20]
