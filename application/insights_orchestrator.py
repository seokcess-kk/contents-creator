"""Insights use case — 성공/실패 패턴 통계.

사용자 운영 철학 §9 의 Insights 화면 — 운영 데이터 누적 기반 분석.
초기에는 단순 그룹 집계 (난이도 × 진입율, 검색량 구간 × 평균 best, compliance × ranking).
데이터 부족 시 graceful — 빈 dict 반환.
"""

from __future__ import annotations

import logging
from typing import Any

from application import performance_orchestrator
from domain.keyword_difficulty import storage as difficulty_storage

logger = logging.getLogger(__name__)

# 검색량 bucket 경계.
_VOLUME_BUCKETS: tuple[tuple[int, int | None, str], ...] = (
    (0, 100, "<100"),
    (100, 500, "100-500"),
    (500, 2000, "500-2K"),
    (2000, 10_000, "2K-10K"),
    (10_000, None, ">10K"),
)


def get_insights_summary(publication_limit: int = 200) -> dict[str, Any]:
    """발행 데이터 기반 통계 요약 — 빈 데이터에도 graceful.

    반환 키:
      - difficulty_top10: dict[grade, {total, top10, ratio}]
      - volume_top10: dict[bucket_label, {total, top10, ratio, avg_best}]
      - dN_top10_ratio: dict[N, ratio]  # D+N 시점 Top10 진입 비율
      - compliance_avg_best: {passed, failed, unknown}  # compliance_passed × 평균 best
      - sample_size: int
    """
    perf_items = performance_orchestrator.list_performance(limit=publication_limit)
    if not perf_items:
        return {
            "sample_size": 0,
            "difficulty_top10": {},
            "volume_top10": {},
            "dN_top10_ratio": {},
            "compliance_avg_best": {},
        }

    keywords = sorted({it["keyword"] for it in perf_items if it.get("keyword")})
    difficulty_map = _fetch_difficulty_map(keywords)

    return {
        "sample_size": len(perf_items),
        "difficulty_top10": _difficulty_top10(perf_items, difficulty_map),
        "volume_top10": _volume_top10(perf_items, difficulty_map),
        "dN_top10_ratio": _dn_top10_ratio(perf_items),
        "compliance_avg_best": _compliance_avg_best(perf_items),
    }


def _fetch_difficulty_map(keywords: list[str]) -> dict[str, dict[str, Any]]:
    """키워드별 최신 difficulty 메타 (grade, search_volume_total)."""
    if not keywords:
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        recent = difficulty_storage.list_recent(limit=max(500, len(keywords) * 2))
    except Exception:
        logger.warning("insights.difficulty_fetch_failed", exc_info=True)
        return {}
    seen: set[str] = set()
    for diff in recent:
        kw = diff.keyword
        if kw in seen:
            continue
        seen.add(kw)
        sv_total = diff.search_volume.monthly_total if diff.search_volume else None
        out[kw] = {"grade": diff.grade.value, "search_volume": sv_total}
    return out


def _difficulty_top10(
    perf_items: list[dict[str, Any]], difficulty_map: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """난이도 등급 × Top10 진입율."""
    by_grade: dict[str, dict[str, int]] = {}
    for it in perf_items:
        meta = difficulty_map.get(it.get("keyword", ""))
        grade = meta.get("grade") if meta else "unknown"
        bucket = by_grade.setdefault(str(grade), {"total": 0, "top10": 0})
        bucket["total"] += 1
        if (it.get("best_position") or 999) <= 10:
            bucket["top10"] += 1
    return {
        g: {**b, "ratio": round(b["top10"] / b["total"], 3) if b["total"] else 0.0}
        for g, b in by_grade.items()
    }


def _volume_top10(
    perf_items: list[dict[str, Any]], difficulty_map: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """검색량 bucket × Top10 진입율 + 평균 best."""
    by_bucket: dict[str, dict[str, Any]] = {}
    for it in perf_items:
        meta = difficulty_map.get(it.get("keyword", ""))
        sv = meta.get("search_volume") if meta else None
        label = _volume_bucket_label(sv)
        bucket = by_bucket.setdefault(label, {"total": 0, "top10": 0, "best_sum": 0, "best_n": 0})
        bucket["total"] += 1
        best = it.get("best_position")
        if best is not None:
            bucket["best_sum"] += best
            bucket["best_n"] += 1
            if best <= 10:
                bucket["top10"] += 1
    out: dict[str, dict[str, Any]] = {}
    for label, b in by_bucket.items():
        avg_best = round(b["best_sum"] / b["best_n"], 1) if b["best_n"] else None
        out[label] = {
            "total": b["total"],
            "top10": b["top10"],
            "ratio": round(b["top10"] / b["total"], 3) if b["total"] else 0.0,
            "avg_best": avg_best,
        }
    return out


def _volume_bucket_label(sv: int | None) -> str:
    if sv is None:
        return "unknown"
    for low, high, label in _VOLUME_BUCKETS:
        if sv >= low and (high is None or sv < high):
            return label
    return "unknown"


def _dn_top10_ratio(perf_items: list[dict[str, Any]]) -> dict[str, float]:
    """D+N 시점 Top10 진입 비율 (D+1, D+3, D+7, D+14, D+30)."""
    out: dict[str, float] = {}
    for n in ("1", "3", "7", "14", "30"):
        total = 0
        top10 = 0
        for it in perf_items:
            pos = (it.get("dN_position") or {}).get(n) or (it.get("dN_position") or {}).get(int(n))
            if pos is None:
                continue
            total += 1
            if pos <= 10:
                top10 += 1
        out[n] = round(top10 / total, 3) if total else 0.0
    return out


def _compliance_avg_best(perf_items: list[dict[str, Any]]) -> dict[str, Any]:
    """compliance 통과/위반 별 평균 best position. compliance_passed 는 batch_item
    수준 메타라 perf_items 에는 없음 → 자체 fetch 필요. 단순화: 여기는 placeholder."""
    # batch_items 와 publication 매칭은 추가 비용. 본 PR 은 골격만 — 후속에서
    # find_batch_item_by_publication_id 등으로 보강.
    return {}
