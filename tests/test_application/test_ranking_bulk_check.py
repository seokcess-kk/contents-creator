"""ranking_bulk_check — 측정 대상 필터 + 진행률 reporter 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from application import ranking_bulk_check
from domain.ranking.model import Publication, RankingMatchError, RankingSnapshot


def _pub(pub_id: str, **overrides: Any) -> Publication:
    base: dict[str, Any] = {
        "id": pub_id,
        "keyword": f"kw-{pub_id}",
        "url": f"https://m.blog.naver.com/u/{pub_id}",
        "workflow_status": "active",
    }
    base.update(overrides)
    return Publication(**base)


@pytest.fixture
def storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(ranking_bulk_check, "ranking_storage", mock)
    return mock


@pytest.fixture
def check_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """check_rankings_for_publication 결과를 통제."""
    mock = MagicMock()
    monkeypatch.setattr(
        ranking_bulk_check, "check_rankings_for_publication", mock
    )
    return mock


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """publication 간 1초 sleep 제거 (테스트 가속)."""
    monkeypatch.setattr(ranking_bulk_check.settings, "ranking_check_sleep_seconds", 0.0)


class TestResolveTargets:
    def test_excludes_url_none(self, storage_mock: MagicMock) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p1", url=None, workflow_status="active"),
            _pub("p2", workflow_status="active"),
        ]
        result = ranking_bulk_check._resolve_targets(None)
        assert [p.id for p in result] == ["p2"]

    def test_excludes_held_dismissed_republishing_draft(
        self, storage_mock: MagicMock
    ) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p1", workflow_status="active"),
            _pub("p2", workflow_status="held"),
            _pub("p3", workflow_status="dismissed"),
            _pub("p4", workflow_status="republishing"),
            _pub("p5", workflow_status="draft"),
            _pub("p6", workflow_status="action_required"),
        ]
        result = ranking_bulk_check._resolve_targets(None)
        assert sorted(p.id for p in result) == ["p1", "p6"]

    def test_publication_ids_filter(self, storage_mock: MagicMock) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p1"),
            _pub("p2"),
            _pub("p3"),
        ]
        result = ranking_bulk_check._resolve_targets(["p1", "p3", "p999"])
        assert sorted(p.id for p in result) == ["p1", "p3"]


class TestBulkCheckRankings:
    def test_aggregates_check_results(
        self, storage_mock: MagicMock, check_mock: MagicMock, no_sleep: None
    ) -> None:
        storage_mock.list_publications.return_value = [_pub("p1"), _pub("p2"), _pub("p3")]
        check_mock.side_effect = [
            RankingSnapshot(publication_id="p1", section="인플루언서", position=3),
            RankingSnapshot(publication_id="p2"),  # 미노출
            RankingSnapshot(publication_id="p3", section="VIEW", position=8),
        ]
        summary = ranking_bulk_check.bulk_check_rankings()
        assert summary.checked_count == 3
        assert summary.found_count == 2
        assert summary.errors_count == 0

    def test_failures_are_isolated(
        self, storage_mock: MagicMock, check_mock: MagicMock, no_sleep: None
    ) -> None:
        storage_mock.list_publications.return_value = [_pub("p1"), _pub("p2"), _pub("p3")]
        check_mock.side_effect = [
            RankingSnapshot(publication_id="p1", section="인플루언서", position=1),
            RankingMatchError("network down"),
            RankingSnapshot(publication_id="p3", section="VIEW", position=5),
        ]
        summary = ranking_bulk_check.bulk_check_rankings()
        assert summary.checked_count == 2
        assert summary.found_count == 2
        assert summary.errors_count == 1

    def test_reporter_progress_emitted(
        self, storage_mock: MagicMock, check_mock: MagicMock, no_sleep: None
    ) -> None:
        storage_mock.list_publications.return_value = [_pub("p1"), _pub("p2")]
        check_mock.side_effect = [
            RankingSnapshot(publication_id="p1", section="VIEW", position=2),
            RankingSnapshot(publication_id="p2"),
        ]
        reporter = MagicMock()
        ranking_bulk_check.bulk_check_rankings(reporter=reporter)
        reporter.stage_start.assert_called_once_with("ranking_bulk_check", total=2)
        assert reporter.stage_progress.call_count == 2
        reporter.stage_end.assert_called_once()

    def test_publication_ids_subset_only_measured(
        self, storage_mock: MagicMock, check_mock: MagicMock, no_sleep: None
    ) -> None:
        storage_mock.list_publications.return_value = [
            _pub("p1"),
            _pub("p2"),
            _pub("p3"),
        ]
        check_mock.return_value = RankingSnapshot(
            publication_id="p1", section="인플루언서", position=1
        )
        ranking_bulk_check.bulk_check_rankings(publication_ids=["p1"])
        assert check_mock.call_count == 1
        check_mock.assert_called_with("p1")
