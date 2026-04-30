"""운영 홈 use case — 요약 카드 + 탭 필터링.

`/rankings` 첫 화면이 "오늘 처리해야 할 작업 큐" 가 되도록 데이터 집계.
키워드 포트폴리오 운영 OS 의 메인 진입점.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from domain.diagnosis import storage as diagnosis_storage
from domain.keyword_difficulty import storage as difficulty_storage
from domain.keyword_difficulty.model import KeywordDifficulty
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication, RankingSnapshot

logger = logging.getLogger(__name__)

# P0-3: 탭별 필터 — workflow_status + visibility_status 동시 IN 매핑.
# "active" 탭은 워크플로우=active AND 가시성 in (exposed/recovered) — 진짜 노출 중만.
# 빈 리스트는 "필터 없음" 의미.
TAB_FILTERS: dict[str, dict[str, list[str]]] = {
    "action_required": {"workflow": ["action_required"], "visibility": []},
    "republishing": {"workflow": ["republishing"], "visibility": []},
    "held": {"workflow": ["held"], "visibility": []},
    "active": {"workflow": ["active"], "visibility": ["exposed", "recovered"]},
    "dismissed": {"workflow": ["dismissed"], "visibility": []},
    "all": {"workflow": [], "visibility": []},
}

DIFFICULTY_STALE_DAYS = 30
DIFFICULTY_LOOKBACK_MIN = 500
DIFFICULTY_LOOKBACK_PER_PUBLICATION = 10


def get_summary() -> dict[str, int]:
    """운영 홈 상단 요약 카드용 카운트.

    "active" 카운트는 workflow=active AND visibility in (exposed/recovered) —
    실제 노출 의미와 일치 (P0-3). 그 외는 workflow_status 별 카운트.
    """
    counts = ranking_storage.count_publications_by_workflow_status()
    exposed_active = counts.get("__exposed", 0)
    summary = {
        "action_required": counts.get("action_required", 0),
        "republishing": counts.get("republishing", 0),
        "held": counts.get("held", 0),
        "active": exposed_active,
        "dismissed": counts.get("dismissed", 0),
        "draft": counts.get("draft", 0),
    }
    # total 은 workflow_status 모든 카운트 (가상 __exposed 제외)
    summary["total"] = sum(v for k, v in counts.items() if not k.startswith("__"))
    summary.update(_difficulty_summary(limit=500))
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
    spec = TAB_FILTERS[tab]
    publications = ranking_storage.list_publications(
        limit=limit,
        workflow_status=spec["workflow"] or None,
        visibility_status=spec["visibility"] or None,
    )

    pub_ids = [p.id for p in publications if p.id is not None]
    snapshots_by_pub = _safe_batch(ranking_storage.list_latest_snapshots_batch, pub_ids, "snapshot")
    diagnoses_by_pub = _safe_batch(
        diagnosis_storage.list_latest_diagnoses_batch, pub_ids, "diagnosis"
    )
    difficulty_by_keyword = _latest_difficulties_for_publications(publications)

    return [
        _enrich_publication(p, snapshots_by_pub, diagnoses_by_pub, difficulty_by_keyword)
        for p in publications
    ]


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
    difficulty_by_keyword: dict[str, KeywordDifficulty],
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

    difficulty = difficulty_by_keyword.get(_normalize_keyword(pub.keyword))
    payload["keyword_difficulty"] = _difficulty_summary_payload(difficulty)

    return payload


def _snapshot_summary(s: RankingSnapshot) -> dict[str, Any]:
    return {
        "captured_at": s.captured_at.isoformat() if s.captured_at else None,
        "section": s.section,
        "position": s.position,
    }


def _latest_difficulties_for_publications(
    publications: list[Publication],
) -> dict[str, KeywordDifficulty]:
    """Fetch recent difficulty snapshots once and match by normalized primary keyword."""
    keywords = {_normalize_keyword(p.keyword) for p in publications if p.keyword}
    if not keywords:
        return {}

    limit = max(DIFFICULTY_LOOKBACK_MIN, len(publications) * DIFFICULTY_LOOKBACK_PER_PUBLICATION)
    try:
        snapshots = difficulty_storage.list_recent(limit=limit)
    except Exception:
        logger.warning("enrich.difficulty_batch_failed", exc_info=True)
        return {}

    by_keyword: dict[str, KeywordDifficulty] = {}
    for diff in snapshots:
        key = _normalize_keyword(diff.keyword)
        if key not in keywords or key in by_keyword:
            continue
        by_keyword[key] = diff
    return by_keyword


def _difficulty_summary(limit: int) -> dict[str, int]:
    try:
        publications = ranking_storage.list_publications(limit=limit)
    except Exception:
        logger.warning("summary.difficulty_publications_failed", exc_info=True)
        return {"difficulty_missing": 0, "difficulty_stale": 0}
    difficulty_by_keyword = _latest_difficulties_for_publications(publications)
    missing = 0
    stale = 0
    for pub in publications:
        diff = difficulty_by_keyword.get(_normalize_keyword(pub.keyword))
        if diff is None:
            missing += 1
        elif _is_stale(diff.checked_at):
            stale += 1
    return {
        "difficulty_missing": missing,
        "difficulty_stale": stale,
    }


def _difficulty_summary_payload(diff: KeywordDifficulty | None) -> dict[str, Any] | None:
    if diff is None:
        return None
    sv = diff.search_volume
    return {
        "keyword": diff.keyword,
        "grade": diff.grade.value,
        "score": diff.score,
        "blog_slots": diff.composition.blog_slots,
        "spam_cards": diff.composition.spam_cards,
        "total_cards": diff.composition.total_cards,
        "monthly_total_search": sv.monthly_total if sv else None,
        "sov_grade": diff.sov_grade.value,
        "checked_at": diff.checked_at.isoformat() if diff.checked_at else None,
        "is_stale": _is_stale(diff.checked_at),
        "stale_after_days": DIFFICULTY_STALE_DAYS,
    }


def _is_stale(checked_at: datetime | None) -> bool:
    if checked_at is None:
        return True
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    age_days = (datetime.now(UTC) - checked_at.astimezone(UTC)).days
    return age_days >= DIFFICULTY_STALE_DAYS


def _normalize_keyword(keyword: str) -> str:
    return "".join(keyword.split()).lower()
