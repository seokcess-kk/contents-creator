"""url_match 단위 테스트."""

from __future__ import annotations

import pytest

from domain.ranking.url_match import (
    BLOG_POST_URL_RE,
    normalize_blog_url,
    urls_match,
)


class TestBlogPostUrlRe:
    def test_matches_desktop(self) -> None:
        assert BLOG_POST_URL_RE.match("https://blog.naver.com/myblog/123456789")

    def test_matches_mobile(self) -> None:
        assert BLOG_POST_URL_RE.match("https://m.blog.naver.com/myblog/123456789")

    def test_rejects_short_postid(self) -> None:
        # 9자리 미만 거부
        assert BLOG_POST_URL_RE.match("https://blog.naver.com/myblog/12345") is None

    def test_rejects_other_domain(self) -> None:
        assert BLOG_POST_URL_RE.match("https://tistory.com/myblog/123456789") is None


class TestNormalizeBlogUrl:
    def test_desktop_to_mobile(self) -> None:
        result = normalize_blog_url("https://blog.naver.com/myblog/123456789")
        assert result == "https://m.blog.naver.com/myblog/123456789"

    def test_mobile_unchanged(self) -> None:
        result = normalize_blog_url("https://m.blog.naver.com/myblog/123456789")
        assert result == "https://m.blog.naver.com/myblog/123456789"

    def test_strips_trailing_slash(self) -> None:
        result = normalize_blog_url("https://blog.naver.com/myblog/123456789/")
        assert result == "https://m.blog.naver.com/myblog/123456789"

    def test_strips_query_string(self) -> None:
        result = normalize_blog_url("https://blog.naver.com/myblog/123456789?source=naver")
        assert result == "https://m.blog.naver.com/myblog/123456789"

    def test_adds_https_when_missing(self) -> None:
        result = normalize_blog_url("blog.naver.com/myblog/123456789")
        assert result == "https://m.blog.naver.com/myblog/123456789"

    def test_returns_none_for_invalid_domain(self) -> None:
        assert normalize_blog_url("https://tistory.com/myblog/123456789") is None

    def test_returns_none_for_empty(self) -> None:
        assert normalize_blog_url("") is None
        assert normalize_blog_url("   ") is None

    def test_returns_none_for_short_postid(self) -> None:
        assert normalize_blog_url("https://blog.naver.com/myblog/123") is None

    def test_returns_none_for_user_home(self) -> None:
        # /clip/ 또는 user 홈 URL 배제
        assert normalize_blog_url("https://blog.naver.com/myblog") is None


class TestUrlsMatch:
    def test_desktop_mobile_equivalent(self) -> None:
        assert urls_match(
            "https://blog.naver.com/myblog/123456789",
            "https://m.blog.naver.com/myblog/123456789",
        )

    def test_trailing_slash_irrelevant(self) -> None:
        assert urls_match(
            "https://blog.naver.com/myblog/123456789/",
            "https://m.blog.naver.com/myblog/123456789",
        )

    def test_different_postids_no_match(self) -> None:
        assert not urls_match(
            "https://blog.naver.com/myblog/111111111",
            "https://blog.naver.com/myblog/222222222",
        )

    def test_different_users_no_match(self) -> None:
        assert not urls_match(
            "https://blog.naver.com/userA/123456789",
            "https://blog.naver.com/userB/123456789",
        )

    def test_invalid_url_no_match(self) -> None:
        assert not urls_match("invalid", "https://blog.naver.com/myblog/123456789")

    def test_query_string_irrelevant(self) -> None:
        assert urls_match(
            "https://blog.naver.com/myblog/123456789?from=naver",
            "https://m.blog.naver.com/myblog/123456789?utm_source=daum",
        )


class TestRegexCopySync:
    """url_match.BLOG_POST_URL_RE 가 serp_collector.BLOG_POST_URL_RE 와 동일한가.

    의도적 복제이므로 변경 시 양쪽 동시 갱신 필수. 본 테스트가 동기화 누락 방어.
    """

    def test_pattern_string_identical(self) -> None:
        from domain.crawler.serp_collector import BLOG_POST_URL_RE as CRAWLER_RE

        assert BLOG_POST_URL_RE.pattern == CRAWLER_RE.pattern, (
            "url_match.BLOG_POST_URL_RE 와 serp_collector.BLOG_POST_URL_RE 가 다릅니다. "
            "도메인 격리 의도적 복제이므로 서로 동기화 필요. SPEC-RANKING.md §11 R1 참조."
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://blog.naver.com/myblog/123456789",
        "https://m.blog.naver.com/myblog/123456789",
        "https://blog.naver.com/myblog/123456789/",
        "https://blog.naver.com/myblog/123456789?source=naver",
    ],
)
def test_normalize_idempotent(url: str) -> None:
    """normalize 결과를 다시 normalize 해도 같아야 한다 (멱등)."""
    once = normalize_blog_url(url)
    assert once is not None
    twice = normalize_blog_url(once)
    assert once == twice
