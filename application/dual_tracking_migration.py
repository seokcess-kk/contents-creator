"""재발행 듀얼 트래킹 정책 백필 — 일회성 마이그레이션 헬퍼.

2026-04-29 정책 전환:
- 재발행 시작 시 부모 publication 을 `republishing` 으로 잠그지 않는다.
- 자식 publication 은 URL 등록 시 `draft → active` 자동 전이.

본 모듈은 정책 전환 이전에 잠긴 row 들을 `active` 로 복귀시키는 백필 함수를
제공한다. publication_actions 에 액션 기록을 남겨 추적성을 유지한다.

scripts/migrate_dual_tracking.py 가 thin CLI wrapper 로 호출.
"""

from __future__ import annotations

import logging

from domain.ranking import publication_actions as actions_storage
from domain.ranking import storage
from domain.ranking.model import Publication
from domain.ranking.publication_actions import PublicationAction

logger = logging.getLogger(__name__)


def collect_dual_tracking_targets(
    keywords: list[str] | None = None,
) -> dict[str, list[Publication]]:
    """정리 대상 publications 을 분류해 반환.

    - parents_to_activate: workflow_status="republishing" + url 있음
    - drafts_to_activate:  workflow_status="draft" + url 있음

    Args:
        keywords: 지정 시 해당 키워드만 필터링. 미지정 시 전체.
    """
    publications = storage.list_publications(limit=10_000)
    parents: list[Publication] = []
    drafts: list[Publication] = []
    for p in publications:
        if keywords and p.keyword not in keywords:
            continue
        if p.url is None:
            continue
        if p.workflow_status == "republishing":
            parents.append(p)
        elif p.workflow_status == "draft":
            drafts.append(p)
    return {"parents_to_activate": parents, "drafts_to_activate": drafts}


def apply_dual_tracking_migration(
    keywords: list[str] | None = None,
) -> dict[str, int]:
    """수집된 대상에 대해 status 전이 + 액션 기록을 일괄 적용.

    Returns: {"parents_activated", "drafts_activated", "failed"}
    """
    targets = collect_dual_tracking_targets(keywords)
    counts = {"parents_activated": 0, "drafts_activated": 0, "failed": 0}
    for pub in targets["parents_to_activate"]:
        if pub.id is None:
            continue
        try:
            _activate_parent(pub)
            counts["parents_activated"] += 1
        except Exception:
            logger.exception("dual_tracking.parent_failed publication_id=%s", pub.id)
            counts["failed"] += 1
    for pub in targets["drafts_to_activate"]:
        if pub.id is None:
            continue
        try:
            _activate_draft(pub)
            counts["drafts_activated"] += 1
        except Exception:
            logger.exception("dual_tracking.draft_failed publication_id=%s", pub.id)
            counts["failed"] += 1
    return counts


def _activate_parent(pub: Publication) -> None:
    """republishing 부모 → active. auto_requeued 액션 기록."""
    assert pub.id is not None
    actions_storage.insert_action(
        PublicationAction(
            publication_id=pub.id,
            action="auto_requeued",
            note="듀얼 트래킹 마이그레이션 — republishing → active",
            metadata={
                "trigger": "dual_tracking_migration",
                "previous_workflow": "republishing",
            },
        )
    )
    storage.update_publication_workflow_state(pub.id, workflow_status="active")


def _activate_draft(pub: Publication) -> None:
    """url 등록된 draft → active. url_registered 액션 백필."""
    assert pub.id is not None
    actions_storage.insert_action(
        PublicationAction(
            publication_id=pub.id,
            action="url_registered",
            note="듀얼 트래킹 마이그레이션 — draft + url → active 백필",
            metadata={"url": pub.url, "backfill": True},
        )
    )
    storage.update_publication_workflow_state(pub.id, workflow_status="active")
