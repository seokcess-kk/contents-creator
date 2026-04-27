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

    🔴 N+1 제거: storage RPC 로 publication 별 최신 1건씩 일괄 조회 → 2 쿼리만 사용.
    100 pubs 도 단일 라운드트립.

    tab: action_required | republishing | held | active | dismissed | all
    """
    if tab not in TAB_FILTERS:
        raise ValueError(f"unknown tab: {tab!r}")
    statuses = TAB_FILTERS[tab]
    publications = ranking_storage.list_publications(
        limit=limit,
        workflow_status=statuses or None,
    )

    pub_ids = [p.id for p in publications if p.id is not None]
    snapshots_by_pub = _safe_batch(ranking_storage.list_latest_snapshots_batch, pub_ids, "snapshot")
    diagnoses_by_pub = _safe_batch(
        diagnosis_storage.list_latest_diagnoses_batch, pub_ids, "diagnosis"
    )

    return [_enrich_publication(p, snapshots_by_pub, diagnoses_by_pub) for p in publications]


def _safe_batch(fn: Any, pub_ids: list[str], label: str) -> dict[str, Any]:
    """RPC 실패 시 빈 dict 로 폴백 — 단순 조회는 내려도 큐 자체는 출력."""
    try:
        return fn(pub_ids)
    except Exception:
        logger.warning("enrich.batch_failed kind=%s", label, exc_info=True)
        return {}


def _enrich_publication(
    pub: Publication,
    snapshots_by_pub: dict[str, Any],
    diagnoses_by_pub: dict[str, Any],
) -> dict[str, Any]:
    """publication 1건에 미리 fetch 된 최신 snapshot + 진단 메타 결합."""
    payload = pub.model_dump(mode="json")
    if pub.id is None:
        payload["latest_snapshot"] = None
        payload["latest_diagnosis"] = None
        return payload

    snap = snapshots_by_pub.get(pub.id)
    payload["latest_snapshot"] = _snapshot_summary(snap) if snap else None

    diag = diagnoses_by_pub.get(pub.id)
    if diag is not None:
        payload["latest_diagnosis"] = {
            "id": diag.id,
            "reason": diag.reason,
            "confidence": float(diag.confidence),
            "diagnosed_at": diag.diagnosed_at.isoformat() if diag.diagnosed_at else None,
            "recommended_action": diag.recommended_action,
            "evidence": list(diag.evidence),
            "metrics": dict(diag.metrics),
        }
    else:
        payload["latest_diagnosis"] = None

    return payload


def _snapshot_summary(s: RankingSnapshot) -> dict[str, Any]:
    return {
        "captured_at": s.captured_at.isoformat() if s.captured_at else None,
        "section": s.section,
        "position": s.position,
    }
