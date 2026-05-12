"""outline_validator.py 단위 테스트."""

from __future__ import annotations

from domain.analysis.pattern_card import (
    ImagePattern,
    PatternCard,
    PatternCardStats,
    RangeStats,
    SectionClassification,
)
from domain.generation.model import (
    ImagePromptItem,
    KeywordPlan,
    Outline,
    OutlineSection,
)
from domain.generation.outline_validator import validate_outline


def _make_pattern_card(
    required: list[str] | None = None,
    frequent: list[str] | None = None,
    avg_images: float = 5.0,
    intents: list[str] | None = None,
) -> PatternCard:
    return PatternCard(
        keyword="테스트",
        slug="test",
        analyzed_count=8,
        sections=SectionClassification(
            required=required or ["도입/공감", "방법제시", "요약"],
            frequent=frequent or ["정보제공", "원인분석"],
        ),
        stats=PatternCardStats(
            chars=RangeStats(avg=2800, min=2100, max=3500),
            subtitles=RangeStats(avg=5, min=4, max=7),
            keyword_density=RangeStats(avg=0.013, min=0.009, max=0.017),
        ),
        image_pattern=ImagePattern(avg_count_per_post=avg_images),
        intents=intents or [],
    )


def _make_outline(
    section_count: int = 5,
    image_count: int = 5,
    intro_len: int = 250,
    first_body_subtitle: str = "소제목 2",
    first_body_summary: str = "",
) -> Outline:
    sections = [
        OutlineSection(index=1, role="도입/공감", subtitle="(도입)", is_intro=True),
    ]
    for i in range(section_count):
        sections.append(
            OutlineSection(
                index=i + 2,
                role="정보제공",
                subtitle=first_body_subtitle if i == 0 else f"소제목 {i + 2}",
                summary=first_body_summary if i == 0 else "",
            )
        )

    prompts = [
        ImagePromptItem(
            sequence=j + 1,
            position="after_intro",
            prompt="test prompt",
            alt_text="alt",
            image_type="photo",
            rationale="reason",
        )
        for j in range(image_count)
    ]

    return Outline(
        title="테스트 제목",
        title_pattern="방법론형",
        target_chars=2800,
        intro="가" * intro_len,
        sections=sections,
        image_prompts=prompts,
        keyword_plan=KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.67,
        ),
    )


class TestValidateOutline:
    def test_passes_when_all_ok(self) -> None:
        issues = validate_outline(_make_outline(), _make_pattern_card())
        assert issues == []

    def test_fails_section_count(self) -> None:
        outline = _make_outline(section_count=2)
        issues = validate_outline(outline, _make_pattern_card())
        fields = [i.field for i in issues]
        assert "section_count" in fields

    def test_fails_image_count(self) -> None:
        outline = _make_outline(image_count=1)
        issues = validate_outline(outline, _make_pattern_card(avg_images=5.0))
        fields = [i.field for i in issues]
        assert "image_count" in fields

    def test_fails_intro_too_short(self) -> None:
        outline = _make_outline(intro_len=50)
        issues = validate_outline(outline, _make_pattern_card())
        fields = [i.field for i in issues]
        assert "intro_length" in fields

    def test_fails_intro_too_long(self) -> None:
        outline = _make_outline(intro_len=500)
        issues = validate_outline(outline, _make_pattern_card())
        fields = [i.field for i in issues]
        assert "intro_length" in fields

    def test_intro_boundary_150_passes(self) -> None:
        outline = _make_outline(intro_len=150)
        issues = validate_outline(outline, _make_pattern_card())
        fields = [i.field for i in issues]
        assert "intro_length" not in fields

    def test_intro_boundary_400_passes(self) -> None:
        outline = _make_outline(intro_len=400)
        issues = validate_outline(outline, _make_pattern_card())
        fields = [i.field for i in issues]
        assert "intro_length" not in fields

    def test_min_sections_at_least_3(self) -> None:
        """required+frequent가 2개여도 최소 3개 섹션 필요."""
        card = _make_pattern_card(required=["a"], frequent=["b"])
        outline = _make_outline(section_count=2)
        issues = validate_outline(outline, card)
        # 2 < 3 (min 3), so should fail
        fields = [i.field for i in issues]
        assert "section_count" in fields

    def test_zero_avg_images_defaults_to_3(self) -> None:
        card = _make_pattern_card(avg_images=0.0)
        outline = _make_outline(image_count=3)
        issues = validate_outline(outline, card)
        fields = [i.field for i in issues]
        assert "image_count" not in fields


class TestFirstSectionIntent:
    """P1 — 첫 본문 섹션의 intent 응답 검증.

    kiwipiepy 미설치 환경에선 skip — title_validator 의 fallback 정책과 일관.
    설치된 환경에서만 의미 있는 회귀.
    """

    def test_empty_intents_skipped(self) -> None:
        """intents 빈 리스트 → 검증 skip (graceful)."""
        card = _make_pattern_card(intents=[])
        outline = _make_outline(first_body_subtitle="무관한 소제목")
        issues = validate_outline(outline, card)
        assert all(i.field != "first_section_intent" for i in issues)

    def test_intent_match_passes(self) -> None:
        """첫 본문 섹션 소제목·요약에 intent 핵심 명사 포함 → 통과."""
        card = _make_pattern_card(intents=["임플란트 비용은 얼마인가요?"])
        outline = _make_outline(
            first_body_subtitle="임플란트 비용 알아보기",
            first_body_summary="비용 구조를 정리한다.",
        )
        issues = validate_outline(outline, card)
        # kiwipiepy 가 있으면 통과, 없으면 skip — 어느 쪽이든 issue 없어야 함
        assert all(i.field != "first_section_intent" for i in issues)

    def test_intent_mismatch_fails(self) -> None:
        """첫 본문 섹션이 intent 와 관련 없는 내용 → 실패 (kiwipiepy 있을 때만)."""
        from domain.generation.title_validator import _get_kiwi

        if _get_kiwi() is None:
            # kiwipiepy 미설치 — 정책상 skip, 테스트도 의미 없음
            return

        card = _make_pattern_card(intents=["임플란트 비용은 얼마인가요?"])
        outline = _make_outline(
            first_body_subtitle="다른 주제 소제목",
            first_body_summary="전혀 관련 없는 설명.",
        )
        issues = validate_outline(outline, card)
        fields = [i.field for i in issues]
        assert "first_section_intent" in fields
