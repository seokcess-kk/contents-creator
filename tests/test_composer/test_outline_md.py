"""outline_md.py 단위 테스트.

검증:
- 태그 섹션 존재
- 이미지 매핑 섹션 존재
- 섹션 구조 정확
- 도입부 확정본 표시
- 키워드 계획 표시
"""

from __future__ import annotations

from domain.composer.outline_md import convert_outline_to_md
from domain.generation.model import (
    ImagePromptItem,
    KeywordPlan,
    Outline,
    OutlineSection,
)


def _make_outline(
    tags: list[str] | None = None,
    image_prompts: list[ImagePromptItem] | None = None,
) -> Outline:
    if tags is None:
        tags = ["다이어트", "한의원", "체질"]
    if image_prompts is None:
        image_prompts = [
            ImagePromptItem(
                sequence=1,
                position="after_intro",
                prompt="A healthy meal photo",
                alt_text="건강한 식사",
                image_type="photo",
                rationale="도입 직후 분위기 사진",
            ),
        ]
    return Outline(
        title="다이어트 한의원 효과 정리",
        title_pattern="방법론형",
        target_chars=2800,
        suggested_tags=tags,
        image_prompts=image_prompts,
        intro="다이어트를 시작하려는 분들이라면 한의원도 고려해볼 만합니다.",
        sections=[
            OutlineSection(
                index=1,
                role="도입/공감",
                subtitle="(도입부)",
                is_intro=True,
            ),
            OutlineSection(
                index=2,
                role="정보제공",
                subtitle="한의원 다이어트가 주목받는 이유",
                summary="최근 트렌드와 원리 설명",
                target_chars=450,
                dia_markers=["list", "statistics"],
            ),
            OutlineSection(
                index=3,
                role="원인분석",
                subtitle="요요가 반복되는 이유",
                summary="3가지 원인 분석",
                target_chars=520,
            ),
        ],
        keyword_plan=KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.67,
        ),
    )


class TestOutlineToMd:
    """convert_outline_to_md 기본 동작 테스트."""

    def test_title_in_output(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "# 다이어트 한의원 효과 정리" in result.content

    def test_title_pattern_shown(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "방법론형" in result.content

    def test_target_chars_shown(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "2800" in result.content

    def test_sections_present(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "정보제공" in result.content
        assert "한의원 다이어트가 주목받는 이유" in result.content
        assert "원인분석" in result.content

    def test_intro_section_marked(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "도입부" in result.content

    def test_dia_markers_shown(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "list" in result.content
        assert "statistics" in result.content

    def test_intro_text_quoted(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "다이어트를 시작하려는" in result.content

    def test_keyword_plan_shown(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "14" in result.content
        assert "67%" in result.content


class TestTagSection:
    """제안 태그 섹션 검증."""

    def test_tag_section_exists(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "## 제안 태그 (수동 삽입용)" in result.content

    def test_tags_displayed(self) -> None:
        result = convert_outline_to_md(_make_outline(tags=["다이어트", "한의원"]))
        assert "`다이어트`" in result.content
        assert "`한의원`" in result.content

    def test_empty_tags(self) -> None:
        result = convert_outline_to_md(_make_outline(tags=[]))
        assert "(태그 없음)" in result.content


class TestImageGuideSection:
    """이미지 매핑 가이드 섹션 검증."""

    def test_image_guide_section_exists(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "## 이미지 매핑 가이드" in result.content

    def test_image_details_shown(self) -> None:
        result = convert_outline_to_md(_make_outline())
        assert "after_intro" in result.content
        assert "건강한 식사" in result.content
        assert "photo" in result.content
        assert "도입 직후 분위기 사진" in result.content

    def test_no_image_prompts(self) -> None:
        result = convert_outline_to_md(_make_outline(image_prompts=[]))
        assert "(이미지 prompt 없음)" in result.content

    def test_multiple_images(self) -> None:
        images = [
            ImagePromptItem(
                sequence=1,
                position="after_intro",
                prompt="Photo 1",
                alt_text="사진 1",
                image_type="photo",
                rationale="근거 1",
            ),
            ImagePromptItem(
                sequence=2,
                position="section_2_end",
                prompt="Photo 2",
                alt_text="사진 2",
                image_type="illustration",
                rationale="근거 2",
            ),
        ]
        result = convert_outline_to_md(_make_outline(image_prompts=images))
        assert "### 이미지 1" in result.content
        assert "### 이미지 2" in result.content
        assert "사진 1" in result.content
        assert "사진 2" in result.content
