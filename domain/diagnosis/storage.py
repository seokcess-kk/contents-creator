"""Diagnoses Supabase CRUD."""

from __future__ import annotations

import logging
from typing import Any, cast

from config.supabase import get_client
from domain.diagnosis.model import Diagnosis

logger = logging.getLogger(__name__)

_TABLE = "visibility_diagnoses"


def insert_diagnosis(diagnosis: Diagnosis) -> Diagnosis:
    """진단 결과 저장 (append-only). id·diagnosed_at 은 DB 가 채움."""
    client = get_client()
    payload = _to_payload(diagnosis)
    result = client.table(_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("diagnoses insert: no row returned")
    return _from_row(cast("dict[str, Any]", rows[0]))


def list_latest_diagnoses_batch(pub_ids: list[str]) -> dict[str, Diagnosis]:
    """publication 별 최신 진단 1건씩 일괄 조회 (RPC 사용).

    운영 홈 N+1 제거용. 빈 리스트면 즉시 빈 dict 반환.
    """
    if not pub_ids:
        return {}
    client = get_client()
    result = client.rpc("latest_visibility_diagnoses", {"pub_ids": pub_ids}).execute()
    out: dict[str, Diagnosis] = {}
    for row in result.data or []:
        d = _from_row(cast("dict[str, Any]", row))
        out[d.publication_id] = d
    return out


def list_diagnoses_by_publication(
    publication_id: str,
    limit: int = 30,
) -> list[Diagnosis]:
    """publication 의 진단 시계열 (diagnosed_at desc)."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("publication_id", publication_id)
        .order("diagnosed_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_from_row(cast("dict[str, Any]", r)) for r in (result.data or [])]


def update_user_action(
    diagnosis_id: str,
    user_action: str,
    user_action_at: str,
) -> Diagnosis | None:
    """사용자 액션 기록 (republished/held/dismissed/marked_competitor_strong)."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .update({"user_action": user_action, "user_action_at": user_action_at})
        .eq("id", diagnosis_id)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return _from_row(cast("dict[str, Any]", rows[0]))


def _to_payload(d: Diagnosis) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "publication_id": d.publication_id,
        "reason": d.reason,
        "confidence": d.confidence,
        "evidence": d.evidence,
        "metrics": d.metrics,
    }
    if d.recommended_action is not None:
        payload["recommended_action"] = d.recommended_action
    return payload


def _from_row(row: dict[str, Any]) -> Diagnosis:
    return Diagnosis(
        id=row.get("id"),
        publication_id=row["publication_id"],
        diagnosed_at=row.get("diagnosed_at"),
        reason=row["reason"],
        confidence=float(row["confidence"]),
        evidence=row.get("evidence") or [],
        metrics=row.get("metrics") or {},
        recommended_action=row.get("recommended_action"),
        outcome_checked_at=row.get("outcome_checked_at"),
        re_exposed=row.get("re_exposed") or False,
        re_exposed_at=row.get("re_exposed_at"),
        re_exposed_section=row.get("re_exposed_section"),
        re_exposed_position=row.get("re_exposed_position"),
        republished=row.get("republished") or False,
        republished_at=row.get("republished_at"),
        republish_publication_id=row.get("republish_publication_id"),
        user_action=row.get("user_action"),
        user_action_at=row.get("user_action_at"),
    )
