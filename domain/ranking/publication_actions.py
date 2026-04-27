"""publication_actions 도메인 — 운영 액션 히스토리 (single source of truth).

visibility_diagnoses.user_action 은 단순 캐시. 본 모듈이 액션 발생의 정식
기록 위치이며, 캐시 갱신은 호출자(application) 가 best-effort 로 수행한다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from config.supabase import get_client

logger = logging.getLogger(__name__)

_TABLE = "publication_actions"

ActionType = Literal[
    "republished",
    "held",
    "released_hold",
    "dismissed",
    "restored",
    "url_registered",
    "auto_requeued",
]


class PublicationAction(BaseModel):
    """publication 운영 액션 1건. append-only 히스토리.

    auto_requeued 의 metadata.trigger:
      - republish_url_pending
      - republish_job_stuck
      - republish_job_failed
      - republish_job_missing
      - hold_expired
    """

    id: str | None = None
    publication_id: str
    diagnosis_id: str | None = None
    action: str
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


def insert_action(action: PublicationAction) -> PublicationAction:
    """액션 INSERT (히스토리 단일 출처). 실패 시 raise."""
    client = get_client()
    payload = _to_payload(action)
    result = client.table(_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("publication_actions insert: no row returned")
    return _from_row(cast("dict[str, Any]", rows[0]))


def list_actions_by_publication(
    publication_id: str,
    limit: int = 50,
) -> list[PublicationAction]:
    """publication 의 액션 시계열 (created_at desc)."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("publication_id", publication_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_from_row(cast("dict[str, Any]", r)) for r in (result.data or [])]


def _to_payload(a: PublicationAction) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "publication_id": a.publication_id,
        "action": a.action,
        "metadata": a.metadata,
    }
    if a.diagnosis_id is not None:
        payload["diagnosis_id"] = a.diagnosis_id
    if a.note is not None:
        payload["note"] = a.note
    return payload


def _from_row(row: dict[str, Any]) -> PublicationAction:
    return PublicationAction(
        id=row.get("id"),
        publication_id=row["publication_id"],
        diagnosis_id=row.get("diagnosis_id"),
        action=row["action"],
        note=row.get("note"),
        metadata=row.get("metadata") or {},
        created_at=row.get("created_at"),
    )
