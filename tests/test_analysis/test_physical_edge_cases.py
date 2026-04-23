"""물리 추출 edge case 테스트 — 인공 HTML.

실측 HTML 2개(golden_values.json) 외의 경계 조건을 보호한다.
실측 샘플 추가는 외부 크롤링 필요하므로 범위 밖. 본 파일은 아래만 다룬다:

1. script/style 오염 방지 (P1-8 회귀 테스트)
2. 이미지 0개
3. 소제목 0개
4. 극단적으로 짧은 글
5. 네이버 구 UI (post_ct fallback)
6. 본문 없음 (빈 컨테이너)
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import HttpUrl

from domain.analysis.physical_extractor import extract_body_text, extract_physical
from domain.crawler.model import BlogPage


def _page(html: str) -> BlogPage:
    return BlogPage(
        idx=0,
        rank=1,
        url=HttpUrl("https://m.blog.naver.com/test/1"),
        mobile_url=HttpUrl("https://m.blog.naver.com/test/1"),
        html=html,
        fetched_at=datetime.now(UTC),
    )


class TestScriptStyleDecompose:
    """P1-8: script/style 제거 후 get_text 호출 — 오염 방지."""

    def test_script_content_not_in_body(self) -> None:
        html = """<html><body>
        <script>var x = "가짜본문_내용_오염원_A";</script>
        <div class="se-main-container">
          <div class="se-component se-text"><div class="se-text-paragraph"><p>진짜 본문입니다.</p></div></div>
        </div>
        </body></html>"""
        text = extract_body_text(_page(html))
        assert "가짜본문" not in text
        assert "진짜 본문" in text

    def test_style_content_not_in_body(self) -> None:
        html = """<html><body>
        <style>.x { content: "가짜본문_내용_오염원_B"; color: red; }</style>
        <div class="se-main-container">
          <div class="se-component se-text"><div class="se-text-paragraph"><p>실제 본문.</p></div></div>
        </div>
        </body></html>"""
        text = extract_body_text(_page(html))
        assert "가짜본문" not in text
        assert "color: red" not in text

    def test_noscript_content_not_in_body(self) -> None:
        html = """<html><body>
        <noscript>자바스크립트를_켜세요_오염원</noscript>
        <div class="se-main-container">
          <div class="se-component se-text"><div class="se-text-paragraph"><p>본문.</p></div></div>
        </div>
        </body></html>"""
        text = extract_body_text(_page(html))
        assert "오염원" not in text


class TestEdgeCaseStructures:
    def test_empty_container_returns_empty_analysis(self) -> None:
        """se-main-container 가 비어 있어도 크래시 없이 PhysicalAnalysis 반환."""
        html = '<html><body><div class="se-main-container"></div></body></html>'
        result = extract_physical(_page(html), "키워드")
        assert result.total_chars == 0
        assert result.total_paragraphs == 0
        assert result.subtitle_count == 0

    def test_no_container_falls_back_to_body(self) -> None:
        """se-main-container 도 post_ct 도 없으면 body 전체를 본문으로 취급."""
        html = "<html><body><p>최소 글자 본문입니다.</p></body></html>"
        result = extract_physical(_page(html), "본문")
        assert result.total_chars > 0

    def test_post_ct_fallback_old_ui(self) -> None:
        """네이버 구 UI (div.post_ct) 도 처리."""
        html = """<html><body>
        <div class="post_ct">
          <h3>구버전 소제목</h3>
          <p>구버전 본문 문단.</p>
          <p>두 번째 문단.</p>
        </div>
        </body></html>"""
        result = extract_physical(_page(html), "구버전")
        assert result.total_chars > 0

    def test_no_images(self) -> None:
        """이미지 0개 블로그도 처리 — element_sequence 에 image 없음."""
        html = """<html><body>
        <div class="se-main-container">
          <div class="se-component se-text"><div class="se-text-paragraph"><p>이미지 없는 글이에요. 텍스트만 있어요.</p></div></div>
        </div>
        </body></html>"""
        result = extract_physical(_page(html), "이미지")
        images = [e for e in result.element_sequence if e.type == "image"]
        assert len(images) == 0

    def test_very_short_body(self) -> None:
        """매우 짧은 글 (< 100자) 도 정상 처리."""
        html = """<html><body>
        <div class="se-main-container">
          <div class="se-component se-text"><div class="se-text-paragraph"><p>짧은 글.</p></div></div>
        </div>
        </body></html>"""
        result = extract_physical(_page(html), "짧은")
        assert result.total_chars > 0
        assert result.total_chars < 100
