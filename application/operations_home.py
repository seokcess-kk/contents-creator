"""운영 홈 use case — 요약 카드 + 탭 필터링.

`/rankings` 첫 화면이 "오늘 처리해야 할 작업 큐" 가 되도록 데이터 집계.
키워드 포트폴리오 운영 OS 의 메인 진입점.
"""

from __future__ import annotations

import logging
from typing import Any

from domain.diagnosis import storage as diagnosis_storage
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication, RankingSnapshot

logger = logging.getLogger(__name__)

# 사용자 가시 탭 → workflow_status 필터 매핑
TAB_FILTERS: dict[str, list[str]] = {
    "action_required": ["action_required"],
    "republishing": ["republishing"],
    "held": ["held"],
    "active": ["active"],  # 노출 중 (visibility_status 로 추가 분기)
    "dismissed": ["dismissed"],
    "all": [],  # 빈 리스트 = 필터 없음
}


def get_summary() -> dict[str, int]:
    """운영 홈 상단 요약 카드용 카운트.

    반환 키: action_required / republishing / held / exposed / dismissed / draft / total
    """
    counts = ranking_storage.count_publications_by_workflow_status()
    summary = {
        "action_required": counts.get("action_required", 0),
        "republishing": counts.get("republishing", 0),
        "held": counts.get("held", 0),
        "active": counts.get("active", 0),
        "dismissed": counts.get("dismissed", 0),
        "draft": counts.get("draft", 0),
    }
    summary["total"] = sum(summary.values())
    return summary


def list_publications_for_tab(
    tab: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """탭별 publication 목록 + 최신 snapshot + 최신 진단 enrichment.

    tab: action_required | republishing | held | active | dismissed | all
    """
    if tab not in TAB_FILTERS:
        raise ValueError(f"unknown tab: {tab!r}")
    statuses = TAB_FILTERS[tab]
    publications = ranking_storage.list_publications(
        limit=limit,
        workflow_status=statuses or None,
    )
    return [_enrich_publication(p) for p in publications]


def _enrich_publication(pub: Publication) -> dict[str, Any]:
    """publication 1건에 최신 snapshot + 최신 진단 메타 결합."""
    payload = pub.model_dump(mode="json")
    if pub.id is None:
        payload["latest_snapshot"] = None
        payload["latest_diagnosis"] = None
        return payload

    snapshots = ranking_storage.list_snapshots(pub.id, limit=1)
    payload["latest_snapshot"] = _snapshot_summary(snapshots[0]) if snapshots else None

    try:
        diagnoses = diagnosis_storage.list_diagnoses_by_publication(pub.id, limit=1)
        if diagnoses:
            d = diagnoses[0]
            payload["latest_diagnosis"] = {
                "id": d.id,
                "reason": d.reason,
                "confidence": float(d.confidence),
                "diagnosed_at": d.diagnosed_at.isoformat() if d.diagnosed_at else None,
                "recommended_action": d.recommended_action,
            }
        else:
            payload["latest_diagnosis"] = None
    except Exception:
        logger.warning("enrich.diagnosis_failed publication_id=%s", pub.id, exc_info=True)
        payload["latest_diagnosis"] = None

    return payload


def _snapshot_summary(s: RankingSnapshot) -> dict[str, Any]:
    return {
        "captured_at": s.captured_at.isoformat() if s.captured_at else None,
        "section": s.section,
        "position": s.position,
    }
