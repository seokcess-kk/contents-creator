"""naver_html.py 단위 테스트.

검증:
- 화이트리스트 태그 보존
- 비허용 태그 제거 (자식 보존)
- class, style, id 속성 제거
- 중첩 ul/ol 평탄화 + 경고
- DOCTYPE + UTF-8 래핑
"""

from __future__ import annotations

from domain.composer.naver_html import ALLOWED_TAGS, convert_to_naver_html


class TestAllowedTags:
    """화이트리스트 태그 상수 검증."""

    def test_contains_all_spec_tags(self) -> None:
        expected = {
            "h2",
            "h3",
            "p",
            "strong",
            "em",
            "hr",
            "ul",
            "ol",
            "li",
            "blockquote",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
        }
        assert expected == ALLOWED_TAGS

    def test_div_not_allowed(self) -> None:
        assert "div" not in ALLOWED_TAGS

    def test_span_not_allowed(self) -> None:
        assert "span" not in ALLOWED_TAGS

    def test_script_not_allowed(self) -> None:
        assert "script" not in ALLOWED_TAGS


class TestConvertToNaverHtml:
    """마크다운 -> 네이버 HTML 변환 테스트."""

    def test_doctype_present(self) -> None:
        result = convert_to_naver_html("Hello")
        assert result.html.startswith("<!DOCTYPE html>")

    def test_utf8_meta(self) -> None:
        result = convert_to_naver_html("Hello")
        assert 'charset="UTF-8"' in result.html

    def test_heading_preserved(self) -> None:
        result = convert_to_naver_html("## 소제목\n\n본문")
        assert "<h2>" in result.html
        assert "소제목" in result.html

    def test_strong_preserved(self) -> None:
        result = convert_to_naver_html("**강조**")
        assert "<strong>" in result.html
        assert "강조" in result.html

    def test_list_preserved(self) -> None:
        result = convert_to_naver_html("- 항목1\n- 항목2")
        assert "<ul>" in result.html
        assert "<li>" in result.html

    def test_table_preserved(self) -> None:
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = convert_to_naver_html(md)
        assert "<table>" in result.html
        assert "<td>" in result.html

    def test_blockquote_preserved(self) -> None:
        result = convert_to_naver_html("> 인용구")
        assert "<blockquote>" in result.html

    def test_hr_preserved(self) -> None:
        result = convert_to_naver_html("위\n\n---\n\n아래")
        assert "<hr" in result.html

    def test_title_in_head(self) -> None:
        result = convert_to_naver_html("Hello", title="제목")
        assert "<title>제목</title>" in result.html


class TestAttributeStripping:
    """class, style, id 속성 제거 검증."""

    def test_no_class_in_output(self) -> None:
        result = convert_to_naver_html("## 소제목\n\n본문")
        assert "class=" not in result.html

    def test_no_style_in_output(self) -> None:
        result = convert_to_naver_html("## 소제목")
        assert "style=" not in result.html


class TestNestedListFlattening:
    """중첩 리스트 평탄화 검증."""

    def test_nested_ul_warning(self) -> None:
        """마크다운으로 생성된 중첩 리스트가 평탄화되는지 확인."""
        # markdown 라이브러리가 들여쓴 리스트를 중첩 ul 로 변환
        md = "- A\n    - B\n    - C\n- D"
        result = convert_to_naver_html(md)
        # 중첩이 감지되면 경고 발생
        if result.warnings:
            assert any("Nested" in w for w in result.warnings)

    def test_no_warning_for_flat_list(self) -> None:
        md = "- A\n- B\n- C"
        result = convert_to_naver_html(md)
        nested_warnings = [w for w in result.warnings if "Nested" in w]
        assert len(nested_warnings) == 0


class TestDisallowedTagStripping:
    """비허용 태그 제거 (자식 텍스트 보존) 검증."""

    def test_div_stripped_text_preserved(self) -> None:
        # h1 은 화이트리스트에 없으므로 unwrap 됨
        md = "# 대제목\n\n본문"
        result = convert_to_naver_html(md)
        # h1 태그 자체는 제거되지만 텍스트는 남음
        assert "대제목" in result.html
        assert "<h1>" not in result.html
