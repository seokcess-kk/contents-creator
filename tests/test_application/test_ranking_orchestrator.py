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

    def test_external_url_without_slug(self, storage_mock: MagicMock) -> None:
        """slug 생략 시 외부 URL 등록 — Publication.slug=None 으로 저장."""
        storage_mock.insert_publication.return_value = _publication(slug=None)
        result = ranking_orchestrator.register_publication(
            keyword="kw", url="https://blog.naver.com/u/123456789"
        )
        passed = storage_mock.insert_publication.call_args.args[0]
        assert passed.slug is None
        assert result.slug is None


class TestUpdatePublication:
    def test_partial_update(self, storage_mock: MagicMock) -> None:
        storage_mock.update_publication.return_value = _publication(keyword="new")
        result = ranking_orchestrator.update_publication("pub-1", keyword="new")
        assert result is not None
        assert result.keyword == "new"
        storage_mock.update_publication.assert_called_once_with(
            "pub-1", keyword="new", url=None, slug=None, published_at=None
        )

    def test_url_normalized_before_update(self, storage_mock: MagicMock) -> None:
        storage_mock.update_publication.return_value = _publication()
        ranking_orchestrator.update_publication("pub-1", url="https://blog.naver.com/u/123456789")
        assert (
            storage_mock.update_publication.call_args.kwargs["url"]
            == "https://m.blog.naver.com/u/123456789"
        )

    def test_invalid_url_rejected(self, storage_mock: MagicMock) -> None:
        with pytest.raises(ValueError, match="네이버 블로그"):
            ranking_orchestrator.update_publication("pub-1", url="https://tistory.com/x")
        storage_mock.update_publication.assert_not_called()


class TestDeletePublication:
    def test_returns_storage_result(self, storage_mock: MagicMock) -> None:
        storage_mock.delete_publication.return_value = True
        assert ranking_orchestrator.delete_publication("pub-1") is True
        storage_mock.delete_publication.assert_called_once_with("pub-1")


class TestGetMonthlyCalendar:
    def test_aggregates_by_pub_and_kst_day(self, storage_mock: MagicMock) -> None:
        from datetime import datetime, timedelta, timezone

        from domain.ranking.model import RankingSnapshot

        kst = timezone(timedelta(hours=9))
        # 동일 KST 일에 두 측정 — 마지막 측정(10시) 이 채택
        s1 = RankingSnapshot(
            publication_id="pub-1",
            position=15,
            captured_at=datetime(2026, 4, 10, 0, 0, tzinfo=kst),
        )
        s2 = RankingSnapshot(
            publication_id="pub-1",
            position=8,
            captured_at=datetime(2026, 4, 10, 10, 0, tzinfo=kst),
        )
        s3 = RankingSnapshot(
            publication_id="pub-2",
            position=None,
            captured_at=datetime(2026, 4, 11, 9, 0, tzinfo=kst),
        )
        storage_mock.list_snapshots_in_range.return_value = [s1, s2, s3]
        storage_mock.list_publications.return_value = [
            _publication(id="pub-1"),
            _publication(id="pub-2", slug=None),
        ]

        cal = ranking_orchestrator.get_monthly_calendar(2026, 4)
        assert cal.month == "2026-04"
        assert len(cal.rows) == 2
        row1 = next(r for r in cal.rows if r.publication.id == "pub-1")
        assert row1.days == {"2026-04-10": 8}
        row2 = next(r for r in cal.rows if r.publication.id == "pub-2")
        assert row2.days == {"2026-04-11": None}

    def test_invalid_month_raises(self, storage_mock: MagicMock) -> None:
        with pytest.raises(ValueError, match="월은 1~12"):
            ranking_orchestrator.get_monthly_calendar(2026, 13)
        storage_mock.list_snapshots_in_range.assert_not_called()

    def test_kst_boundary_to_utc(self, storage_mock: MagicMock) -> None:
        """KST 월 경계 — UTC 환산값을 storage 에 전달."""
        storage_mock.list_snapshots_in_range.return_value = []
        storage_mock.list_publications.return_value = []
        ranking_orchestrator.get_monthly_calendar(2026, 4)
        call = storage_mock.list_snapshots_in_range.call_args
        start_utc, end_utc = call.args[0], call.args[1]
        # 2026-04-01 00:00 KST == 2026-03-31 15:00 UTC
        assert start_utc.isoformat().startswith("2026-03-31T15:00")
        # 2026-05-01 00:00 KST == 2026-04-30 15:00 UTC
        assert end_utc.isoformat().startswith("2026-04-30T15:00")


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
