"""publication 이벤트 통합 타임라인.

3종 소스(ranking_snapshots, visibility_diagnoses, publication_actions) 를
시간순으로 합쳐 단일 시계열로 노출한다. UI 의 통합 타임라인용.

DB UNION 대신 application 레이어 merge 를 채택 — 기존 list_* 함수 재사용,
도메인 격리 유지, 추가 SQL 마이그레이션 불필요.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from domain.diagnosis import storage as diag_storage
from domain.ranking import publication_actions
from domain.ranking import storage as ranking_storage

logger = logging.getLogger(__name__)

EventType = Literal["snapshot", "diagnosis", "action"]


class PublicationEvent(BaseModel):
    """publication 이벤트 1건. 3종 소스를 단일 모양으로 통합."""

    type: str = Field(description="EventType")
    occurred_at: datetime
    data: dict[str, Any] = Field(default_factory=dict)


def list_publication_events(
    publication_id: str,
    snapshot_limit: int = 90,
    diagnosis_limit: int = 30,
    action_limit: int = 50,
) -> list[PublicationEvent]:
    """3종 소스 fetch 후 occurred_at desc 로 merge."""
    events: list[PublicationEvent] = []
    events.extend(_fetch_snapshots(publication_id, snapshot_limit))
    events.extend(_fetch_diagnoses(publication_id, diagnosis_limit))
    events.extend(_fetch_actions(publication_id, action_limit))
    events.sort(key=lambda e: e.occurred_at, reverse=True)
    return events


def _fetch_snapshots(publication_id: str, limit: int) -> list[PublicationEvent]:
    out: list[PublicationEvent] = []
    for s in ranking_storage.list_snapshots(publication_id, limit=limit):
        if s.captured_at is None:
            continue
        out.append(
            PublicationEvent(
                type="snapshot",
                occurred_at=s.captured_at,
                data={
                    "position": s.position,
                    "section": s.section,
                    "total_results": s.total_results,
                },
            )
        )
    return out


def _fetch_diagnoses(publication_id: str, limit: int) -> list[PublicationEvent]:
    out: list[PublicationEvent] = []
    for d in diag_storage.list_diagnoses_by_publication(publication_id, limit=limit):
        if d.diagnosed_at is None:
            continue
        out.append(
            PublicationEvent(
                type="diagnosis",
                occurred_at=d.diagnosed_at,
                data={
                    "id": d.id,
                    "reason": d.reason,
                    "confidence": float(d.confidence),
                    "evidence": list(d.evidence),
                    "metrics": dict(d.metrics),
                    "recommended_action": d.recommended_action,
                    "user_action": d.user_action,
                },
            )
        )
    return out


def _fetch_actions(publication_id: str, limit: int) -> list[PublicationEvent]:
    out: list[PublicationEvent] = []
    for a in publication_actions.list_actions_by_publication(publication_id, limit=limit):
        if a.created_at is None:
            continue
        out.append(
            PublicationEvent(
                type="action",
                occurred_at=a.created_at,
                data={
                    "id": a.id,
                    "action": a.action,
                    "note": a.note,
                    "metadata": dict(a.metadata),
                    "diagnosis_id": a.diagnosis_id,
                },
            )
        )
    return out
