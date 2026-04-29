"""keyword_difficulty_orchestrator 단위 테스트 — Bright Data + storage mock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from application.keyword_difficulty_orchestrator import (
    analyze_keyword,
    batch_analyze_keywords,
)
from domain.keyword_difficulty.cache import clear_cache
from domain.keyword_difficulty.model import DifficultyGrade


@pytest.fixture(autouse=True)
def _clear_serp_cache() -> None:
    """각 테스트 전후 SERP 캐시 비우기 (테스트 간 격리)."""
    clear_cache()
    yield
    clear_cache()


_FAKE_HTML = """
<html><body>
<div id="main_pack">
  <div class="sc_new ad_section">
    <h2>광고</h2>
    <ul class="lst_type"><li class="lst">a1</li><li class="lst">a2</li></ul>
  </div>
  <div class="sc_new">
    <h2>블로그</h2>
    <a href="https://blog.naver.com/u1/123456789">b1</a>
    <a href="https://blog.naver.com/u2/987654321">b2</a>
    <a href="https://blog.naver.com/u3/555555555">b3</a>
    <a href="https://blog.naver.com/u4/444444444">b4</a>
    <a href="https://blog.naver.com/u5/333333333">b5</a>
  </div>
</div>
</body></html>
"""


class TestAnalyzeKeyword:
    @patch("application.keyword_difficulty_orchestrator._safe_get_volume", return_value=None)
    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    def test_returns_keyword_difficulty(
        self, mock_insert: MagicMock, mock_volume: MagicMock
    ) -> None:
        client = MagicMock()
        client.fetch.return_value = _FAKE_HTML
        mock_insert.side_effect = lambda diff: diff

        result = analyze_keyword("테스트", client=client)
        assert result.keyword == "테스트"
        assert result.grade in {
            DifficultyGrade.MISSING,
            DifficultyGrade.HIGH,
            DifficultyGrade.MEDIUM,
            DifficultyGrade.LOW,
        }
        client.fetch.assert_called_once()
        mock_insert.assert_called_once()

    @patch("application.keyword_difficulty_orchestrator.save_usage_to_supabase")
    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    def test_records_brightdata_usage(
        self, mock_insert: MagicMock, mock_save_usage: MagicMock
    ) -> None:
        """BrightDataClient.fetch 의 자동 record_usage 가 Supabase 까지 저장된다."""
        from domain.common.usage import ApiUsage, record_usage

        client = MagicMock()

        def fetch_with_usage(url: str) -> str:
            # 실 BrightDataClient 가 fetch 후 record_usage 호출하는 동작 모방
            record_usage(ApiUsage(provider="brightdata", model="web_unlocker"))
            return _FAKE_HTML

        client.fetch.side_effect = fetch_with_usage
        mock_insert.side_effect = lambda diff: diff

        analyze_keyword("테스트", client=client)
        mock_save_usage.assert_called_once()
        _, kwargs = mock_save_usage.call_args
        assert kwargs["keyword"] == "테스트"
        assert kwargs["stage"] == "keyword_difficulty"

    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    def test_persist_false_skips_insert(self, mock_insert: MagicMock) -> None:
        client = MagicMock()
        client.fetch.return_value = _FAKE_HTML
        analyze_keyword("테스트", client=client, persist=False)
        mock_insert.assert_not_called()

    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    def test_storage_failure_does_not_raise(self, mock_insert: MagicMock) -> None:
        """저장 실패는 분석 결과 반환을 막지 않는다."""
        client = MagicMock()
        client.fetch.return_value = _FAKE_HTML
        mock_insert.side_effect = RuntimeError("supabase down")
        result = analyze_keyword("테스트", client=client)
        # 인-메모리 결과는 정상 반환
        assert result.keyword == "테스트"

    def test_fetch_failure_raises_serp_fetch_error(self) -> None:
        from domain.crawler.brightdata_client import BrightDataError
        from domain.keyword_difficulty.model import SerpFetchError

        client = MagicMock()
        client.fetch.side_effect = BrightDataError("network")

        try:
            analyze_keyword("테스트", client=client, persist=False)
        except SerpFetchError:
            pass
        else:
            raise AssertionError("SerpFetchError 가 발생해야 한다")


class TestBatchAnalyzeKeywords:
    @patch("application.keyword_difficulty_orchestrator._build_client")
    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    @patch("application.keyword_difficulty_orchestrator.time.sleep")
    def test_processes_all_keywords(
        self,
        mock_sleep: MagicMock,
        mock_insert: MagicMock,
        mock_build: MagicMock,
    ) -> None:
        client = MagicMock()
        client.fetch.return_value = _FAKE_HTML
        mock_build.return_value = client
        mock_insert.side_effect = lambda diff: diff

        keywords = ["k1", "k2", "k3"]
        results = batch_analyze_keywords(keywords, parallel=2)
        assert len(results) == 3
        assert {r.keyword for r in results} == set(keywords)

    @patch("application.keyword_difficulty_orchestrator._build_client")
    @patch("application.keyword_difficulty_orchestrator.storage.insert_snapshot")
    @patch("application.keyword_difficulty_orchestrator.time.sleep")
    def test_individual_failure_does_not_stop_batch(
        self,
        mock_sleep: MagicMock,
        mock_insert: MagicMock,
        mock_build: MagicMock,
    ) -> None:
        from domain.crawler.brightdata_client import BrightDataError

        client = MagicMock()

        def fetch_side(url: str) -> str:
            if "k2" in url:
                raise BrightDataError("network")
            return _FAKE_HTML

        client.fetch.side_effect = fetch_side
        mock_build.return_value = client
        mock_insert.side_effect = lambda diff: diff

        results = batch_analyze_keywords(["k1", "k2", "k3"])
        # k2 는 실패 → 결과에서 제외, k1/k3 만 성공
        assert len(results) == 2
        assert {r.keyword for r in results} == {"k1", "k3"}

    def test_empty_input_returns_empty(self) -> None:
        results = batch_analyze_keywords([])
        assert results == []
