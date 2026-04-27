"""publication 운영 액션 (보류·해제·기각·복원·자동 큐 복귀) 단위 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from application import publication_actions_orchestrator as actions_orch
from domain.ranking.model import Publication


@pytest.fixture
def storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(actions_orch, "ranking_storage", mock)
    return mock


@pytest.fixture
def actions_storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(actions_orch, "actions_storage", mock)
    return mock


def _publication(**overrides: Any) -> Publication:
    base: dict[str, Any] = {
        "id": "pub-1",
        "keyword": "kw",
        "url": "https://m.blog.naver.com/u/123456789",
    }
    base.update(overrides)
    return Publication(**base)


class TestHold:
    def test_records_action_and_updates_state(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        storage_mock.get_publication.return_value = _publication()
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="held"
        )

        result = actions_orch.hold("pub-1", days=7, reason="경쟁 강도 높음")

        assert result is not None
        assert result.workflow_status == "held"
        # 히스토리 INSERT 우선
        actions_storage_mock.insert_action.assert_called_once()
        action_arg = actions_storage_mock.insert_action.call_args.args[0]
        assert action_arg.action == "held"
        assert action_arg.note == "경쟁 강도 높음"
        assert action_arg.metadata["days"] == 7
        # state 전이
        storage_mock.update_publication_workflow_state.assert_called_once()
        kwargs = storage_mock.update_publication_workflow_state.call_args.kwargs
        assert kwargs["workflow_status"] == "held"

    def test_returns_none_when_publication_missing(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        storage_mock.get_publication.return_value = None
        result = actions_orch.hold("pub-x", days=7)
        assert result is None
        actions_storage_mock.insert_action.assert_not_called()


class TestReleaseHold:
    def test_clears_held_and_requeues(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        storage_mock.get_publication.return_value = _publication(workflow_status="held")
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="action_required"
        )

        actions_orch.release_hold("pub-1")

        action_arg = actions_storage_mock.insert_action.call_args.args[0]
        assert action_arg.action == "released_hold"
        kwargs = storage_mock.update_publication_workflow_state.call_args.kwargs
        assert kwargs["workflow_status"] == "action_required"
        assert kwargs["clear_held"] is True


class TestDismiss:
    def test_records_and_transitions(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        storage_mock.get_publication.return_value = _publication()
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="dismissed"
        )

        result = actions_orch.dismiss("pub-1", reason="경쟁 너무 강함")

        action_arg = actions_storage_mock.insert_action.call_args.args[0]
        assert action_arg.action == "dismissed"
        assert action_arg.note == "경쟁 너무 강함"
        assert result is not None
        assert result.workflow_status == "dismissed"


class TestAutoRequeue:
    def test_records_with_metadata_trigger(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="action_required"
        )

        actions_orch.auto_requeue(
            "pub-1",
            trigger="republish_url_pending",
            note="재발행 후 7일 동안 새 URL 미등록",
        )

        action_arg = actions_storage_mock.insert_action.call_args.args[0]
        assert action_arg.action == "auto_requeued"
        assert action_arg.metadata["auto"] is True
        assert action_arg.metadata["trigger"] == "republish_url_pending"

    def test_hold_expired_clears_held(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        actions_orch.auto_requeue("pub-1", trigger="hold_expired", note="만료")
        kwargs = storage_mock.update_publication_workflow_state.call_args.kwargs
        assert kwargs["clear_held"] is True

    def test_other_trigger_keeps_held(
        self, storage_mock: MagicMock, actions_storage_mock: MagicMock
    ) -> None:
        actions_orch.auto_requeue("pub-1", trigger="republish_job_failed", note="x")
        kwargs = storage_mock.update_publication_workflow_state.call_args.kwargs
        assert kwargs["clear_held"] is False


class TestActionRecordIsBestEffort:
    def test_action_failure_does_not_block_state_transition(
        self,
        storage_mock: MagicMock,
        actions_storage_mock: MagicMock,
    ) -> None:
        """publication_actions INSERT 실패해도 status 전이는 진행 (logger 만 경고)."""
        storage_mock.get_publication.return_value = _publication()
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="held"
        )
        actions_storage_mock.insert_action.side_effect = RuntimeError("DB down")

        result = actions_orch.hold("pub-1", days=3)
        # state 전이는 실행됨 (best-effort 보장)
        assert result is not None
        storage_mock.update_publication_workflow_state.assert_called_once()
