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


@pytest.fixture(autouse=True)
def keyword_difficulty_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    from application import keyword_difficulty_orchestrator

    diff = MagicMock()
    diff.id = "kd-1"
    analyze_mock = MagicMock(return_value=diff)
    monkeypatch.setattr(keyword_difficulty_orchestrator, "analyze_keyword", analyze_mock)
    return analyze_mock


@pytest.fixture(autouse=True)
def generated_content_client_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    import config.supabase as supabase_config

    client = MagicMock()
    table = client.table.return_value
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(supabase_config, "get_client", lambda: client)
    return client


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

    def test_external_url_rejected(self, storage_mock: MagicMock) -> None:
        """정식 등록은 네이버 블로그 URL 만 허용 (측정 매칭 정합성). 외부 URL 거부."""
        with pytest.raises(ValueError, match="네이버 블로그 포스트 URL"):
            ranking_orchestrator.register_publication(
                keyword="kw", slug="s", url="https://tistory.com/foo"
            )
        storage_mock.insert_publication.assert_not_called()

    def test_draft_publication_when_url_none(self, storage_mock: MagicMock) -> None:
        """url=None 은 draft publication 생성 (재발행 임시 등)."""
        storage_mock.insert_publication.return_value = _publication(url=None, slug=None)
        ranking_orchestrator.register_publication(keyword="kw", url=None)
        passed = storage_mock.insert_publication.call_args.args[0]
        assert passed.url is None
        assert passed.workflow_status == "draft"
        assert passed.visibility_status == "not_measured"

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

    def test_attaches_keyword_difficulty_for_published_url(
        self,
        storage_mock: MagicMock,
        keyword_difficulty_mock: MagicMock,
        generated_content_client_mock: MagicMock,
    ) -> None:
        publication = _publication()
        storage_mock.insert_publication.return_value = publication

        ranking_orchestrator.register_publication(
            keyword="kw", slug="s", url="https://blog.naver.com/u/123456789"
        )

        keyword_difficulty_mock.assert_called_once_with("kw", persist=True)
        storage_mock.update_publication_keyword_difficulty.assert_called_once_with("pub-1", "kd-1")
        generated_content_client_mock.table.assert_called_with("generated_contents")

    def test_draft_does_not_attach_keyword_difficulty(self, storage_mock: MagicMock) -> None:
        storage_mock.insert_publication.return_value = _publication(url=None, slug=None)

        ranking_orchestrator.register_publication(keyword="kw", url=None)

        storage_mock.update_publication_keyword_difficulty.assert_not_called()


