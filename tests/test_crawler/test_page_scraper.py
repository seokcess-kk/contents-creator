"""Page scraper 단위 테스트."""

from __future__ import annotations

from datetime import datetime

import pytest

from domain.crawler.brightdata_client import BrightDataError
from domain.crawler.fallback_fetcher import FallbackFetcher
from domain.crawler.insane_fetcher import InsaneFetchError
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
    serp = _make_serp(7)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(7)
    }
    # 2개 실패 → 성공 5 = MIN_COLLECTED_PAGES 딱 맞음
    failing = {
        "https://m.blog.naver.com/u0/1000000000",
        "https://m.blog.naver.com/u1/1000000001",
    }
    client = StubClient(mapping, failing=failing)

    result = scrape_pages(serp, client)  # type: ignore[arg-type]

    assert len(result.successful) == 5
    assert len(result.failed) == 2
    assert {f.idx for f in result.failed} == {0, 1}


def test_scrape_pages_insufficient_raises() -> None:
    serp = _make_serp(8)
    mapping = {
        f"https://m.blog.naver.com/u{i}/10000000{i:02d}": f"<html>body{i}</html>" for i in range(8)
    }
    # 4개 실패 → 성공 4 < 5 → 예외
    failing = {f"https://m.blog.naver.com/u{i}/10000000{i:02d}" for i in range(4)}
    client = StubClient(mapping, failing=failing)

    with pytest.raises(InsufficientCollectionError) as exc_info:
        scrape_pages(serp, client)  # type: ignore[arg-type]

    assert exc_info.value.actual == 4
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


# ── RI-9 재시도 증폭 상호작용 (PR4 step21b) ──────────────────────────────────
#
# scrape_pages 의 1회 batch 재시도는 `_fetch_one` 을 다시 호출한다. 주입된 client 가
# FallbackFetcher 면 이 재시도가 **폴백 체인 전체(primary insane + fallback BrightData)를
# 다시 돈다**. 아래 테스트가 그 호출 카운트 증폭을 고정한다.


class _CountingFetcher:
    """호출 카운트 + url별 시나리오 기반 HtmlFetcher duck-type stub."""

    def __init__(
        self,
        *,
        always_fail: bool = False,
        fail_first_n: dict[str, int] | None = None,
        error: Exception | None = None,
        html: str = "<html>ok body content</html>",
    ) -> None:
        self.calls: list[str] = []
        self._always_fail = always_fail
        self._fail_first_n = dict(fail_first_n or {})
        self._error = error or BrightDataError("stub fail")
        self._html = html

    def fetch(self, url: str) -> str:
        self.calls.append(url)
        if self._always_fail:
            raise self._error
        remaining = self._fail_first_n.get(url, 0)
        if remaining > 0:
            self._fail_first_n[url] = remaining - 1
            raise self._error
        return self._html

    def close(self) -> None:
        pass

    def __enter__(self) -> _CountingFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_batch_retry_reruns_full_fallback_chain() -> None:
    """지속 실패 URL 1건 → primary 2회(초기 1 + batch 재시도 1) + fallback 2회."""
    serp = _make_serp(1)
    primary = _CountingFetcher(always_fail=True, error=InsaneFetchError("primary down"))
    fallback = _CountingFetcher(always_fail=True, error=BrightDataError("fallback down"))
    client = FallbackFetcher(primary, fallback)  # type: ignore[arg-type]

    # 성공 0 < MIN_COLLECTED_PAGES → batch 재시도 후에도 미달 → 예외.
    with pytest.raises(InsufficientCollectionError):
        scrape_pages(serp, client)  # type: ignore[arg-type]

    # 재시도 증폭: client.fetch 2회 × (primary 1 + fallback 1) = 각 2회.
    assert len(primary.calls) == 2
    assert len(fallback.calls) == 2


def test_batch_retry_recovers_via_fallback() -> None:
    """primary 전건 실패(폴백 강제) + 일부 URL 이 batch 재시도로 회복 → 예외 미발생."""
    serp = _make_serp(6)
    urls = [normalize_to_mobile(str(r.url)) for r in serp.results]
    primary = _CountingFetcher(always_fail=True, error=InsaneFetchError("primary down"))
    # 2개 URL 은 초기엔 fallback 도 실패 → 초기 성공 4 < 5 로 batch 재시도 유발.
    # batch 재시도에서 fail_first_n 소진 → 성공 회복 → 총 6 성공.
    fallback = _CountingFetcher(fail_first_n={urls[0]: 1, urls[1]: 1})
    client = FallbackFetcher(primary, fallback)  # type: ignore[arg-type]

    result = scrape_pages(serp, client)  # type: ignore[arg-type]

    assert len(result.successful) == 6
    assert len(result.failed) == 0
    # primary 는 매 client.fetch 마다 호출: 초기 6 + 재시도 2 = 8회.
    assert len(primary.calls) == 8
