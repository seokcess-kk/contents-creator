"""assembler.py 단위 테스트.

검증:
- intro + body concat 정상 동작
- 제목(# title) 포함
- suggested_tags 미포함
- 빈 body_sections 처리
"""

from __future__ import annotations

from domain.composer.assembler import assemble_content
from domain.generation.model import (
    BodyResult,
    BodySection,
    KeywordPlan,
    Outline,
    OutlineSection,
)


def _make_outline(
    title: str = "테스트 제목",
    intro: str = "도입부 확정본 200자 이상 텍스트입니다.",
    tags: list[str] | None = None,
) -> Outline:
    return Outline(
        title=title,
        title_pattern="방법론형",
        target_chars=2800,
        suggested_tags=tags or ["태그1", "태그2"],
        intro=intro,
        sections=[
            OutlineSection(index=1, role="도입/공감", subtitle="(도입부)", is_intro=True),
            OutlineSection(
                index=2,
                role="정보제공",
                subtitle="정보 소제목",
                summary="요약",
                target_chars=450,
            ),
        ],
        keyword_plan=KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.67,
        ),
    )


def _make_body(sections: list[BodySection] | None = None) -> BodyResult:
    if sections is None:
        sections = [
            BodySection(
                index=2,
                subtitle="정보 소제목",
                content_md="본문 내용입니다. 여러 문단으로 구성됩니다.",
            ),
            BodySection(
                index=3,
                subtitle="원인 분석",
                content_md="원인 분석 내용입니다.",
            ),
        ]
    return BodyResult(body_sections=sections)


class TestAssembleContent:
    """assemble_content 기본 동작 테스트."""

    def test_title_included(self) -> None:
        result = assemble_content(_make_outline(), _make_body())
        assert result.content_md.startswith("# 테스트 제목")

    def test_intro_included(self) -> None:
        intro_text = "도입부 확정본 200자 이상 텍스트입니다."
        result = assemble_content(
            _make_outline(intro=intro_text),
            _make_body(),
        )
        assert intro_text in result.content_md

    def test_body_sections_included(self) -> None:
        result = assemble_content(_make_outline(), _make_body())
        assert "## 정보 소제목" in result.content_md
        assert "## 원인 분석" in result.content_md
        assert "본문 내용입니다." in result.content_md

    def test_tags_not_included(self) -> None:
        result = assemble_content(
            _make_outline(tags=["다이어트", "한의원"]),
            _make_body(),
        )
        assert "다이어트" not in result.content_md
        assert "한의원" not in result.content_md

    def test_empty_body_sections(self) -> None:
        result = assemble_content(
            _make_outline(),
            _make_body(sections=[]),
        )
        assert "# 테스트 제목" in result.content_md
        assert "도입부 확정본" in result.content_md

    def test_title_field_matches(self) -> None:
        result = assemble_content(_make_outline(title="커스텀 제목"), _make_body())
        assert result.title == "커스텀 제목"

    def test_section_order_preserved(self) -> None:
        result = assemble_content(_make_outline(), _make_body())
        md = result.content_md
        intro_pos = md.index("도입부 확정본")
        section2_pos = md.index("## 정보 소제목")
        section3_pos = md.index("## 원인 분석")
        assert intro_pos < section2_pos < section3_pos
