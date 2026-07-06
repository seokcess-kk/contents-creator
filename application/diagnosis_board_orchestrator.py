"""미노출 진단 일괄 액션 보드 use case.

`/insights` 의 '진단 조치' 탭이 호출하는 운영 use case. workflow_status=action_required
publication 들 중 최신 진단을 confidence·reason 으로 필터링해 목록을 제공하고,
선택한 진단들에 대한 일괄 액션을 적절한 orchestrator 로 라우팅한다.

🔴 단일 출처 원칙:
- "재발행 시작" → `application/republish_orchestrator.start_republish`
- "보류"          → `application/publication_actions_orchestrator.hold`
- "기각"          → `application/publication_actions_orchestrator.dismiss`
- "경쟁자 강함"   → `domain/diagnosis/storage.update_user_action` (진단 메모만)

bulk-action 은 단순 user_action wrapper 가 아니다 — action 별로 다른 명령을
호출해 publication_actions / republish_jobs / visibility_diagnoses 의 정합성을
유지한다. partial failure 는 데이터로 반환 (raise 회피).
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from application import publication_actions_orchestrator, republish_orchestrator
from domain.diagnosis import storage as diagnosis_storage
from domain.diagnosis.model import Diagnosis
from domain.ranking import storage as ranking_storage
from domain.ranking.model import Publication

logger = logging.getLogger(__name__)

# 진단 보드의 정책 상수. SPEC-RANKING.md Phase 1 정합.
DEFAULT_MIN_CONFIDENCE = 0.6
DEFAULT_BOARD_LIMIT = 200
# action_required 한 번 조회 시 가져올 publication 상한. 운영 규모(<1000) 가정.
_PUBLICATION_FETCH_LIMIT = 1000

# 4종 액션. 프론트 라벨은 labels.ts 의 DIAGNOSIS_ACTION_LABELS 가 단일 출처.
BulkAction = Literal["republished", "held", "dismissed", "marked_competitor_strong"]
_VALID_ACTIONS: tuple[BulkAction, ...] = (
    "republished",
    "held",
    "dismissed",
    "marked_competitor_strong",
)

# 보류 default 일수 — 운영자가 별도 입력 안 하면 7일 (Phase 1 운영 가이드).
DEFAULT_HOLD_DAYS = 7


# ── 응답 모델 ─────────────────────────────────────────────────────────────


class DiagnosisBoardItem(BaseModel):
    """진단 보드 1행 — publication + 최신 진단."""

    publication: Publication
    diagnosis: Diagnosis


class DiagnosisBoardResponse(BaseModel):
    """진단 보드 응답.

    counts_by_reason 는 필터 적용 후 표시 row 기준. total_action_required 는
    필터와 무관한 action_required publication 전체 수 (오해 방지용 별도 노출).
    """

    items: list[DiagnosisBoardItem]
    counts_by_reason: dict[str, int]
    total_action_required: int


class BulkActionItemResult(BaseModel):
    diagnosis_id: str
    publication_id: str | None = None
    reason: str | None = None
    # succeeded: 성공 / skipped: 멱등으로 변동 없음 또는 stale / failed: 예외
    status: Literal["succeeded", "skipped", "failed"]
    message: str | None = None


class BulkActionResult(BaseModel):
    total: int
    succeeded: list[BulkActionItemResult] = Field(default_factory=list)
    skipped: list[BulkActionItemResult] = Field(default_factory=list)
    failed: list[BulkActionItemResult] = Field(default_factory=list)


# ── 조회 ──────────────────────────────────────────────────────────────────


def get_diagnosis_board(
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    reasons: list[str] | None = None,
    limit: int = DEFAULT_BOARD_LIMIT,
) -> DiagnosisBoardResponse:
    """workflow_status=action_required 인 publication + 최신 진단 매칭.

    필터: min_confidence (>=), reasons (in). limit 는 키워드(=row) 기준.
    counts_by_reason 는 필터 적용 후 표시 결과 기준이라 UI 상단에서
    "현재 보이는 row 의 사유 분포" 로 사용 가능.
    """
    pubs = ranking_storage.list_publications(
        workflow_status=["action_required"],
        limit=_PUBLICATION_FETCH_LIMIT,
    )
    total_action_required = len(pubs)
    if not pubs:
        return DiagnosisBoardResponse(items=[], counts_by_reason={}, total_action_required=0)

    pub_ids = [p.id for p in pubs if p.id is not None]
    diag_by_pub = diagnosis_storage.list_latest_diagnoses_batch(pub_ids)

    items: list[DiagnosisBoardItem] = []
    for pub in pubs:
        if pub.id is None:
            continue
        diag = diag_by_pub.get(pub.id)
        if diag is None:
            continue
        if diag.confidence < min_confidence:
            continue
        if reasons and diag.reason not in reasons:
            continue
        items.append(DiagnosisBoardItem(publication=pub, diagnosis=diag))

    # confidence desc, diagnosed_at desc 보조 정렬 — 운영자가 위에서부터 처리
    items.sort(
        key=lambda it: (
            -it.diagnosis.confidence,
            -(_iso_to_epoch(it.diagnosis.diagnosed_at)),
        )
    )
    items = items[:limit]

    counts = Counter(it.diagnosis.reason for it in items)
    return DiagnosisBoardResponse(
        items=items,
        counts_by_reason=dict(counts),
        total_action_required=total_action_required,
    )


# ── 일괄 액션 ─────────────────────────────────────────────────────────────


def execute_bulk_action(
    *,
    diagnosis_ids: list[str],
    action: str,
) -> BulkActionResult:
    """진단 ID 들에 대한 일괄 액션. action 별로 다른 orchestrator 호출.

    안전 정책 (codex review 2026-05-15 반영):
    - 실행 시점에 publication.workflow_status 가 action_required 가 아니면 skipped
      (보드 조회 후 다른 운영자가 상태 변경했거나, API 직접 호출 stale)
    - republished: active republish job 충돌만 skipped, 그 외 RuntimeError 는 failed
    - held / dismissed: publication 의 현재 status 가 이미 목적 status 면 skipped
    - marked_competitor_strong: 이미 같은 user_action 이면 skipped
    """
    if action not in _VALID_ACTIONS:
        raise ValueError(
            f"action 은 {_VALID_ACTIONS} 중 하나: {action!r}",
        )
    if not diagnosis_ids:
        return BulkActionResult(total=0)

    diagnoses = diagnosis_storage.get_diagnoses_batch(diagnosis_ids)

    result = BulkActionResult(total=len(diagnosis_ids))
    for diag_id in diagnosis_ids:
        diag = diagnoses.get(diag_id)
        if diag is None:
            result.failed.append(
                BulkActionItemResult(
                    diagnosis_id=diag_id,
                    status="failed",
                    message="diagnosis 미존재 또는 stale",
                )
            )
            continue
        try:
            outcome = _apply_action(diag, action)
        except Exception as exc:  # noqa: BLE001 — bulk 는 개별 실패를 데이터로 노출
            logger.warning(
                "diagnosis_board.bulk_action.failed diagnosis_id=%s action=%s err=%s",
                diag_id,
                action,
                exc,
            )
            result.failed.append(
                BulkActionItemResult(
                    diagnosis_id=diag_id,
                    publication_id=diag.publication_id,
                    reason=diag.reason,
                    status="failed",
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        bucket = getattr(result, outcome.status)
        bucket.append(outcome)
    return result


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────


# publication.workflow_status 가 이 상태가 아니면 일괄 액션 모두 skipped.
# republish/hold/dismiss 는 보드에서 보일 때만 의미 있다 (예: held → 재발행 트리거 부적절).
_ACTIONABLE_WORKFLOW = "action_required"


def _apply_action(diag: Diagnosis, action: str) -> BulkActionItemResult:
    # 액션 실행 시점에 publication 의 현재 workflow_status 재검증.
    # 보드 조회 후 stale 이거나 직접 API 호출 시 부적절한 publication 차단.
    # workflow_status != action_required 면 모두 skipped — 이미 held/dismissed 인
    # publication 의 재호출 멱등성도 이 분기로 흡수된다 (보드는 action_required 만 노출).
    if action != "marked_competitor_strong":
        pub = ranking_storage.get_publication(diag.publication_id)
        if pub is None:
            return _result(diag, "failed", "publication 미존재")
        if pub.workflow_status != _ACTIONABLE_WORKFLOW:
            return _result(
                diag,
                "skipped",
                f"stale workflow_status: {pub.workflow_status} ({_ACTIONABLE_WORKFLOW} 만 처리 대상)",
            )

    if action == "republished":
        return _action_republish(diag)
    if action == "held":
        return _action_hold(diag)
    if action == "dismissed":
        return _action_dismiss(diag)
    if action == "marked_competitor_strong":
        return _action_mark_competitor(diag)
    raise ValueError(f"unsupported action: {action!r}")


def _action_republish(diag: Diagnosis) -> BulkActionItemResult:
    try:
        info = republish_orchestrator.start_republish(
            diag.publication_id,
            strategy="full_rewrite",
            diagnosis_id=diag.id,
        )
    except RuntimeError as exc:
        # republish_orchestrator 가 RuntimeError 로 던지는 케이스 분류:
        # 1) 동일 source 에 active(queued/running) job 충돌 → skipped (운영 의도)
        # 2) draft publication insert / republish_jobs INSERT 실패 등 인프라 오류 → failed
        # republish_orchestrator.py 의 실제 메시지: "이미 진행 중인 재발행 작업이 있습니다: {id}"
        # 한국어 "이미 진행" 또는 영어 "active" 키워드 양쪽 매칭 (영문 메시지 변경 대비).
        if _is_active_job_conflict(exc):
            return _result(diag, "skipped", f"이미 진행 중인 재발행 job: {exc}")
        return _result(diag, "failed", f"RuntimeError: {exc}")
    return _result(diag, "succeeded", f"job_id={info.get('pipeline_job_id')}")


def _is_active_job_conflict(exc: BaseException) -> bool:
    """republish_orchestrator 의 active job 충돌 RuntimeError 식별."""
    text = str(exc).lower()
    return "이미 진행" in str(exc) or "active" in text


def _action_hold(diag: Diagnosis) -> BulkActionItemResult:
    pub = publication_actions_orchestrator.hold(
        diag.publication_id, days=DEFAULT_HOLD_DAYS, reason="진단 보드 일괄 보류"
    )
    if pub is None:
        return _result(diag, "failed", "publication 미존재")
    _record_user_action(diag.id, "held")
    return _result(diag, "succeeded", f"{DEFAULT_HOLD_DAYS}일 보류")


def _action_dismiss(diag: Diagnosis) -> BulkActionItemResult:
    pub = publication_actions_orchestrator.dismiss(
        diag.publication_id, reason="진단 보드 일괄 기각"
    )
    if pub is None:
        return _result(diag, "failed", "publication 미존재")
    _record_user_action(diag.id, "dismissed")
    return _result(diag, "succeeded", None)


def _action_mark_competitor(diag: Diagnosis) -> BulkActionItemResult:
    if diag.user_action == "marked_competitor_strong":
        return _result(diag, "skipped", "이미 같은 상태")
    _record_user_action(diag.id, "marked_competitor_strong")
    return _result(diag, "succeeded", None)


def _result(
    diag: Diagnosis,
    status: Literal["succeeded", "skipped", "failed"],
    message: str | None,
) -> BulkActionItemResult:
    return BulkActionItemResult(
        diagnosis_id=diag.id or "",
        publication_id=diag.publication_id,
        reason=diag.reason,
        status=status,
        message=message,
    )


def _record_user_action(diagnosis_id: str | None, action: str) -> None:
    """진단 row 에 user_action 기록. id 가 없으면 무시 (테스트 안전망)."""
    if not diagnosis_id:
        return
    now_iso = datetime.now(tz=UTC).isoformat()
    diagnosis_storage.update_user_action(diagnosis_id, action, now_iso)


def _iso_to_epoch(value: Any) -> float:
    if not value:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0
