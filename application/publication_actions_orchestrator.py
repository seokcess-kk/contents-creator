"""publication 운영 액션 — 보류·해제·기각·복원.

🔴 핵심 원칙: publication_actions 테이블이 히스토리의 single source of truth.
액션 INSERT 가 실패하면 status 전이도 진행하지 않는다 (raise 로 보장).
이전 best-effort 정책은 히스토리 유실 시 status 만 바뀌어 운영 추적이
끊기는 부패 시나리오를 만들었기에 폐기.

원자성 한계: Supabase REST 는 다중 statement transaction 미지원.
따라서 INSERT → UPDATE 순서를 보장하되, INSERT 실패 시 raise 로
UPDATE 자체가 실행되지 않도록 한다. 반대(UPDATE 실패) 시에는 액션
히스토리가 INSERT 된 채 status 가 남는 비대칭 케이스가 발생할 수
있으므로, 이 케이스는 추후 RPC 로 원자화 예정 (P1).

매일 09:00 측정 사이클이 held_until 만료 등 자동 전이도 동일 패턴으로 호출.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from domain.ranking import publication_actions as actions_storage
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication
from domain.ranking.publication_actions import PublicationAction

logger = logging.getLogger(__name__)


def hold(
    publication_id: str,
    *,
    days: int,
    reason: str | None = None,
) -> Publication | None:
    """보류 — N일 후 자동 큐 복귀."""
    pub = ranking_storage.get_publication(publication_id)
    if pub is None:
        return None

    now = datetime.now(tz=UTC)
    held_until = now + timedelta(days=days)

    _record_action(
        publication_id=publication_id,
        action="held",
        note=reason,
        metadata={"days": days, "held_until": held_until.isoformat()},
    )

    return ranking_storage.update_publication_workflow_state(
        publication_id,
        workflow_status="held",
        held_until=held_until,
        held_reason=reason,
    )


def release_hold(publication_id: str) -> Publication | None:
    """사용자 명시적 보류 해제 → action_required 복귀."""
    pub = ranking_storage.get_publication(publication_id)
    if pub is None:
        return None

    _record_action(
        publication_id=publication_id,
        action="released_hold",
        note="사용자 명시적 해제",
        metadata={"trigger": "manual"},
    )

    return ranking_storage.update_publication_workflow_state(
        publication_id,
        workflow_status="action_required",
        clear_held=True,
    )


def dismiss(
    publication_id: str,
    *,
    reason: str | None = None,
) -> Publication | None:
    """기각 — 더 이상 측정·작업하지 않음 (workflow_status=dismissed)."""
    pub = ranking_storage.get_publication(publication_id)
    if pub is None:
        return None

    _record_action(
        publication_id=publication_id,
        action="dismissed",
        note=reason,
        metadata={},
    )

    return ranking_storage.update_publication_workflow_state(
        publication_id,
        workflow_status="dismissed",
    )


def restore(publication_id: str) -> Publication | None:
    """기각 취소 → action_required 복귀."""
    pub = ranking_storage.get_publication(publication_id)
    if pub is None:
        return None

    _record_action(
        publication_id=publication_id,
        action="restored",
        note=None,
        metadata={},
    )

    return ranking_storage.update_publication_workflow_state(
        publication_id,
        workflow_status="action_required",
    )


def auto_requeue(
    publication_id: str,
    *,
    trigger: str,
    note: str,
) -> Publication | None:
    """시스템 자동 큐 복귀 — state_calculator 트리거 사유 기반.

    trigger: republish_url_pending | republish_job_stuck | republish_job_failed
           | republish_job_missing | hold_expired
    """
    _record_action(
        publication_id=publication_id,
        action="auto_requeued",
        note=note,
        metadata={"auto": True, "trigger": trigger},
    )
    return ranking_storage.update_publication_workflow_state(
        publication_id,
        workflow_status="action_required",
        clear_held=trigger == "hold_expired",
    )


def _record_action(
    publication_id: str,
    *,
    action: str,
    note: str | None,
    metadata: dict[str, Any],
    diagnosis_id: str | None = None,
) -> None:
    """publication_actions 히스토리에 액션 기록 (실패 시 raise).

    히스토리는 single source of truth — INSERT 실패 시 status 전이도
    중단되어야 하므로 예외를 그대로 전파한다. 호출자(API 레이어)가 500 으로
    응답하고, 사용자는 재시도 가능. 부분 적용 상태로 진행되어 데이터가
    부패하는 것보다 명시적 실패가 운영 안전성 측면에서 우선이다.
    """
    actions_storage.insert_action(
        PublicationAction(
            publication_id=publication_id,
            diagnosis_id=diagnosis_id,
            action=action,
            note=note,
            metadata=metadata,
        )
    )
