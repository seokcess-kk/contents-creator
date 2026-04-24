"""Supabase CRUD — publications + ranking_snapshots.

도메인 함수는 Pydantic 모델만 받고/반환한다. raw dict 노출 금지.
config/.env 가 없는 환경에서는 get_client() 가 RuntimeError 를 raise 하므로
호출자(orchestrator)가 best-effort 패턴으로 wrap 할 수 있다.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from config.supabase import get_client
from domain.ranking.model import (
    Publication,
    RankingDuplicateUrlError,
    RankingSnapshot,
)

logger = logging.getLogger(__name__)

_PUB_TABLE = "publications"
_SNAP_TABLE = "ranking_snapshots"


def insert_publication(publication: Publication) -> Publication:
    """publications row insert. UNIQUE(url) 충돌 시 RankingDuplicateUrlError.

    멱등 변환은 application 레이어가 책임 (충돌 시 get_publication_by_url 호출).
    """
    client = get_client()
    payload = _publication_to_payload(publication)
    try:
        result = client.table(_PUB_TABLE).insert(payload).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise RankingDuplicateUrlError(publication.url) from exc
        raise
    rows = result.data or []
    if not rows:
        raise RuntimeError("publications insert: no row returned")
    return _row_to_publication(cast("dict[str, Any]", rows[0]))


def get_publication(publication_id: str) -> Publication | None:
    client = get_client()
    result = client.table(_PUB_TABLE).select("*").eq("id", publication_id).limit(1).execute()
    rows = result.data or []
    return _row_to_publication(cast("dict[str, Any]", rows[0])) if rows else None


def get_publication_by_url(url: str) -> Publication | None:
    client = get_client()
    result = client.table(_PUB_TABLE).select("*").eq("url", url).limit(1).execute()
    rows = result.data or []
    return _row_to_publication(cast("dict[str, Any]", rows[0])) if rows else None


def list_publications(
    keyword: str | None = None,
    limit: int = 50,
) -> list[Publication]:
    client = get_client()
    query = client.table(_PUB_TABLE).select("*").order("created_at", desc=True).limit(limit)
    if keyword:
        query = query.eq("keyword", keyword)
    result = query.execute()
    return [_row_to_publication(cast("dict[str, Any]", r)) for r in (result.data or [])]


def insert_snapshot(snapshot: RankingSnapshot) -> RankingSnapshot:
    """ranking_snapshots row insert (append-only)."""
    client = get_client()
    payload = _snapshot_to_payload(snapshot)
    result = client.table(_SNAP_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("ranking_snapshots insert: no row returned")
    return _row_to_snapshot(cast("dict[str, Any]", rows[0]))


def list_snapshots(publication_id: str, limit: int = 90) -> list[RankingSnapshot]:
    """publication_id 의 snapshot 시계열 (captured_at desc)."""
    client = get_client()
    result = (
        client.table(_SNAP_TABLE)
        .select("*")
        .eq("publication_id", publication_id)
        .order("captured_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_snapshot(cast("dict[str, Any]", r)) for r in (result.data or [])]


def _publication_to_payload(p: Publication) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "keyword": p.keyword,
        "slug": p.slug,
        "url": p.url,
    }
    if p.job_id is not None:
        payload["job_id"] = p.job_id
    if p.published_at is not None:
        payload["published_at"] = p.published_at.isoformat()
    return payload


def _snapshot_to_payload(s: RankingSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {"publication_id": s.publication_id}
    if s.position is not None:
        payload["position"] = s.position
    if s.total_results is not None:
        payload["total_results"] = s.total_results
    if s.serp_html_path is not None:
        payload["serp_html_path"] = s.serp_html_path
    return payload


def _row_to_publication(row: dict[str, Any]) -> Publication:
    return Publication(
        id=row.get("id"),
        job_id=row.get("job_id"),
        keyword=row["keyword"],
        slug=row["slug"],
        url=row["url"],
        published_at=row.get("published_at"),
        created_at=row.get("created_at"),
    )


def _row_to_snapshot(row: dict[str, Any]) -> RankingSnapshot:
    return RankingSnapshot(
        id=row.get("id"),
        publication_id=row["publication_id"],
        position=row.get("position"),
        total_results=row.get("total_results"),
        captured_at=row.get("captured_at"),
        serp_html_path=row.get("serp_html_path"),
    )


def _is_unique_violation(exc: BaseException) -> bool:
    """Supabase/PostgREST 의 unique 위반 여부 판정 (best-effort)."""
    text = str(exc).lower()
    return "duplicate key" in text or "23505" in text or "unique" in text
