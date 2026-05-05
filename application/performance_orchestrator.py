"""Performance Dashboard use case.

발행된 publication 의 순위 궤적 (D+1/3/7/14/30) + best/current rank + top10 유지 일수
를 집계해 사용자 운영 철학 §9 의 "Performance Dashboard" 화면 데이터를 제공한다.

도메인 격리: ranking 도메인은 그대로 사용 (URL 매칭/snapshot 조회). 본 모듈이
publication × snapshots 시계열을 가공해 D+N 인덱싱 + 통계 산출.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication, RankingSnapshot

logger = logging.getLogger(__name__)

# D+N 측정 buckets — published_at 기준 ±1 일 허용오차로 가장 가까운 snapshot 선택.
_DAY_OFFSETS: tuple[int, ...] = (1, 3, 7, 14, 30)


def get_publication_trajectory(publication_id: str) -> dict[str, Any]:
    """단일 publication 의 D+N 순위 궤적 + 통계.

    반환 키:
      - publication_id / keyword / url / published_at
      - dN_position: dict[int, int|None]  # {1: 5, 3: 3, 7: 1, ...}
      - best_position / current_position
      - top10_days  # position<=10 인 snapshot 수
      - snapshot_count
    """
    pub = ranking_storage.get_publication(publication_id)
    if pub is None:
        raise ValueError(f"publication 미존재: {publication_id}")

    # 시계열 (capture asc) — D+N 매칭 + 최저/최신 추출에 모두 사용.
    snaps = ranking_storage.list_snapshots(publication_id, limit=500)
    snaps.sort(key=lambda s: s.captured_at or datetime.now(UTC))

    return _build_trajectory(pub, snaps)


def list_performance(limit: int = 50) -> list[dict[str, Any]]:
    """모든 published publication 의 performance 요약.

    URL 등록된 publication 만 (workflow_status='active' or non-draft). 최근 N건.
    각 publication 마다 snapshots 시계열을 가져와 D+N + best/current 산출.
    """
    publications = ranking_storage.list_publications(limit=limit)
    return [_summarize(p) for p in publications if p.id is not None and p.url is not None]


def _summarize(pub: Publication) -> dict[str, Any]:
    """단일 publication 요약 — 실패 시 dN 빈 dict 로 graceful."""
    if pub.id is None:
        return {"publication_id": None, "keyword": pub.keyword}
    try:
        snaps = ranking_storage.list_snapshots(pub.id, limit=500)
        snaps.sort(key=lambda s: s.captured_at or datetime.now(UTC))
        return _build_trajectory(pub, snaps)
    except Exception:
        logger.warning("performance.summary_failed pub_id=%s", pub.id, exc_info=True)
        return {
            "publication_id": pub.id,
            "keyword": pub.keyword,
            "url": pub.url,
            "published_at": pub.published_at.isoformat() if pub.published_at else None,
            "dN_position": dict.fromkeys(_DAY_OFFSETS, None),
            "best_position": None,
            "current_position": None,
            "top10_days": 0,
            "snapshot_count": 0,
        }


def _build_trajectory(pub: Publication, snaps: list[RankingSnapshot]) -> dict[str, Any]:
    """publication + snapshots 시계열 → D+N 매칭 + 통계 dict."""
    base = pub.published_at
    day_n_position: dict[int, int | None] = dict.fromkeys(_DAY_OFFSETS, None)
    if base is not None:
        for n in _DAY_OFFSETS:
            target = base + timedelta(days=n)
            best_match = _nearest_snapshot(snaps, target, max_gap_days=1.5)
            day_n_position[n] = best_match.position if best_match else None

    positions = [s.position for s in snaps if s.position is not None]
    best_position = min(positions) if positions else None

    current_snap = snaps[-1] if snaps else None
    current_position = current_snap.position if current_snap else None

    top10_days = sum(1 for p in positions if p <= 10)

    return {
        "publication_id": pub.id,
        "keyword": pub.keyword,
        "slug": pub.slug,
        "url": pub.url,
        "published_at": base.isoformat() if base else None,
        "dN_position": day_n_position,
        "best_position": best_position,
        "current_position": current_position,
        "top10_days": top10_days,
        "snapshot_count": len(snaps),
    }


def _nearest_snapshot(
    snaps: list[RankingSnapshot], target: datetime, *, max_gap_days: float
) -> RankingSnapshot | None:
    """target 시점에 가장 가까운 snapshot. max_gap_days 이내만 매칭."""
    best: RankingSnapshot | None = None
    best_gap = float("inf")
    for s in snaps:
        if s.captured_at is None:
            continue
        gap_seconds = abs((s.captured_at - target).total_seconds())
        gap_days = gap_seconds / 86400.0
        if gap_days <= max_gap_days and gap_days < best_gap:
            best_gap = gap_days
            best = s
    return best
