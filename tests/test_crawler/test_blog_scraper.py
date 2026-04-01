"""블로그 스크래퍼 테스트."""

from __future__ import annotations

from domain.crawler.blog_scraper import _parse_blog_html, _resolve_blog_url


class TestResolveBlogUrl:
    def test_mobile_to_desktop(self) -> None:
        url = "https://m.blog.naver.com/testuser/123456"
        result = _resolve_blog_url(url)
        assert "blog.naver.com" in result
        assert "m.blog.naver.com" not in result

    def test_short_url_to_postview(self) -> None:
        url = "https://blog.naver.com/testuser/123456"
        result = _resolve_blog_url(url)
        assert "PostView.naver" in result
        assert "blogId=testuser" in result
        assert "logNo=123456" in result

    def test_already_postview(self) -> None:
        url = "https://blog.naver.com/PostView.naver?blogId=test&logNo=123"
        result = _resolve_blog_url(url)
        assert result == url


class TestParseBlogHtml:
    def test_smart_editor_3(self) -> None:
        html = """
        <html><body>
            <div class="se-main-container">
                <p>본문 내용입니다.</p>
            </div>
        </body></html>
        """
        raw, text = _parse_blog_html(html)
        assert "se-main-container" in raw
        assert "본문 내용입니다" in text

    def test_old_editor(self) -> None:
        html = """
        <html><body>
            <div id="postViewArea">
                <p>구버전 본문</p>
            </div>
        </body></html>
        """
        raw, text = _parse_blog_html(html)
        assert "postViewArea" in raw
        assert "구버전 본문" in text

    def test_body_fallback(self) -> None:
        html = "<html><body><p>기본 내용</p></body></html>"
        raw, text = _parse_blog_html(html)
        assert "기본 내용" in text
