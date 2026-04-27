"""일괄 순위 측정 use case — 운영자 수동 트리거용.

기존 `check_all_active_rankings()` 와 차이:
- publication_ids 옵션으로 대상 좁힘 가능 (None 이면 measurable 전체)
- ProgressReporter 주입 — job_manager 가 WebSocket 으로 진행률 emit
- 측정 대상 필터는 동일 (URL not null, workflow_status active/action_required)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from application.ranking_orchestrator import check_rankings_for_publication
from config.settings import settings
from domain.ranking import storage as ranking_storage
from domain.ranking.model import RankingCheckSummary, RankingMatchError

if TYPE_CHECKING:
    from application.progress import ProgressReporter

logger = logging.getLogger(__name__)


def bulk_check_rankings(
    publication_ids: list[str] | None = None,
    *,
    reporter: ProgressReporter | None = None,
) -> RankingCheckSummary:
    """선택된(또는 전체) publication 의 SERP 일괄 측정.

    publication_ids=None: measurable (URL 있고 active/action_required) 전체.
    publication_ids=[...]: 그 목록 중 measurable 만 (제외 대상 자동 필터).

    개별 실패는 logging.warning + reporter.stage_progress 로 알리고 다음으로.
    Bright Data rate 보호 위해 publication 간 sleep.
    """
    started = time.monotonic()
    targets = _resolve_targets(publication_ids)
    total = len(targets)
    if reporter is not None:
        reporter.stage_start("ranking_bulk_check", total=total)

    checked = 0
    found = 0
    errors = 0
    skipped = 0

    for idx, pub in enumerate(targets, start=1):
        if pub.id is None:
            skipped += 1
            continue
        try:
            snap = check_rankings_for_publication(pub.id)
            checked += 1
            if snap.position is not None:
                found += 1
            if reporter is not None:
                pos_str = (
                    f"{snap.section} {snap.position}위" if snap.position is not None else "미노출"
                )
                reporter.stage_progress(idx, f"{pub.keyword} → {pos_str}")
        except (RankingMatchError, ValueError) as exc:
            errors += 1
            logger.warning(
                "bulk_check.failed publication_id=%s keyword=%r err=%s",
                pub.id,
                pub.keyword,
                exc,
            )
            if reporter is not None:
                reporter.stage_progress(idx, f"{pub.keyword} 실패: {exc}")
        time.sleep(settings.ranking_check_sleep_seconds)

    duration = time.monotonic() - started
    summary = RankingCheckSummary(
        checked_count=checked,
        found_count=found,
        errors_count=errors,
        duration_seconds=duration,
    )
    if reporter is not None:
        reporter.stage_end(
            "ranking_bulk_check",
            {
                "total": total,
                "checked": checked,
                "found": found,
                "errors": errors,
                "skipped": skipped,
            },
        )
    logger.info(
        "bulk_check.done total=%d checked=%d found=%d errors=%d skipped=%d duration=%.1fs",
        total,
        checked,
        found,
        errors,
        skipped,
        duration,
    )
    return summary


def _resolve_targets(publication_ids: list[str] | None) -> list:
    """측정 대상 publication 리스트.

    URL 있고 workflow_status 가 active/action_required 인 것만.
    publication_ids 가 주어지면 거기서 추가 필터.
    """
    all_pubs = ranking_storage.list_publications(limit=10_000)
    measurable = [
        p
        for p in all_pubs
        if p.url is not None and p.workflow_status in ("active", "action_required")
    ]
    if publication_ids is None:
        return measurable
    id_set = set(publication_ids)
    return [p for p in measurable if p.id in id_set]


def count_measurable(publication_ids: list[str] | None = None) -> int:
    """일괄 측정 시 실제 대상이 될 publication 개수 (UI 미리 표시용)."""
    return len(_resolve_targets(publication_ids))
