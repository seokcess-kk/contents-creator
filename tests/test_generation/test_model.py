"""Generation 도메인 모델 테스트."""

from __future__ import annotations

from domain.generation.model import (
    BodyResult,
    BodySection,
    ImagePromptItem,
    KeywordPlan,
    Outline,
    OutlineSection,
)


class TestOutlineSection:
    def test_minimal(self) -> None:
        s = OutlineSection(index=1, role="도입/공감", subtitle="test")
        assert s.index == 1
        assert s.is_intro is False
        assert s.dia_markers == []

    def test_with_intro_flag(self) -> None:
        s = OutlineSection(index=1, role="도입/공감", subtitle="x", is_intro=True)
        assert s.is_intro is True


class TestImagePromptItem:
    def test_fields(self) -> None:
        ip = ImagePromptItem(
            sequence=1,
            position="after_intro",
            prompt="A peaceful Korean tea scene",
            alt_text="한국 차 풍경",
            image_type="photo",
            rationale="도입 직후 분위기 사진",
        )
        assert ip.sequence == 1
        assert "Korean" in ip.prompt


class TestKeywordPlan:
    def test_range(self) -> None:
        kp = KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.67,
        )
        assert kp.main_keyword_target_count == 14
        assert 0.0 <= kp.subtitle_inclusion_target <= 1.0


class TestOutline:
    def test_roundtrip(self) -> None:
        outline = Outline(
            title="test title",
            title_pattern="질문형",
            target_chars=2800,
            intro="테스트 도입부 200자 이상의 텍스트",
            sections=[
                OutlineSection(index=1, role="도입/공감", subtitle="intro", is_intro=True),
                OutlineSection(index=2, role="정보제공", subtitle="body"),
            ],
            keyword_plan=KeywordPlan(
                main_keyword_target_count=10,
                subtitle_inclusion_target=0.5,
            ),
        )
        data = outline.model_dump()
        loaded = Outline.model_validate(data)
        assert loaded.title == outline.title
        assert len(loaded.sections) == 2

    def test_filter_intro_sections(self) -> None:
        outline = Outline(
            title="t",
            title_pattern="질문형",
            target_chars=1000,
            intro="도입부",
            sections=[
                OutlineSection(index=1, role="도입/공감", subtitle="i", is_intro=True),
                OutlineSection(index=2, role="정보제공", subtitle="b"),
                OutlineSection(index=3, role="요약", subtitle="c"),
            ],
            keyword_plan=KeywordPlan(
                main_keyword_target_count=5,
                subtitle_inclusion_target=0.5,
            ),
        )
        body_sections = [s for s in outline.sections if not s.is_intro]
        assert len(body_sections) == 2
        assert all(not s.is_intro for s in body_sections)


class TestBodyResult:
    def test_empty(self) -> None:
        br = BodyResult()
        assert br.body_sections == []

    def test_with_sections(self) -> None:
        br = BodyResult(
            body_sections=[
                BodySection(index=2, subtitle="제목", content_md="본문 내용"),
                BodySection(index=3, subtitle="제목2", content_md="본문2"),
            ]
        )
        assert len(br.body_sections) == 2
        assert br.body_sections[0].index == 2
