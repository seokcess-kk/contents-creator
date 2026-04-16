"""SERP collector 단위 테스트.

Bright Data 호출은 실제 수행하지 않고 stub client 를 주입한다.
"""

from __future__ import annotations

import pytest

from domain.crawler.model import InsufficientCollectionError
from domain.crawler.serp_collector import (
    _is_ad_context,
    _normalize_href,
    _parse_serp_html,
    build_serp_url,
    collect_serp,
)


class StubClient:
    """모든 fetch 호출에 동일한 HTML 을 반환 (페이지 구분 안 함)."""

    def __init__(self, html: str) -> None:
        self._html = html
        self.fetch_calls: list[str] = []

    def fetch(self, url: str) -> str:
        self.fetch_calls.append(url)
        return self._html

    def close(self) -> None:
        pass


def test_build_serp_url_encodes_keyword() -> None:
    url = build_serp_url("강남 다이어트 한의원")
    assert url.startswith("https://search.naver.com/search.naver?")
    assert "ssc=tab.blog.all" in url
    assert "start=1" in url
    assert "%EA%B0%95%EB%82%A8" in url  # 강남 URL 인코딩


def test_build_serp_url_pagination() -> None:
    url = build_serp_url("k", start=11)
    assert "start=11" in url


class TestNormalizeHref:
    def test_accepts_desktop_blog_post(self) -> None:
        assert (
            _normalize_href("https://blog.naver.com/ssmaa/224246591163")
            == "https://blog.naver.com/ssmaa/224246591163"
        )

    def test_accepts_mobile_blog_post(self) -> None:
        assert (
            _normalize_href("https://m.blog.naver.com/foo/123456789")
            == "https://m.blog.naver.com/foo/123456789"
        )

    def test_rejects_clip_url(self) -> None:
        assert _normalize_href("https://blog.naver.com/clip/123") is None

    def test_rejects_user_home(self) -> None:
        assert _normalize_href("https://blog.naver.com/ssmaa") is None

    def test_rejects_non_naver(self) -> None:
        assert _normalize_href("https://other.com/blog/123456789") is None

    def test_rejects_short_post_id(self) -> None:
        # 9자리 미만 숫자
        assert _normalize_href("https://blog.naver.com/ssmaa/12345") is None

    def test_strips_query_and_fragment(self) -> None:
        assert (
            _normalize_href("https://blog.naver.com/ssmaa/224246591163?from=search#anchor")
            == "https://blog.naver.com/ssmaa/224246591163"
        )

    def test_protocol_relative(self) -> None:
        assert (
            _normalize_href("//blog.naver.com/ssmaa/224246591163")
            == "https://blog.naver.com/ssmaa/224246591163"
        )

    def test_empty(self) -> None:
        assert _normalize_href("") is None


def test_parse_serp_html_filters_and_deduplicates() -> None:
    html = """
    <html><body>
      <a href="https://blog.naver.com/alice/100000001">alice post</a>
      <a href="https://blog.naver.com/alice/100000001">alice post dup</a>
      <a href="https://m.blog.naver.com/bob/200000002">bob post</a>
      <a href="https://blog.naver.com/clip/999">clip</a>
      <a href="https://other.com/abc">outside</a>
      <a href="https://blog.naver.com/alice">user home</a>
    </body></html>
    """
    results = _parse_serp_html(html)
    urls = [str(r.url) for r in results]
    assert len(results) == 2
    assert "https://blog.naver.com/alice/100000001" in urls
    assert "https://m.blog.naver.com/bob/200000002" in urls
    # rank 은 1부터 오름차순
    assert [r.rank for r in results] == [1, 2]


def test_parse_serp_html_max_results_cap() -> None:
    anchors = "\n".join(
        f'<a href="https://blog.naver.com/user{i}/10000000{i:02d}">p{i}</a>' for i in range(15)
    )
    html = f"<html><body>{anchors}</body></html>"
    results = _parse_serp_html(html)
    assert len(results) == 10  # MAX_RESULTS


