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
    build_blog_tab_serp_url,
    build_integrated_serp_url,
    collect_serp,
)


class StubClient:
    """모든 fetch 호출에 동일한 HTML 을 반환. 통합검색과 블로그 탭 모두 같은 결과."""

    def __init__(self, html: str) -> None:
        self._html = html
        self.fetch_calls: list[str] = []

    def fetch(self, url: str) -> str:
        self.fetch_calls.append(url)
        return self._html

    def close(self) -> None:
        pass


class TrackStubClient:
    """통합검색/블로그 탭 URL 을 구분해 다른 HTML 을 반환."""

    def __init__(self, integrated_html: str, blog_tab_html: str) -> None:
        self._integrated = integrated_html
        self._blog_tab = blog_tab_html
        self.fetch_calls: list[str] = []

    def fetch(self, url: str) -> str:
        self.fetch_calls.append(url)
        if "ssc=tab.blog.all" in url:
            return self._blog_tab
        return self._integrated

    def close(self) -> None:
        pass


def test_build_integrated_serp_url_encodes_keyword() -> None:
    url = build_integrated_serp_url("강남 다이어트 한의원")
    assert url.startswith("https://search.naver.com/search.naver?")
    assert "where=blog" in url
    assert "ssc=tab.blog.all" not in url
    assert "%EA%B0%95%EB%82%A8" in url  # 강남 URL 인코딩


def test_build_blog_tab_serp_url() -> None:
    url = build_blog_tab_serp_url("k")
    assert "ssc=tab.blog.all" in url
    assert "start=1" in url
    assert "where=blog" not in url


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


def _html_with_posts(prefix: str, count: int) -> str:
    """테스트용 HTML 생성 — prefix 가 다른 고유 URL N개."""
    anchors = "".join(
        f'<a href="https://blog.naver.com/{prefix}{i}/10000000{i:02d}">p{i}</a>'
        for i in range(count)
    )
    return f"<html><body>{anchors}</body></html>"


def test_collect_serp_uses_integrated_first_skips_blog_tab_when_full() -> None:
    """통합검색에서 MAX_RESULTS(10) 가 충족되면 블로그 탭은 호출 안 한다."""
    integrated = _html_with_posts("int", 12)
    blog_tab = _html_with_posts("tab", 40)
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert len(result.results) == 10
    assert len(client.fetch_calls) == 1  # 블로그 탭 fetch 없음
    assert all(r.source == "integrated" for r in result.results)


def test_collect_serp_boosts_from_blog_tab_when_integrated_short() -> None:
    """통합 4개 + 블로그 탭 5개 보충 = 총 9개. source 필드 구분 확인."""
    integrated = _html_with_posts("int", 4)
    blog_tab = _html_with_posts("tab", 40)
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert len(result.results) == 9  # 4 + BLOG_TAB_BOOST_LIMIT(5)
    assert len(client.fetch_calls) == 2
    integrated_items = [r for r in result.results if r.source == "integrated"]
    blog_tab_items = [r for r in result.results if r.source == "blog_tab"]
    assert len(integrated_items) == 4
    assert len(blog_tab_items) == 5
    # 통합검색이 rank 앞쪽(1~4), 블로그 탭이 뒤쪽(5~9)
    assert [r.rank for r in integrated_items] == [1, 2, 3, 4]
    assert [r.rank for r in blog_tab_items] == [5, 6, 7, 8, 9]


def test_collect_serp_blog_tab_boost_capped_by_limit() -> None:
    """블로그 탭에 아무리 많아도 BLOG_TAB_BOOST_LIMIT(5) 까지만 가져온다."""
    integrated = _html_with_posts("int", 2)
    blog_tab = _html_with_posts("tab", 40)
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert len(result.results) == 7  # 2 + 5 cap
    assert sum(r.source == "blog_tab" for r in result.results) == 5


def test_collect_serp_blog_tab_boost_respects_remaining_slots() -> None:
    """통합 8개일 때 블로그 탭 보충은 2개만 (MAX_RESULTS-통합=2)."""
    integrated = _html_with_posts("int", 8)
    blog_tab = _html_with_posts("tab", 40)
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    assert len(result.results) == 10
    assert sum(r.source == "integrated" for r in result.results) == 8
    assert sum(r.source == "blog_tab" for r in result.results) == 2


def test_collect_serp_dedup_across_tracks() -> None:
    """통합검색 URL 이 블로그 탭에도 있으면 블로그 탭 쪽에서 skip."""
    shared = '<a href="https://blog.naver.com/shared/100000001">s</a>'
    integrated = f"<html><body>{shared}{_html_with_posts('int', 3).split('<body>')[1].split('</body>')[0]}</body></html>"
    blog_tab = f"<html><body>{shared}{_html_with_posts('tab', 10).split('<body>')[1].split('</body>')[0]}</body></html>"
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    result = collect_serp("테스트", client)  # type: ignore[arg-type]

    urls = [str(r.url) for r in result.results]
    assert urls.count("https://blog.naver.com/shared/100000001") == 1
    # 통합에서 shared 차지 → source=integrated 로 기록
    shared_item = next(r for r in result.results if "shared" in str(r.url))
    assert shared_item.source == "integrated"


def test_collect_serp_boost_still_insufficient_raises() -> None:
    """통합 2개 + 블로그 탭에도 3개만 있으면 합 5 < 7 → InsufficientCollectionError."""
    integrated = _html_with_posts("int", 2)
    blog_tab = _html_with_posts("tab", 3)
    client = TrackStubClient(integrated_html=integrated, blog_tab_html=blog_tab)

    with pytest.raises(InsufficientCollectionError) as exc_info:
        collect_serp("테스트", client)  # type: ignore[arg-type]

    assert exc_info.value.actual == 5
    assert exc_info.value.stage == "serp"


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
