"""Supabase CRUD — publications + ranking_snapshots.

도메인 함수는 Pydantic 모델만 받고/반환한다. raw dict 노출 금지.
config/.env 가 없는 환경에서는 get_client() 가 RuntimeError 를 raise 하므로
호출자(orchestrator)가 best-effort 패턴으로 wrap 할 수 있다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from config.supabase import get_client
from domain.ranking.model import (
    Publication,
    RankingDuplicateUrlError,
    RankingSnapshot,
    Top10Snapshot,
)

logger = logging.getLogger(__name__)

_PUB_TABLE = "publications"
_SNAP_TABLE = "ranking_snapshots"
_TOP10_TABLE = "serp_top10_snapshots"


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


def update_publication(
    publication_id: str,
    *,
    keyword: str | None = None,
    url: str | None = None,
    slug: str | None = None,
    published_at: datetime | None = None,
) -> Publication | None:
    """publications row partial update. 명시적으로 전달된 키만 갱신.

    URL 변경 시 UNIQUE(url) 충돌 가능 → RankingDuplicateUrlError.
    행 미존재 시 None.
    """
    payload: dict[str, Any] = {}
    if keyword is not None:
        payload["keyword"] = keyword
    if url is not None:
        payload["url"] = url
    if slug is not None:
        payload["slug"] = slug
    if published_at is not None:
        payload["published_at"] = published_at.isoformat()
    if not payload:
        # 변경 없음 — 기존 row 반환
        return get_publication(publication_id)

    client = get_client()
    try:
        result = client.table(_PUB_TABLE).update(payload).eq("id", publication_id).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise RankingDuplicateUrlError(url or "") from exc
        raise
    rows = result.data or []
    if not rows:
        return None
    return _row_to_publication(cast("dict[str, Any]", rows[0]))


def delete_publication(publication_id: str) -> bool:
    """publications row 삭제. ranking_snapshots 는 ON DELETE CASCADE 로 동반 삭제.

    삭제된 행이 1건 이상이면 True, 미존재면 False.
    """
    client = get_client()
    result = client.table(_PUB_TABLE).delete().eq("id", publication_id).execute()
    return bool(result.data)


def list_publications(
    keyword: str | None = None,
    limit: int = 50,
    workflow_status: list[str] | None = None,
) -> list[Publication]:
    """publications 목록. workflow_status 가 주어지면 IN 필터 적용."""
    client = get_client()
    query = client.table(_PUB_TABLE).select("*").order("created_at", desc=True).limit(limit)
    if keyword:
        query = query.eq("keyword", keyword)
    if workflow_status:
        query = query.in_("workflow_status", workflow_status)
    result = query.execute()
    return [_row_to_publication(cast("dict[str, Any]", r)) for r in (result.data or [])]


def count_publications_by_workflow_status() -> dict[str, int]:
    """workflow_status 별 publication 개수 — 운영 홈 요약 카드용."""
    client = get_client()
    result = client.table(_PUB_TABLE).select("workflow_status").execute()
    counts: dict[str, int] = {}
    for row in result.data or []:
        status = (cast("dict[str, Any]", row)).get("workflow_status") or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def update_publication_workflow_state(
    publication_id: str,
    *,
    workflow_status: str | None = None,
    visibility_status: str | None = None,
    held_until: datetime | None = None,
    held_reason: str | None = None,
    republishing_started_at: datetime | None = None,
    clear_held: bool = False,
) -> Publication | None:
    """workflow/visibility 전이 전용 업데이트.

    clear_held=True 면 held_until/held_reason 을 NULL 로 갱신 (보류 해제).
    """
    payload: dict[str, Any] = {}
    if workflow_status is not None:
        payload["workflow_status"] = workflow_status
    if visibility_status is not None:
        payload["visibility_status"] = visibility_status
    if held_until is not None:
        payload["held_until"] = held_until.isoformat()
    if held_reason is not None:
        payload["held_reason"] = held_reason
    if republishing_started_at is not None:
        payload["republishing_started_at"] = republishing_started_at.isoformat()
    if clear_held:
        payload["held_until"] = None
        payload["held_reason"] = None
    if not payload:
        return get_publication(publication_id)

    client = get_client()
    result = client.table(_PUB_TABLE).update(payload).eq("id", publication_id).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_publication(cast("dict[str, Any]", rows[0]))


def insert_top10_snapshots(items: list[Top10Snapshot]) -> int:
    """SERP Top10 일괄 insert. 빈 리스트면 0 반환."""
    if not items:
        return 0
    client = get_client()
    payloads = [_top10_to_payload(it) for it in items]
    result = client.table(_TOP10_TABLE).insert(payloads).execute()
    return len(result.data or [])


def list_top10_snapshots(
    keyword: str,
    limit: int = 30,
) -> list[Top10Snapshot]:
    """키워드의 최근 Top10 측정 시계열 (captured_at desc, rank asc)."""
    client = get_client()
    result = (
        client.table(_TOP10_TABLE)
        .select("*")
        .eq("keyword", keyword)
        .order("captured_at", desc=True)
        .order("rank", desc=False)
        .limit(limit)
        .execute()
    )
    return [_row_to_top10(cast("dict[str, Any]", r)) for r in (result.data or [])]


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


def list_latest_snapshots_batch(pub_ids: list[str]) -> dict[str, RankingSnapshot]:
    """publication 별 최신 snapshot 1건씩 일괄 조회 (RPC 사용).

    운영 홈 N+1 제거용. 100 pubs 도 단일 쿼리.
    빈 리스트면 즉시 빈 dict 반환.
    """
    if not pub_ids:
        return {}
    client = get_client()
    result = client.rpc("latest_ranking_snapshots", {"pub_ids": pub_ids}).execute()
    out: dict[str, RankingSnapshot] = {}
    for row in result.data or []:
        snap = _row_to_snapshot(cast("dict[str, Any]", row))
        out[snap.publication_id] = snap
    return out


def list_snapshots_in_range(
    start_utc: datetime,
    end_utc: datetime,
    limit: int = 10_000,
) -> list[RankingSnapshot]:
    """captured_at 이 [start_utc, end_utc) 인 모든 snapshot.

    캘린더 뷰 집계용. publication_id 무관하게 한 번에 가져온 뒤 application
    레이어에서 group-by 한다 (월 단위라 row 수가 한정적, 1만 건 안전 상한).
    """
    client = get_client()
    result = (
        client.table(_SNAP_TABLE)
        .select("*")
        .gte("captured_at", start_utc.isoformat())
        .lt("captured_at", end_utc.isoformat())
        .order("captured_at", desc=False)
        .limit(limit)
        .execute()
    )
    return [_row_to_snapshot(cast("dict[str, Any]", r)) for r in (result.data or [])]


def _publication_to_payload(p: Publication) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "keyword": p.keyword,
        "url": p.url,  # nullable — draft 시 None
        "visibility_status": p.visibility_status,
        "workflow_status": p.workflow_status,
    }
    if p.slug is not None:
        payload["slug"] = p.slug
    if p.job_id is not None:
        payload["job_id"] = p.job_id
    if p.published_at is not None:
        payload["published_at"] = p.published_at.isoformat()
    if p.held_until is not None:
        payload["held_until"] = p.held_until.isoformat()
    if p.held_reason is not None:
        payload["held_reason"] = p.held_reason
    if p.parent_publication_id is not None:
        payload["parent_publication_id"] = p.parent_publication_id
    if p.priority_score is not None:
        payload["priority_score"] = p.priority_score
    if p.republishing_started_at is not None:
        payload["republishing_started_at"] = p.republishing_started_at.isoformat()
    return payload


def _snapshot_to_payload(s: RankingSnapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {"publication_id": s.publication_id}
    if s.section is not None:
        payload["section"] = s.section
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
        slug=row.get("slug"),
        url=row.get("url"),  # nullable
        published_at=row.get("published_at"),
        created_at=row.get("created_at"),
        visibility_status=row.get("visibility_status") or "not_measured",
        workflow_status=row.get("workflow_status") or "active",
        held_until=row.get("held_until"),
        held_reason=row.get("held_reason"),
        parent_publication_id=row.get("parent_publication_id"),
        priority_score=row.get("priority_score"),
        republishing_started_at=row.get("republishing_started_at"),
    )


def _row_to_snapshot(row: dict[str, Any]) -> RankingSnapshot:
    return RankingSnapshot(
        id=row.get("id"),
        publication_id=row["publication_id"],
        section=row.get("section"),
        position=row.get("position"),
        total_results=row.get("total_results"),
        captured_at=row.get("captured_at"),
        serp_html_path=row.get("serp_html_path"),
    )


def _top10_to_payload(t: Top10Snapshot) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "keyword": t.keyword,
        "rank": t.rank,
        "url": t.url,
        "is_ours": t.is_ours,
    }
    if t.section is not None:
        payload["section"] = t.section
    if t.blog_id is not None:
        payload["blog_id"] = t.blog_id
    return payload


def _row_to_top10(row: dict[str, Any]) -> Top10Snapshot:
    return Top10Snapshot(
        id=row.get("id"),
        keyword=row["keyword"],
        captured_at=row.get("captured_at"),
        rank=row["rank"],
        url=row["url"],
        section=row.get("section"),
        blog_id=row.get("blog_id"),
        is_ours=row.get("is_ours") or False,
    )


def _is_unique_violation(exc: BaseException) -> bool:
    """Supabase/PostgREST 의 unique 위반 여부 판정 (best-effort)."""
    text = str(exc).lower()
    return "duplicate key" in text or "23505" in text or "unique" in text
