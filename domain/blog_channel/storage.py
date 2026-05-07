"""Supabase CRUD — blog_channels.

도메인 함수는 Pydantic 만 받고/반환한다 (raw dict 노출 금지). config/.env 가
없는 환경에서 get_client() 가 RuntimeError 를 raise 하므로 호출자가 best-effort
로 wrap 가능.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from config.supabase import get_client
from domain.blog_channel.model import BlogChannel, BlogChannelDuplicateError

logger = logging.getLogger(__name__)

_TABLE = "blog_channels"


def list_channels(limit: int = 100) -> list[BlogChannel]:
    """등록된 채널 전부 (최신순). is_default=true 가 첫 번째에 오도록 정렬."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .order("is_default", desc=True)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_channel(cast("dict[str, Any]", r)) for r in (result.data or [])]


def get_channel(channel_id: str) -> BlogChannel | None:
    client = get_client()
    result = client.table(_TABLE).select("*").eq("id", channel_id).limit(1).execute()
    rows = result.data or []
    return _row_to_channel(cast("dict[str, Any]", rows[0])) if rows else None


def find_channel_by_name(name: str) -> BlogChannel | None:
    """별칭 lookup — CSV 의 `blog` 컬럼이 별칭일 때 사용."""
    client = get_client()
    result = client.table(_TABLE).select("*").eq("name", name).limit(1).execute()
    rows = result.data or []
    return _row_to_channel(cast("dict[str, Any]", rows[0])) if rows else None


def find_channel_by_blog_id(blog_id: str) -> BlogChannel | None:
    """네이버 blog_id lookup — CSV 의 `blog` 컬럼이 ID 일 때 사용."""
    client = get_client()
    result = client.table(_TABLE).select("*").eq("blog_id", blog_id).limit(1).execute()
    rows = result.data or []
    return _row_to_channel(cast("dict[str, Any]", rows[0])) if rows else None


def get_default_channel() -> BlogChannel | None:
    """is_default=true 채널. 0 또는 1개. UI 셀렉트 default 용."""
    client = get_client()
    result = client.table(_TABLE).select("*").eq("is_default", True).limit(1).execute()
    rows = result.data or []
    return _row_to_channel(cast("dict[str, Any]", rows[0])) if rows else None


def create_channel(channel: BlogChannel) -> BlogChannel:
    """신규 채널 insert. name/blog_id 충돌 시 BlogChannelDuplicateError."""
    if channel.is_default:
        _clear_default_flag()
    client = get_client()
    payload = _channel_to_payload(channel)
    try:
        result = client.table(_TABLE).insert(payload).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise BlogChannelDuplicateError(channel.name) from exc
        raise
    rows = result.data or []
    if not rows:
        raise RuntimeError("blog_channels insert: no row returned")
    return _row_to_channel(cast("dict[str, Any]", rows[0]))


def update_channel(
    channel_id: str,
    *,
    name: str | None = None,
    blog_id: str | None = None,
    homepage_url: str | None = None,
    memo: str | None = None,
    is_default: bool | None = None,
) -> BlogChannel | None:
    """partial update. 명시적으로 전달된 키만 갱신. 미존재 시 None."""
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if blog_id is not None:
        payload["blog_id"] = blog_id
    if homepage_url is not None:
        payload["homepage_url"] = homepage_url
    if memo is not None:
        payload["memo"] = memo
    if is_default is True:
        _clear_default_flag(except_id=channel_id)
        payload["is_default"] = True
    elif is_default is False:
        payload["is_default"] = False
    if not payload:
        return get_channel(channel_id)
    payload["updated_at"] = datetime.now().isoformat()

    client = get_client()
    try:
        result = client.table(_TABLE).update(payload).eq("id", channel_id).execute()
    except Exception as exc:
        if _is_unique_violation(exc):
            raise BlogChannelDuplicateError(name or blog_id or "") from exc
        raise
    rows = result.data or []
    return _row_to_channel(cast("dict[str, Any]", rows[0])) if rows else None


def delete_channel(channel_id: str) -> bool:
    """채널 삭제. publications/keyword_batch_items 의 FK 는 ON DELETE SET NULL.

    삭제된 행이 1건 이상이면 True, 미존재면 False.
    """
    client = get_client()
    result = client.table(_TABLE).delete().eq("id", channel_id).execute()
    return bool(result.data)


# ── 내부 헬퍼 ────────────────────────────────────────────────


def _clear_default_flag(except_id: str | None = None) -> None:
    """is_default=true 인 기존 채널을 false 로 일괄 갱신 (정책: 1 default only)."""
    client = get_client()
    query = client.table(_TABLE).update({"is_default": False}).eq("is_default", True)
    if except_id is not None:
        query = query.neq("id", except_id)
    query.execute()


def _channel_to_payload(c: BlogChannel) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": c.name,
        "blog_id": c.blog_id,
        "homepage_url": c.homepage_url,
        "is_default": c.is_default,
    }
    if c.memo is not None:
        payload["memo"] = c.memo
    return payload


def _row_to_channel(row: dict[str, Any]) -> BlogChannel:
    return BlogChannel(
        id=row.get("id"),
        name=row["name"],
        blog_id=row["blog_id"],
        homepage_url=row["homepage_url"],
        memo=row.get("memo"),
        is_default=bool(row.get("is_default", False)),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _is_unique_violation(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "duplicate key" in text or "23505" in text or "unique" in text


__all__ = [
    "BlogChannelDuplicateError",
    "create_channel",
    "delete_channel",
    "find_channel_by_blog_id",
    "find_channel_by_name",
    "get_channel",
    "get_default_channel",
    "list_channels",
    "update_channel",
]
