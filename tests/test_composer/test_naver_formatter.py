"""네이버 포맷터 테스트."""

from __future__ import annotations

from domain.composer.naver_formatter import (
    insert_disclaimer,
    markdown_to_naver_html,
)


class TestMarkdownToNaverHtml:
    def test_converts_h1_to_h2(self) -> None:
        md = "# 제목입니다"
        html = markdown_to_naver_html(md)
        assert "<h2" in html
        assert "제목입니다" in html

    def test_converts_h2_to_h3(self) -> None:
        md = "## 소제목"
        html = markdown_to_naver_html(md)
        assert "<h3" in html
        assert "소제목" in html

    def test_converts_paragraph(self) -> None:
        md = "일반 텍스트 문단입니다."
        html = markdown_to_naver_html(md)
        assert "<p" in html
        assert "일반 텍스트" in html

    def test_inline_styles_only(self) -> None:
        md = "# 제목\n\n본문"
        html = markdown_to_naver_html(md)
        assert "<style>" not in html
        assert "style=" in html

    def test_image_placeholder(self) -> None:
        md = "[이미지: 시술실 사진]"
        html = markdown_to_naver_html(md)
        assert "실사 사진 삽입" in html
        assert "시술실 사진" in html

    def test_bold_text(self) -> None:
        md = "이것은 **강조** 텍스트입니다."
        html = markdown_to_naver_html(md)
        assert "<strong>강조</strong>" in html

    def test_empty_line_becomes_br(self) -> None:
        md = "첫째\n\n둘째"
        html = markdown_to_naver_html(md)
        assert "<br>" in html

    def test_font_family_nanum(self) -> None:
        md = "텍스트"
        html = markdown_to_naver_html(md)
        assert "Nanum Gothic" in html


class TestInsertDisclaimer:
    def test_appends_disclaimer(self) -> None:
        html = "<p>본문</p>"
        result = insert_disclaimer(html, "테스트 고지문")
        assert "테스트 고지문" in result
        assert html in result

    def test_disclaimer_has_styling(self) -> None:
        result = insert_disclaimer("<p>본문</p>", "고지문")
        assert "background" in result
        assert "font-size:13px" in result