def test_parse_serp_html_reads_data_url_attr() -> None:
    """네이버 신버전 SERP 는 a[href] 대신 [data-url] 을 사용한다 (2026-04-16 실측)."""
    html = """
    <html><body>
      <button class="sp_button" data-url="https://blog.naver.com/ssmaa/224246591163">click</button>
      <div data-url="https://blog.naver.com/other/224246591164">other</div>
      <a href="https://blog.naver.com/legacy/224246591165">legacy anchor</a>
    </body></html>
    """
    results = _parse_serp_html(html)
    urls = [str(r.url) for r in results]
    assert len(results) == 3
    assert "https://blog.naver.com/ssmaa/224246591163" in urls
    assert "https://blog.naver.com/other/224246591164" in urls
    assert "https://blog.naver.com/legacy/224246591165" in urls


def test_parse_serp_html_prefers_href_over_data_url_when_both_present() -> None:
    """href 와 data-url 이 공존하면 href 가 우선 (정상 a 태그 케이스)."""
    html = '<a href="https://blog.naver.com/a/100000001" data-url="https://blog.naver.com/b/200000002">x</a>'
    results = _parse_serp_html(html)
    assert len(results) == 1
    assert str(results[0].url) == "https://blog.naver.com/a/100000001"


def test_parse_serp_html_skips_ads() -> None:
    html = """
    <html><body>
      <div class="sp_power_ad">
        <a href="https://blog.naver.com/ad/100000001">ad post</a>
      </div>
      <a href="https://blog.naver.com/clean/200000002">clean post</a>
    </body></html>
    """
    results = _parse_serp_html(html)
    urls = [str(r.url) for r in results]
    assert urls == ["https://blog.naver.com/clean/200000002"]


def test_collect_serp_raises_on_insufficient() -> None:
    # 3개만 있는 HTML → 7개 미만 → InsufficientCollectionError
    html = """
    <html><body>
      <a href="https://blog.naver.com/a/100000001">a</a>
      <a href="https://blog.naver.com/b/100000002">b</a>
      <a href="https://blog.naver.com/c/100000003">c</a>
    </body></html>
    """
    client = StubClient(html)

    with pytest.raises(InsufficientCollectionError) as exc_info:
        collect_serp("테스트", client)  # type: ignore[arg-type]

    assert exc_info.value.actual == 3
    assert exc_info.value.minimum == 7
    assert exc_info.value.stage == "serp"


def test_collect_serp_success_single_page() -> None:
    """1페이지만으로 MAX_RESULTS(10) 채워지면 추가 페이지 fetch 없이 종료."""
    anchors = "\n".join(
        f'<a href="https://blog.naver.com/user{i}/10000000{i:02d}">p{i}</a>' for i in range(12)
    )
    html = f"<html><body>{anchors}</body></html>"
    client = StubClient(html)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert result.keyword == "테스트"
    assert len(result.results) == 10  # MAX_RESULTS 캡
    assert len(client.fetch_calls) == 1  # 1페이지로 충족 → 2페이지 호출 없음


def test_collect_serp_deduplicates_urls() -> None:
    """단일 페이지 내 중복 URL 은 한 번만 카운트."""
    anchors = (
        '<a href="https://blog.naver.com/shared/100000001">s</a>'
        '<a href="https://blog.naver.com/shared/100000001">s dup</a>'
    ) + "".join(f'<a href="https://blog.naver.com/u{i}/10000000{i:02d}">p{i}</a>' for i in range(7))
    client = StubClient(f"<html><body>{anchors}</body></html>")

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    urls = [str(r.url) for r in result.results]
    assert urls.count("https://blog.naver.com/shared/100000001") == 1
    assert len(result.results) == 8


def test_is_ad_context_positive() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        '<div id="power_ad_container"><a href="x">ad</a></div>',
        "html.parser",
    )
    anchor = soup.find("a")
    assert anchor is not None
    assert _is_ad_context(anchor) is True


def test_is_ad_context_negative() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup('<div class="total_area"><a href="x">ok</a></div>', "html.parser")
    anchor = soup.find("a")
    assert anchor is not None
    assert _is_ad_context(anchor) is False
