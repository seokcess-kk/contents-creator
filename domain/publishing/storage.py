"""publishing_attempts Supabase CRUD — 발행 시도 영속 로그.

성공·실패·dry_run 모두 1행씩 기록. 운영 분석 + 재시도 판단 + 사고 추적.
schema.sql 의 publishing_attempts 테이블 참조.

best-effort — Supabase 미설정/네트워크 실패 시 logger.warning 만 남기고 흡수.
publish 본 흐름이 publishing_attempts 영속 실패로 깨지면 안 된다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from config.supabase import get_client

from .model import PublishingAttempt

logger = logging.getLogger(__name__)

_TABLE = "publishing_attempts"


def insert_attempt(attempt: PublishingAttempt) -> str | None:
    """1행 insert. 반환은 생성된 id. Supabase 미가용 시 None + logger.warning."""
    try:
        client = get_client()
    except Exception as exc:
        logger.warning("publishing_attempts.no_supabase err=%s", exc)
        return None

    payload: dict[str, Any] = {
        "channel_id": attempt.channel_id,
        "keyword": attempt.keyword,
        "slug": attempt.slug,
        "job_id": attempt.job_id,
        "status": attempt.status,
        "post_url": attempt.post_url,
        "post_id": attempt.post_id,
        "message": attempt.message[:1000] if attempt.message else "",
        "response_excerpt": attempt.response_excerpt[:500] if attempt.response_excerpt else "",
        "attempted_at": (attempt.attempted_at or datetime.now()).isoformat(),
    }

    try:
        result = client.table(_TABLE).insert(payload).execute()
    except Exception as exc:
        logger.warning("publishing_attempts.insert_failed err=%s", exc)
        return None

    rows = result.data or []
    if not rows:
        return None
    return cast("dict[str, Any]", rows[0]).get("id")


def list_attempts_for_channel(channel_id: str, *, limit: int = 50) -> list[PublishingAttempt]:
    """채널별 최근 발행 시도. 운영자가 채널 상태 점검 시 사용."""
    try:
        client = get_client()
    except Exception:
        return []
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("channel_id", channel_id)
        .order("attempted_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_attempt(cast("dict[str, Any]", r)) for r in (result.data or [])]


def _row_to_attempt(row: dict[str, Any]) -> PublishingAttempt:
    return PublishingAttempt(
        id=row.get("id"),
        channel_id=row.get("channel_id"),
        keyword=row.get("keyword"),
        slug=row.get("slug"),
        job_id=row.get("job_id"),
        status=row.get("status", "failed"),
        post_url=row.get("post_url"),
        post_id=row.get("post_id"),
        message=row.get("message", ""),
        response_excerpt=row.get("response_excerpt", ""),
        attempted_at=row.get("attempted_at"),
    )


__all__ = ["insert_attempt", "list_attempts_for_channel"]
