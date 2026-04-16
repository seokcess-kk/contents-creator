"""Page scraper 단위 테스트."""

from __future__ import annotations

from datetime import datetime

import pytest

from domain.crawler.brightdata_client import BrightDataError
from domain.crawler.model import (
    InsufficientCollectionError,
    SerpResult,
    SerpResults,
)
from domain.crawler.page_scraper import normalize_to_mobile, scrape_pages


class StubClient:
    """urls → html 매핑 기반 stub. 매핑 없으면 BrightDataError 발생."""

    def __init__(self, mapping: dict[str, str], failing: set[str] | None = None) -> None:
        self._mapping = mapping
        self._failing = failing or set()
        self.fetch_calls: list[str] = []

    def fetch(self, url: str) -> str:
        self.fetch_calls.append(url)
        if url in self._failing:
            raise BrightDataError(f"stub failure: {url}")
        if url not in self._mapping:
            raise BrightDataError(f"stub unknown: {url}")
        return self._mapping[url]

    def close(self) -> None:
        pass


class TestNormalizeToMobile:
    def test_desktop_https(self) -> None:
        assert (
            normalize_to_mobile("https://blog.naver.com/ssmaa/224246591163")
            == "https://m.blog.naver.com/ssmaa/224246591163"
        )

    def test_desktop_http(self) -> None:
        assert (
            normalize_to_mobile("http://blog.naver.com/ssmaa/224246591163")
            == "https://m.blog.naver.com/ssmaa/224246591163"
        )

    def test_already_mobile(self) -> None:
        assert (
            normalize_to_mobile("https://m.blog.naver.com/ssmaa/224246591163")
            == "https://m.blog.naver.com/ssmaa/224246591163"
        )

    def test_mobile_http_upgraded(self) -> None:
        assert (
            normalize_to_mobile("http://m.blog.naver.com/ssmaa/224246591163")
            == "https://m.blog.naver.com/ssmaa/224246591163"
        )


def _make_serp(count: int) -> SerpResults:
    return SerpResults(
        keyword="테스트",
        collected_at=datetime.now().astimezone(),
        results=[
            SerpResult(
                rank=i + 1,
                url=f"https://blog.naver.com/u{i}/10000000{i:02d}",  # type: ignore[arg-type]
                title=f"post {i}",
            )
            for i in range(count)
        ],
    )


def test_scrape_pages_all_success(tmp_path: object) -> None:
    serp = _make_serp(8)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(8)
    }
    client = StubClient(mapping)

    result = scrape_pages(serp, client)  # type: ignore[arg-type]

    assert len(result.successful) == 8
    assert len(result.failed) == 0
    # 모든 호출이 모바일 URL 로 정규화됨
    for call in client.fetch_calls:
        assert call.startswith("https://m.blog.naver.com/")
    # idx 보존
    assert [p.idx for p in result.successful] == list(range(8))
    # html 내용 보존
    assert result.successful[0].html == "<html>body0</html>"


def test_scrape_pages_partial_failure_above_minimum() -> None:
    serp = _make_serp(9)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(9)
    }
    # 2개 실패 → 성공 7 = MIN_COLLECTED_PAGES 딱 맞음
    failing = {
        "https://m.blog.naver.com/u0/1000000000",
        "https://m.blog.naver.com/u1/1000000001",
    }
    client = StubClient(mapping, failing=failing)

    result = scrape_pages(serp, client)  # type: ignore[arg-type]

    assert len(result.successful) == 7
    assert len(result.failed) == 2
    assert {f.idx for f in result.failed} == {0, 1}


def test_scrape_pages_insufficient_raises() -> None:
    serp = _make_serp(8)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(8)
    }
    # 3개 실패 → 성공 5 < 7 → 예외
    failing = {f"https://m.blog.naver.com/u{i}/10000000{i:02d}" for i in range(3)}
    client = StubClient(mapping, failing=failing)

    with pytest.raises(InsufficientCollectionError) as exc_info:
        scrape_pages(serp, client)  # type: ignore[arg-type]

    assert exc_info.value.actual == 5
    assert exc_info.value.stage == "scrape"


def test_scrape_pages_preserves_original_desktop_url() -> None:
    """원본 URL(desktop) 은 BlogPage.url 에 그대로 보존되고,
    mobile_url 은 정규화된 URL 을 가진다."""
    serp = _make_serp(7)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(7)
    }
    client = StubClient(mapping)

    result = scrape_pages(serp, client)  # type: ignore[arg-type]

    for page in result.successful:
        assert "blog.naver.com" in str(page.url)  # 원본
        assert str(page.mobile_url).startswith("https://m.blog.naver.com/")