class TestBulkRegisterPublications:
    def test_creates_skips_and_fails(self, storage_mock: MagicMock) -> None:
        # 1번째: 신규 등록 / 2번째: 중복 / 3번째: URL 형식 위반 / 4번째: 키워드 누락
        # storage.get_publication_by_url 사용해 사전 중복 체크
        existing = _publication(id="existing-pub", url="https://m.blog.naver.com/u/200000002")

        def fake_get_by_url(url: str) -> Publication | None:
            return existing if "200000002" in url else None

        storage_mock.get_publication_by_url.side_effect = fake_get_by_url
        storage_mock.insert_publication.side_effect = lambda p: _publication(
            id="new-pub", url=p.url, keyword=p.keyword
        )

        items = [
            {"keyword": "kw1", "url": "https://blog.naver.com/u/100000001"},
            {"keyword": "kw2", "url": "https://blog.naver.com/u/200000002"},  # 중복
            {"keyword": "kw3", "url": "https://tistory.com/x"},  # 형식 위반
            {"keyword": "", "url": "https://blog.naver.com/u/300000003"},  # 키워드 누락
        ]

        result = ranking_orchestrator.bulk_register_publications(items)

        assert len(result["created"]) == 1
        assert result["created"][0]["index"] == 0
        assert len(result["skipped"]) == 1
        assert result["skipped"][0]["index"] == 1
        assert result["skipped"][0]["existing_publication_id"] == "existing-pub"
        assert len(result["failed"]) == 2
        assert result["failed"][0]["index"] == 2
        assert "네이버 블로그" in result["failed"][0]["reason"]
        assert result["failed"][1]["index"] == 3
        assert "키워드 누락" in result["failed"][1]["reason"]

    def test_empty_items(self, storage_mock: MagicMock) -> None:
        result = ranking_orchestrator.bulk_register_publications([])
        assert result == {"created": [], "skipped": [], "failed": []}
        storage_mock.insert_publication.assert_not_called()


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
        with pytest.raises(ValueError, match="URL 형식"):
            ranking_orchestrator.update_publication("pub-1", url="")
        storage_mock.update_publication.assert_not_called()

    def test_draft_auto_activates_on_url_registration(
        self, storage_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """재발행 자식 draft 가 URL 등록 시 active 로 자동 전이 + 액션 기록."""
        storage_mock.get_publication.return_value = _publication(url=None, workflow_status="draft")
        storage_mock.update_publication.return_value = _publication(workflow_status="draft")
        storage_mock.update_publication_workflow_state.return_value = _publication(
            workflow_status="active"
        )
        actions_mock = MagicMock()
        monkeypatch.setattr(
            "domain.ranking.publication_actions.insert_action",
            actions_mock,
        )

        result = ranking_orchestrator.update_publication(
            "pub-1", url="https://blog.naver.com/u/123456789"
        )

        assert result is not None and result.workflow_status == "active"
        actions_mock.assert_called_once()
        action_arg = actions_mock.call_args.args[0]
        assert action_arg.action == "url_registered"
        storage_mock.update_publication_workflow_state.assert_called_once_with(
            "pub-1", workflow_status="active"
        )

    def test_draft_activation_attaches_keyword_difficulty(
        self, storage_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        storage_mock.get_publication.return_value = _publication(url=None, workflow_status="draft")
        storage_mock.update_publication.return_value = _publication(workflow_status="draft")
        activated = _publication(workflow_status="active")
        storage_mock.update_publication_workflow_state.return_value = activated
        monkeypatch.setattr(
            "domain.ranking.publication_actions.insert_action",
            MagicMock(),
        )

        ranking_orchestrator.update_publication("pub-1", url="https://blog.naver.com/u/123456789")

        storage_mock.update_publication_keyword_difficulty.assert_called_once_with("pub-1", "kd-1")

    def test_active_publication_url_change_keeps_status(
        self, storage_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """이미 active 인 publication 의 URL 변경은 status 전이·액션 기록 없음."""
        storage_mock.get_publication.return_value = _publication(workflow_status="active")
        storage_mock.update_publication.return_value = _publication(workflow_status="active")
        actions_mock = MagicMock()
        monkeypatch.setattr(
            "domain.ranking.publication_actions.insert_action",
            actions_mock,
        )

        ranking_orchestrator.update_publication("pub-1", url="https://blog.naver.com/u/999999999")

        actions_mock.assert_not_called()
        storage_mock.update_publication_workflow_state.assert_not_called()


class TestKeywordDifficultyAttach:
    def test_attach_analyzes_and_links_snapshot(
        self, storage_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from application import keyword_difficulty_orchestrator

        diff = MagicMock()
        diff.id = "kd-1"
        analyze_mock = MagicMock(return_value=diff)
        monkeypatch.setattr(keyword_difficulty_orchestrator, "analyze_keyword", analyze_mock)

        ranking_orchestrator._ensure_keyword_difficulty_attached(_publication())

        analyze_mock.assert_called_once_with("kw", persist=True)
        storage_mock.update_publication_keyword_difficulty.assert_called_once_with("pub-1", "kd-1")

    def test_attach_skips_existing_snapshot(self, storage_mock: MagicMock) -> None:
        publication = _publication(keyword_difficulty_snapshot_id="kd-existing")

        ranking_orchestrator._ensure_keyword_difficulty_attached(publication)

        storage_mock.update_publication_keyword_difficulty.assert_not_called()

    def test_attach_generated_content_prefers_job_id(
        self, generated_content_client_mock: MagicMock
    ) -> None:
        ranking_orchestrator._attach_generated_content(_publication(job_id="job-1", slug="slug-1"))

        table = generated_content_client_mock.table.return_value
        table.update.return_value.eq.assert_called_once_with("job_id", "job-1")

    def test_attach_generated_content_falls_back_to_slug(
        self, generated_content_client_mock: MagicMock
    ) -> None:
        ranking_orchestrator._attach_generated_content(_publication(job_id=None, slug="slug-1"))

        table = generated_content_client_mock.table.return_value
        table.update.return_value.eq.assert_called_once_with("slug", "slug-1")


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
            section="VIEW",
            position=15,
            captured_at=datetime(2026, 4, 10, 0, 0, tzinfo=kst),
        )
        s2 = RankingSnapshot(
            publication_id="pub-1",
            section="인플루언서",
            position=8,
            captured_at=datetime(2026, 4, 10, 10, 0, tzinfo=kst),
        )
        s3 = RankingSnapshot(
            publication_id="pub-2",
            section=None,
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
        cell = row1.days["2026-04-10"]
        assert cell.position == 8  # 마지막 측정값
        assert cell.section == "인플루언서"
        row2 = next(r for r in cal.rows if r.publication.id == "pub-2")
        cell2 = row2.days["2026-04-11"]
        assert cell2.position is None  # 미노출
        assert cell2.section is None

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

    def test_records_brightdata_usage(
        self,
        storage_mock: MagicMock,
        brightdata_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SERP fetch 시 BrightData usage 가 Supabase api_usage 에 저장된다."""
        from domain.common.usage import ApiUsage, record_usage

        storage_mock.get_publication.return_value = _publication()
        snap = RankingSnapshot(publication_id="pub-1", position=3, total_results=10)
        monkeypatch.setattr(
            ranking_orchestrator.tracker,
            "find_position",
            lambda **_: snap,
        )
        storage_mock.insert_snapshot.return_value = snap

        # fetch 가 record_usage 를 호출하도록 모방 (find_position 이 monkeypatch 되어 html 내용 무관)
        def fetch_with_usage(url: str) -> str:
            record_usage(ApiUsage(provider="brightdata", model="web_unlocker"))
            return "<html></html>"

        brightdata_mock.fetch.side_effect = fetch_with_usage

        save_mock = MagicMock(return_value=True)
        monkeypatch.setattr(ranking_orchestrator, "save_usage_to_supabase", save_mock)

        ranking_orchestrator.check_rankings_for_publication("pub-1")
        save_mock.assert_called_once()
        _, kwargs = save_mock.call_args
        assert kwargs["stage"] == "ranking_check"


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

    def test_usage_save_failures_propagate_to_summary(
        self,
        storage_mock: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """save_usage_to_supabase 실패가 RankingCheckSummary 의
        usage_save_failed_count 로 전파되어야 한다 — 2026-05-02 silent failure
        사고 회귀 방지."""
        storage_mock.list_publications.return_value = [
            _publication(id="p1"),
            _publication(id="p2", url="https://m.blog.naver.com/u/222222222"),
        ]

        # 카운터를 먼저 reset 한 뒤 두 번 실패 기록 → check_all 이 reset 후 재시작
        ranking_orchestrator._reset_check_all_counters()

        def fake_check(_id: str) -> RankingSnapshot:
            # 실제 저장 실패를 시뮬레이션 — 측정은 성공했지만 usage 저장만 실패
            ranking_orchestrator._record_usage_save_failure()
            return RankingSnapshot(publication_id=_id, position=1)

        monkeypatch.setattr(ranking_orchestrator, "check_rankings_for_publication", fake_check)
        monkeypatch.setattr(ranking_orchestrator.settings, "ranking_check_sleep_seconds", 0.0)

        summary = ranking_orchestrator.check_all_active_rankings()
        assert summary.checked_count == 2
        assert summary.usage_save_failed_count == 2
        # 측정 자체는 정상이므로 errors_count 와 분리되어 노출
        assert summary.errors_count == 0


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
