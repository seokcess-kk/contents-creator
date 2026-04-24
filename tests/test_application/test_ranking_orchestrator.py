"""ranking_orchestrator 단위 테스트 — Bright Data + Supabase 모두 mock."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from application import ranking_orchestrator
from domain.ranking.model import (
    Publication,
    RankingDuplicateUrlError,
    RankingMatchError,
    RankingSnapshot,
)


@pytest.fixture
def storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(ranking_orchestrator, "storage", mock)
    return mock


@pytest.fixture
def brightdata_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """BrightDataClient 생성자 자체를 mock."""
    cls = MagicMock()
    instance = MagicMock()
    instance.fetch.return_value = "<html/>"
    instance.close.return_value = None
    cls.return_value = instance
    monkeypatch.setattr(ranking_orchestrator, "BrightDataClient", cls)
    monkeypatch.setattr(
        ranking_orchestrator,
        "require",
        lambda key: "test-value",
    )
    return instance


def _publication(**overrides: Any) -> Publication:
    base = {
        "id": "pub-1",
        "keyword": "kw",
        "slug": "kw-slug",
        "url": "https://m.blog.naver.com/u/123456789",
    }
    base.update(overrides)
    return Publication(**base)


class TestRegisterPublication:
    def test_inserts_new(self, storage_mock: MagicMock) -> None:
        storage_mock.insert_publication.return_value = _publication()
        result = ranking_orchestrator.register_publication(
            keyword="kw",
            slug="kw-slug",
            url="https://blog.naver.com/u/123456789",
        )
        assert result.id == "pub-1"
        storage_mock.insert_publication.assert_called_once()

    def test_duplicate_returns_existing(self, storage_mock: MagicMock) -> None:
        storage_mock.insert_publication.side_effect = RankingDuplicateUrlError("dup")
        existing = _publication(id="pub-existing")
        storage_mock.get_publication_by_url.return_value = existing

        result = ranking_orchestrator.register_publication(
            keyword="kw", slug="s", url="https://blog.naver.com/u/123456789"
        )
        assert result.id == "pub-existing"

    def test_invalid_url_rejected(self, storage_mock: MagicMock) -> None:
        with pytest.raises(ValueError, match="네이버 블로그"):
            ranking_orchestrator.register_publication(
                keyword="kw", slug="s", url="https://tistory.com/foo"
            )
        storage_mock.insert_publication.assert_not_called()

    def test_normalizes_to_mobile(self, storage_mock: MagicMock) -> None:
        storage_mock.insert_publication.return_value = _publication()
        ranking_orchestrator.register_publication(
            keyword="kw", slug="s", url="https://blog.naver.com/u/123456789"
        )
        passed = storage_mock.insert_publication.call_args.args[0]
        assert passed.url == "https://m.blog.naver.com/u/123456789"


class TestCheckRankingsForPublication:
    def test_publication_missing(self, storage_mock: MagicMock) -> None:
        storage_mock.get_publication.return_value = None
        with pytest.raises(ValueError, match="publication 미존재"):
            ranking_orchestrator.check_rankings_for_publication("pub-x")

    def test_finds_position_and_saves(
        self,
        storage_mock: MagicMock,
        brightdata_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage_mock.get_publication.return_value = _publication()
        # tracker.find_position 결과를 직접 주입
        snap = RankingSnapshot(publication_id="pub-1", position=3, total_results=10)
        monkeypatch.setattr(
            ranking_orchestrator.tracker,
            "find_position",
            lambda **_: snap,
        )
        storage_mock.insert_snapshot.return_value = snap

        result = ranking_orchestrator.check_rankings_for_publication("pub-1")
        assert result.position == 3
        # BrightData close 호출 보장
        brightdata_mock.close.assert_called_once()

    def test_match_error_propagates(
        self,
        storage_mock: MagicMock,
        brightdata_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage_mock.get_publication.return_value = _publication()

        def boom(**_: Any) -> RankingSnapshot:
            raise RankingMatchError("network")

        monkeypatch.setattr(ranking_orchestrator.tracker, "find_position", boom)

        with pytest.raises(RankingMatchError):
            ranking_orchestrator.check_rankings_for_publication("pub-1")
        brightdata_mock.close.assert_called_once()


class TestCheckAllActiveRankings:
    def test_iterates_all_publications(
        self,
        storage_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage_mock.list_publications.return_value = [
            _publication(id="p1"),
            _publication(id="p2", url="https://m.blog.naver.com/u/222222222"),
            _publication(id="p3", url="https://m.blog.naver.com/u/333333333"),
        ]

        # check_rankings_for_publication 을 직접 mock
        results = [
            RankingSnapshot(publication_id="p1", position=1),
            RankingSnapshot(publication_id="p2"),  # off-chart
            RankingSnapshot(publication_id="p3", position=10),
        ]
        results_iter = iter(results)
        monkeypatch.setattr(
            ranking_orchestrator,
            "check_rankings_for_publication",
            lambda _id: next(results_iter),
        )
        # sleep 시간 단축
        monkeypatch.setattr(ranking_orchestrator.settings, "ranking_check_sleep_seconds", 0.0)

        summary = ranking_orchestrator.check_all_active_rankings()
        assert summary.checked_count == 3
        assert summary.found_count == 2  # off-chart 1개 제외
        assert summary.errors_count == 0

    def test_individual_failure_isolated(
        self,
        storage_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage_mock.list_publications.return_value = [
            _publication(id="p1"),
            _publication(id="p2", url="https://m.blog.naver.com/u/222222222"),
        ]
        outcomes = [
            RankingMatchError("first failed"),
            RankingSnapshot(publication_id="p2", position=5),
        ]
        outcomes_iter = iter(outcomes)

        def fake_check(_id: str) -> RankingSnapshot:
            o = next(outcomes_iter)
            if isinstance(o, Exception):
                raise o
            return o

        monkeypatch.setattr(ranking_orchestrator, "check_rankings_for_publication", fake_check)
        monkeypatch.setattr(ranking_orchestrator.settings, "ranking_check_sleep_seconds", 0.0)

        summary = ranking_orchestrator.check_all_active_rankings()
        assert summary.checked_count == 1
        assert summary.found_count == 1
        assert summary.errors_count == 1


class TestParseSerpForRanking:
    def test_extracts_blog_post_urls(self) -> None:
        html = """
        <html><body>
          <a href="https://blog.naver.com/userA/100000001">A</a>
          <a href="https://m.blog.naver.com/userB/100000002">B</a>
          <a href="https://tistory.com/foo">other</a>
          <div data-url="https://blog.naver.com/userC/100000003"></div>
        </body></html>
        """
        items = ranking_orchestrator._parse_serp_for_ranking(html)
        assert len(items) == 3
        assert items[0].rank == 1
        assert items[2].rank == 3

    def test_dedupes_repeated_urls(self) -> None:
        html = """
        <html><body>
          <a href="https://blog.naver.com/userA/100000001">A</a>
          <a href="https://blog.naver.com/userA/100000001">A again</a>
        </body></html>
        """
        items = ranking_orchestrator._parse_serp_for_ranking(html)
        assert len(items) == 1


class TestGetPublicationTimeline:
    def test_returns_none_when_publication_missing(self, storage_mock: MagicMock) -> None:
        storage_mock.get_publication.return_value = None
        assert ranking_orchestrator.get_publication_timeline("pub-x") is None

    def test_combines_publication_and_snapshots(self, storage_mock: MagicMock) -> None:
        storage_mock.get_publication.return_value = _publication()
        storage_mock.list_snapshots.return_value = [
            RankingSnapshot(publication_id="pub-1", position=1),
            RankingSnapshot(publication_id="pub-1", position=3),
        ]
        timeline = ranking_orchestrator.get_publication_timeline("pub-1")
        assert timeline is not None
        assert timeline.publication.id == "pub-1"
        assert len(timeline.snapshots) == 2
