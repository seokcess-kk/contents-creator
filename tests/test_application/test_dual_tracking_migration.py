"""dual_tracking_migration 단위 테스트 — storage/actions 모두 mock."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from application import dual_tracking_migration as mig
from domain.ranking.model import Publication


def _pub(
    pub_id: str,
    *,
    workflow_status: str = "active",
    url: str | None = "https://m.blog.naver.com/u/123",
    keyword: str = "kw",
) -> Publication:
    return Publication(
        id=pub_id,
        keyword=keyword,
        slug="s",
        url=url,
        workflow_status=workflow_status,
    )


@pytest.fixture
def storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(mig, "storage", mock)
    return mock


@pytest.fixture
def actions_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(mig, "actions_storage", mock)
    return mock


class TestCollectTargets:
    def test_classifies_republishing_and_draft_with_url(self, storage_mock: MagicMock) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p-1", workflow_status="republishing"),
            _pub("p-2", workflow_status="draft"),
            _pub("p-3", workflow_status="active"),  # 제외
            _pub("p-4", workflow_status="draft", url=None),  # url 없음 → 제외
            _pub("p-5", workflow_status="republishing", url=None),  # url 없음 → 제외
        ]
        targets = mig.collect_dual_tracking_targets()
        assert [p.id for p in targets["parents_to_activate"]] == ["p-1"]
        assert [p.id for p in targets["drafts_to_activate"]] == ["p-2"]

    def test_keyword_filter(self, storage_mock: MagicMock) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p-1", workflow_status="republishing", keyword="압구정"),
            _pub("p-2", workflow_status="republishing", keyword="대전"),
        ]
        targets = mig.collect_dual_tracking_targets(["압구정"])
        assert [p.id for p in targets["parents_to_activate"]] == ["p-1"]


class TestApplyMigration:
    def test_activates_parents_and_drafts(
        self, storage_mock: MagicMock, actions_mock: MagicMock
    ) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p-1", workflow_status="republishing"),
            _pub("p-2", workflow_status="draft"),
        ]
        counts = mig.apply_dual_tracking_migration()
        assert counts == {
            "parents_activated": 1,
            "drafts_activated": 1,
            "failed": 0,
        }
        # status 전이 2번 (parent + draft 각각)
        assert storage_mock.update_publication_workflow_state.call_count == 2
        # 액션 INSERT 2번
        assert actions_mock.insert_action.call_count == 2
        actions = [c.args[0].action for c in actions_mock.insert_action.call_args_list]
        assert "auto_requeued" in actions
        assert "url_registered" in actions

    def test_failure_counted_and_continues(
        self, storage_mock: MagicMock, actions_mock: MagicMock
    ) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p-1", workflow_status="republishing"),
            _pub("p-2", workflow_status="republishing"),
        ]
        actions_mock.insert_action.side_effect = [RuntimeError("DB hiccup"), None]
        counts = mig.apply_dual_tracking_migration()
        assert counts["parents_activated"] == 1
        assert counts["failed"] == 1

    def test_skips_pub_without_id(self, storage_mock: MagicMock, actions_mock: MagicMock) -> None:
        # id=None 인 row 는 (방어적으로) skip
        pub_no_id = Publication(
            keyword="kw",
            slug="s",
            url="https://m.blog.naver.com/u/123",
            workflow_status="republishing",
        )
        storage_mock.list_publications.return_value = [pub_no_id]
        counts = mig.apply_dual_tracking_migration()
        assert counts == {"parents_activated": 0, "drafts_activated": 0, "failed": 0}
        actions_mock.insert_action.assert_not_called()
