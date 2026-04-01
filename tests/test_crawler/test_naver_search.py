"""네이버 검색 API 테스트."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from domain.crawler.naver_search import _strip_html, search_blog


def _make_api_response(items: list[dict]) -> bytes:
    return json.dumps({"items": items}).encode("utf-8")


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert _strip_html("<b>hello</b> world") == "hello world"

    def test_empty_string(self) -> None:
        assert _strip_html("") == ""

    def test_no_tags(self) -> None:
        assert _strip_html("plain text") == "plain text"


class TestSearchBlog:
    @patch("domain.crawler.naver_search.settings")
    @patch("domain.crawler.naver_search.urllib.request.urlopen")
    def test_returns_results(self, mock_urlopen: MagicMock, mock_settings: MagicMock) -> None:
        mock_settings.naver_client_id = "test_id"
        mock_settings.naver_client_secret = "test_secret"
        mock_response = MagicMock()
        mock_response.read.return_value = _make_api_response(
            [
                {
                    "title": "<b>강남</b> 피부과",
                    "link": "https://blog.naver.com/test/123",
                    "description": "test desc",
                    "bloggername": "tester",
                    "bloggerlink": "https://blog.naver.com/test",
                    "postdate": "20260401",
                }
            ]
        )
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        results = search_blog("강남 피부과", top_n=5)

        assert len(results) == 1
        assert results[0].title == "강남 피부과"  # HTML 태그 제거됨
        assert results[0].link == "https://blog.naver.com/test/123"

    def test_raises_without_api_keys(self) -> None:
        with patch("domain.crawler.naver_search.settings") as mock_settings:
            mock_settings.naver_client_id = ""
            mock_settings.naver_client_secret = ""

            try:
                search_blog("test")
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "NAVER_CLIENT_ID" in str(e)
