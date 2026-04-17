"""API 사용량 조회 엔드포인트."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

from config.settings import settings

router = APIRouter(prefix="/usage", tags=["usage"])
logger = logging.getLogger(__name__)


def _get_supabase():  # type: ignore[no-untyped-def]
    from config.supabase import get_client

    return get_client()


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

        query = client.table("api_usage").select("*").gte("created_at", since)
        if provider:
            query = query.eq("provider", provider)
        query = query.order("created_at", desc=True).limit(500)

        result = query.execute()
        rows = result.data or []

        # 집계
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
            client.table("api_usage")
            .select("*")
            .eq("job_id", job_id)
            .order("created_at")
            .execute()
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
    total_cost = sum(float(r.get("estimated_cost_usd", 0) or 0) for r in rows)
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "requests": total_requests,
        "estimated_cost_usd": round(total_cost, 4),
    }


def _aggregate_by_provider(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        p = r.get("provider", "unknown")
        if p not in by:
            by[p] = {"provider": p, "input_tokens": 0, "output_tokens": 0, "requests": 0, "cost": 0.0}
        by[p]["input_tokens"] += r.get("input_tokens", 0) or 0
        by[p]["output_tokens"] += r.get("output_tokens", 0) or 0
        by[p]["requests"] += r.get("requests", 0) or 0
        by[p]["cost"] += float(r.get("estimated_cost_usd", 0) or 0)
    for v in by.values():
        v["cost"] = round(v["cost"], 4)
    return list(by.values())


def _aggregate_by_day(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        day = str(r.get("created_at", ""))[:10]
        if not day:
            continue
        if day not in by:
            by[day] = {"date": day, "requests": 0, "tokens": 0, "cost": 0.0}
        by[day]["requests"] += r.get("requests", 0) or 0
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
                "cost": 0.0,
                "last_at": r.get("created_at", ""),
            }
        by[jid]["requests"] += r.get("requests", 0) or 0
        by[jid]["cost"] += float(r.get("estimated_cost_usd", 0) or 0)
    for v in by.values():
        v["cost"] = round(v["cost"], 4)
    items = sorted(by.values(), key=lambda x: x["last_at"], reverse=True)
    return items[:20]
