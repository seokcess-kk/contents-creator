"""application/diagnosis_board_orchestrator.py — 단위 테스트.

핵심 검증:
- get_diagnosis_board: workflow=action_required 만, min_confidence·reasons 필터,
  counts_by_reason 정확성, confidence desc 정렬, total_action_required 별도 노출
- execute_bulk_action: action 별로 다른 orchestrator 호출 (republish/hold/dismiss/mark),
  partial failure → succeeded/skipped/failed 분리, 알 수 없는 action 은 ValueError
- 단일 출처: backend Literal UserAction 과 _VALID_ACTIONS 일치 회귀
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import get_args
from unittest.mock import patch

import pytest

from application import diagnosis_board_orchestrator as board
from domain.diagnosis.model import Diagnosis, UserAction
from domain.ranking.model import Publication


def _pub(pid: str, keyword: str = "kw", workflow_status: str = "action_required") -> Publication:
    return Publication(
        id=pid,
        keyword=keyword,
        url=f"https://m.blog.naver.com/u/{pid}",
        slug=f"slug-{pid}",
        workflow_status=workflow_status,
        visibility_status="off_radar",
    )


def _diag(
    pid: str,
    reason: str = "lost_visibility",
    confidence: float = 0.8,
    diag_id: str | None = None,
) -> Diagnosis:
    return Diagnosis(
        id=diag_id or f"d-{pid}",
        publication_id=pid,
        diagnosed_at=datetime.now(tz=UTC),
        reason=reason,
        confidence=confidence,
        evidence=["근거"],
        metrics={},
        recommended_action="권장",
    )


# ── get_diagnosis_board ───────────────────────────────────────────────────


class TestGetDiagnosisBoard:
    def test_filter_min_confidence_and_reason(self) -> None:
        pubs = [_pub("p1"), _pub("p2"), _pub("p3")]
        diags = {
            "p1": _diag("p1", "lost_visibility", 0.9),
            "p2": _diag("p2", "never_indexed", 0.55),  # min_confidence 미달
            "p3": _diag("p3", "cannibalization", 0.85),
        }
        with (
            patch.object(board.ranking_storage, "list_publications", return_value=pubs),
            patch.object(
                board.diagnosis_storage, "list_latest_diagnoses_batch", return_value=diags
            ),
        ):
            result = board.get_diagnosis_board(
                min_confidence=0.7, reasons=["lost_visibility", "cannibalization"]
            )
        # p1, p3 만 남음. p2 는 confidence 미달 + reason 불일치
        kws = [it.publication.id for it in result.items]
        assert kws == ["p1", "p3"]
        # counts_by_reason 은 표시 결과 기준
        assert result.counts_by_reason == {"lost_visibility": 1, "cannibalization": 1}
        # total_action_required 는 필터와 무관한 publication 전체 수
        assert result.total_action_required == 3

    def test_sort_by_confidence_desc(self) -> None:
        pubs = [_pub("low"), _pub("mid"), _pub("hi")]
        diags = {
            "low": _diag("low", confidence=0.65),
            "mid": _diag("mid", confidence=0.75),
            "hi": _diag("hi", confidence=0.95),
        }
        with (
            patch.object(board.ranking_storage, "list_publications", return_value=pubs),
            patch.object(
                board.diagnosis_storage, "list_latest_diagnoses_batch", return_value=diags
            ),
        ):
            result = board.get_diagnosis_board(min_confidence=0.5)
        assert [it.publication.id for it in result.items] == ["hi", "mid", "low"]

    def test_skips_publications_without_diagnosis(self) -> None:
        pubs = [_pub("p1"), _pub("p2")]
        diags = {"p1": _diag("p1")}
        with (
            patch.object(board.ranking_storage, "list_publications", return_value=pubs),
            patch.object(
                board.diagnosis_storage, "list_latest_diagnoses_batch", return_value=diags
            ),
        ):
            result = board.get_diagnosis_board(min_confidence=0.5)
        assert [it.publication.id for it in result.items] == ["p1"]
        assert result.total_action_required == 2

    def test_empty_publications_returns_zero(self) -> None:
        with (
            patch.object(board.ranking_storage, "list_publications", return_value=[]),
            patch.object(board.diagnosis_storage, "list_latest_diagnoses_batch", return_value={}),
        ):
            result = board.get_diagnosis_board(min_confidence=0.5)
        assert result.items == []
        assert result.total_action_required == 0
        assert result.counts_by_reason == {}


# ── execute_bulk_action ───────────────────────────────────────────────────


def _patch_load_diagnoses(diagnoses: list[Diagnosis]):
    """diagnosis_storage.get_diagnoses_batch 우회 — id→Diagnosis dict 직접 주입."""
    by_id = {d.id: d for d in diagnoses if d.id}
    return patch.object(board.diagnosis_storage, "get_diagnoses_batch", return_value=by_id)


def _patch_get_publication(pub: Publication | None):
    """ranking_storage.get_publication 우회 — workflow_status 재검증 케이스용."""
    return patch.object(board.ranking_storage, "get_publication", return_value=pub)


class TestExecuteBulkAction:
    def test_rejects_unknown_action(self) -> None:
        with pytest.raises(ValueError, match="action 은"):
            board.execute_bulk_action(diagnosis_ids=["d-1"], action="unknown_action")

    def test_empty_diagnosis_ids_short_circuits(self) -> None:
        result = board.execute_bulk_action(diagnosis_ids=[], action="held")
        assert result.total == 0
        assert result.succeeded == []

    def test_republish_routes_to_republish_orchestrator(self) -> None:
        diag = _diag("p1", diag_id="d-1")
        mock_info = {"pipeline_job_id": "job-xyz"}
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.republish_orchestrator, "start_republish", return_value=mock_info
            ) as start,
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="republished")
        start.assert_called_once_with("p1", strategy="full_rewrite", diagnosis_id="d-1")
        assert len(result.succeeded) == 1
        assert "job-xyz" in (result.succeeded[0].message or "")

    def test_republish_active_job_conflict_is_skipped_korean_message(self) -> None:
        # republish_orchestrator.start_republish 의 실제 메시지는 한국어.
        # codex review 2 반영 — 실제 운영 메시지 기준으로 회귀.
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.republish_orchestrator,
                "start_republish",
                side_effect=RuntimeError("이미 진행 중인 재발행 작업이 있습니다: p1"),
            ),
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="republished")
        assert len(result.skipped) == 1
        assert "이미 진행" in (result.skipped[0].message or "")

    def test_republish_active_job_conflict_english_message_also_skipped(self) -> None:
        # 영문 메시지로 바뀔 가능성에 대비한 키워드 매칭 회귀.
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.republish_orchestrator,
                "start_republish",
                side_effect=RuntimeError("active job already exists"),
            ),
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="republished")
        assert len(result.skipped) == 1

    def test_republish_non_active_runtime_error_is_failed(self) -> None:
        # codex review 반영: active job 이외의 RuntimeError 는 failed (인프라 오류)
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.republish_orchestrator,
                "start_republish",
                side_effect=RuntimeError("draft publication insert 실패"),
            ),
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="republished")
        assert len(result.failed) == 1
        assert "draft publication" in (result.failed[0].message or "")

    def test_hold_routes_to_publication_actions_orchestrator(self) -> None:
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.publication_actions_orchestrator,
                "hold",
                return_value=_pub("p1"),
            ) as hold,
            patch.object(board, "_record_user_action") as record,
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="held")
        hold.assert_called_once()
        record.assert_called_once_with("d-1", "held")
        assert len(result.succeeded) == 1

    def test_hold_when_publication_missing_in_orchestrator_is_failed(self) -> None:
        # workflow 재검증은 통과(action_required)했지만, hold 도중 publication 사라진 케이스
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(board.publication_actions_orchestrator, "hold", return_value=None),
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="held")
        assert len(result.failed) == 1
        assert "publication 미존재" in (result.failed[0].message or "")

    def test_dismiss_routes_correctly(self) -> None:
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(_pub("p1")),
            patch.object(
                board.publication_actions_orchestrator,
                "dismiss",
                return_value=_pub("p1"),
            ) as dismiss,
            patch.object(board, "_record_user_action"),
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="dismissed")
        dismiss.assert_called_once()
        assert len(result.succeeded) == 1

    def test_skips_when_workflow_status_not_action_required(self) -> None:
        # codex review 반영: 보드 조회 후 stale 또는 직접 API 호출 시 차단
        diag = _diag("p1", diag_id="d-1")
        stale_pub = _pub("p1", workflow_status="held")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(stale_pub),
            patch.object(board.publication_actions_orchestrator, "hold") as hold,
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="held")
        hold.assert_not_called()
        assert len(result.skipped) == 1
        assert "stale workflow_status" in (result.skipped[0].message or "")

    def test_skips_when_workflow_already_dismissed(self) -> None:
        # held / dismissed 이미 같은 상태인 publication 은 일괄 액션 부적절 —
        # workflow_status != action_required 분기로 흡수되어 skipped (stale 메시지).
        diag = _diag("p1", diag_id="d-1")
        already = _pub("p1", workflow_status="dismissed")
        with (
            _patch_load_diagnoses([diag]),
            _patch_get_publication(already),
            patch.object(board.publication_actions_orchestrator, "dismiss") as dismiss,
        ):
            result = board.execute_bulk_action(diagnosis_ids=["d-1"], action="dismissed")
        dismiss.assert_not_called()
        assert len(result.skipped) == 1
        assert "stale" in (result.skipped[0].message or "")

    def test_mark_competitor_only_records_user_action(self) -> None:
        # mark_competitor 는 publication workflow 변경 X — get_publication 도 호출 안 함
        diag = _diag("p1", diag_id="d-1")
        with (
            _patch_load_diagnoses([diag]),
            patch.object(board, "_record_user_action") as record,
            patch.object(board.republish_orchestrator, "start_republish") as start,
            patch.object(board.publication_actions_orchestrator, "hold") as hold,
            patch.object(board.publication_actions_orchestrator, "dismiss") as dismiss,
            patch.object(board.ranking_storage, "get_publication") as get_pub,
        ):
            result = board.execute_bulk_action(
                diagnosis_ids=["d-1"], action="marked_competitor_strong"
            )
        record.assert_called_once_with("d-1", "marked_competitor_strong")
        start.assert_not_called()
        hold.assert_not_called()
        dismiss.assert_not_called()
        get_pub.assert_not_called()  # mark_competitor 는 workflow 재검증 우회
        assert len(result.succeeded) == 1

    def test_mark_competitor_idempotent_when_same_state(self) -> None:
        diag = _diag("p1", diag_id="d-1")
        diag.user_action = "marked_competitor_strong"
        with (
            _patch_load_diagnoses([diag]),
            patch.object(board, "_record_user_action") as record,
        ):
            result = board.execute_bulk_action(
                diagnosis_ids=["d-1"], action="marked_competitor_strong"
            )
        record.assert_not_called()
        assert len(result.skipped) == 1

    def test_missing_diagnosis_is_failed(self) -> None:
        with _patch_load_diagnoses([]):
            result = board.execute_bulk_action(diagnosis_ids=["d-missing"], action="held")
        assert len(result.failed) == 1
        assert "stale" in (result.failed[0].message or "")

    def test_partial_failure_separates_buckets(self) -> None:
        d_ok = _diag("p1", diag_id="d-ok")
        d_conflict = _diag("p2", diag_id="d-conflict")
        d_infra = _diag("p3", diag_id="d-infra")
        # get_publication 은 모두 action_required → workflow 재검증 통과
        with (
            _patch_load_diagnoses([d_ok, d_conflict, d_infra]),
            patch.object(
                board.ranking_storage,
                "get_publication",
                side_effect=lambda pid: _pub(pid),
            ),
            patch.object(
                board.republish_orchestrator,
                "start_republish",
                side_effect=[
                    {"pipeline_job_id": "j1"},
                    RuntimeError("이미 진행 중인 재발행 작업이 있습니다: p2"),
                    RuntimeError("supabase 5xx"),
                ],
            ),
        ):
            result = board.execute_bulk_action(
                diagnosis_ids=["d-ok", "d-conflict", "d-infra"], action="republished"
            )
        assert result.total == 3
        assert [it.diagnosis_id for it in result.succeeded] == ["d-ok"]
        assert [it.diagnosis_id for it in result.skipped] == ["d-conflict"]
        assert [it.diagnosis_id for it in result.failed] == ["d-infra"]


# ── 단일 출처 회귀 ────────────────────────────────────────────────────────


class TestSingleSourceOfTruth:
    def test_valid_actions_match_user_action_literal(self) -> None:
        # backend Literal UserAction 과 application 의 _VALID_ACTIONS 가 동일해야
        # 진단 보드의 action 라우팅이 정상 동작한다.
        literal_actions = set(get_args(UserAction))
        valid_actions = set(board._VALID_ACTIONS)
        assert literal_actions == valid_actions

    def test_backend_literal_matches_frontend_keys(self) -> None:
        # codex review 반영: backend Literal UserAction 과 frontend
        # DIAGNOSIS_ACTION_KEYS 가 일치하지 않으면 UI 가 보내는 action 이 백엔드
        # 라우팅에서 거부되거나 그 반대 현상이 발생한다. 정규식으로 frontend
        # 파일을 직접 파싱해 양쪽을 cross-check 한다.
        import re
        from pathlib import Path

        labels_path = (
            Path(__file__).resolve().parents[2] / "web" / "frontend" / "src" / "lib" / "labels.ts"
        )
        text = labels_path.read_text(encoding="utf-8")
        match = re.search(r"DIAGNOSIS_ACTION_KEYS\s*=\s*\[(.*?)\]", text, re.DOTALL)
        assert match is not None, "DIAGNOSIS_ACTION_KEYS 가 labels.ts 에 정의되어 있어야 함"
        frontend_keys = set(re.findall(r'"([^"]+)"', match.group(1)))
        literal_actions = set(get_args(UserAction))
        assert literal_actions == frontend_keys, (
            f"backend↔frontend action key 불일치: "
            f"backend(UserAction)={literal_actions}, frontend={frontend_keys}"
        )
