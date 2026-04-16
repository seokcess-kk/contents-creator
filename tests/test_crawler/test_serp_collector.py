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
    assert url.startswith("https://search.naver.com/search.naver?query=")
    assert "where=blog" in url
    assert "%EA%B0%95%EB%82%A8" in url  # 강남 URL 인코딩


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


def test_collect_serp_success() -> None:
    anchors = "\n".join(
        f'<a href="https://blog.naver.com/user{i}/10000000{i:02d}">p{i}</a>' for i in range(8)
    )
    html = f"<html><body>{anchors}</body></html>"
    client = StubClient(html)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert result.keyword == "테스트"
    assert len(result.results) == 8
    assert client.fetch_calls == [build_serp_url("테스트")]


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
