"""image_prompt_fallback — LLM 이 image_prompts=0 반환 시 코드로 강제 생성.

stage_runner [6] 단계에서 outline.image_prompts 가 빈 경우 폴백 호출.
"""

from __future__ import annotations

import random

import pytest

from domain.generation.image_prompt_fallback import generate_fallback_image_prompts
from domain.generation.model import KeywordPlan, Outline, OutlineSection


@pytest.fixture(autouse=True)
def _seed_random() -> None:
    """random.choice 결정성 확보 — 시나리오 검증을 위해 시드 고정."""
    random.seed(42)


def _outline(section_count: int = 3) -> Outline:
    sections = [
        OutlineSection(
            index=1,
            role="도입/공감",
            subtitle="도입부",
            is_intro=True,
        )
    ]
    roles = ["원인분석", "방법제시", "비교분석", "정보제공", "요약"]
    for i in range(section_count):
        sections.append(
            OutlineSection(
                index=i + 2,
                role=roles[i % len(roles)],
                subtitle=f"섹션 {i + 2}",
            )
        )
    return Outline(
        title="다이어트한의원 효과 정리",
        title_pattern="키워드+정리",
        target_chars=2800,
        intro="도입부 텍스트입니다.",
        sections=sections,
        keyword_plan=KeywordPlan(
            main_keyword_target_count=10,
            subtitle_inclusion_target=0.5,
        ),
    )


class TestGenerateFallbackImagePrompts:
    def test_target_count_respects_section_limit(self) -> None:
        """target=5 + 본문 섹션 3개 → max count = sections + 1 = 4."""
        outline = _outline(section_count=3)
        prompts = generate_fallback_image_prompts(outline, target_count=5)
        assert len(prompts) == 4  # min(5, 3+1)

    def test_target_count_smaller_than_sections_used(self) -> None:
        outline = _outline(section_count=5)
        prompts = generate_fallback_image_prompts(outline, target_count=2)
        assert len(prompts) == 2

    def test_first_prompt_is_after_intro(self) -> None:
        outline = _outline(section_count=3)
        prompts = generate_fallback_image_prompts(outline, target_count=4)
        assert prompts[0].position == "after_intro"
        assert prompts[0].sequence == 1

    def test_section_positions_use_section_index(self) -> None:
        outline = _outline(section_count=2)
        prompts = generate_fallback_image_prompts(outline, target_count=3)
        # 0: after_intro, 1: section_2_end, 2: section_3_end
        assert prompts[1].position == "section_2_end"
        assert prompts[2].position == "section_3_end"

    def test_all_prompts_contain_no_text_constraint(self) -> None:
        outline = _outline(section_count=3)
        prompts = generate_fallback_image_prompts(outline, target_count=4)
        for p in prompts:
            assert "No text" in p.prompt or "no letters" in p.prompt

    def test_alt_text_includes_outline_title(self) -> None:
        outline = _outline(section_count=2)
        prompts = generate_fallback_image_prompts(outline, target_count=2)
        for p in prompts:
            assert "다이어트한의원" in p.alt_text

    def test_image_type_inferred_photo_or_illustration(self) -> None:
        outline = _outline(section_count=3)
        prompts = generate_fallback_image_prompts(outline, target_count=3)
        types = {p.image_type for p in prompts}
        assert types <= {"photo", "illustration"}

    def test_aspect_ratio_from_allowed_set(self) -> None:
        outline = _outline(section_count=3)
        prompts = generate_fallback_image_prompts(outline, target_count=3)
        for p in prompts:
            assert p.aspect_ratio in {"1:1", "4:3", "16:9", "3:4"}

    def test_sequence_is_one_based_consecutive(self) -> None:
        outline = _outline(section_count=4)
        prompts = generate_fallback_image_prompts(outline, target_count=4)
        sequences = [p.sequence for p in prompts]
        assert sequences == [1, 2, 3, 4]

    def test_unknown_role_falls_back_to_default(self) -> None:
        """_ROLE_SCENARIOS 에 없는 role 도 default scenario 사용."""
        outline = Outline(
            title="제목",
            title_pattern="...",
            target_chars=2000,
            intro="...",
            sections=[
                OutlineSection(index=1, role="도입/공감", subtitle="도입", is_intro=True),
                OutlineSection(index=2, role="알수없는역할", subtitle="섹션 2"),
            ],
            keyword_plan=KeywordPlan(main_keyword_target_count=5, subtitle_inclusion_target=0.5),
        )
        prompts = generate_fallback_image_prompts(outline, target_count=2)
        assert len(prompts) == 2
        for p in prompts:
            assert "no text" in p.prompt.lower() or "no letters" in p.prompt.lower()

    def test_intro_only_outline_returns_one_prompt(self) -> None:
        """본문 섹션이 없으면 도입 후 1개만."""
        outline = _outline(section_count=0)
        prompts = generate_fallback_image_prompts(outline, target_count=5)
        assert len(prompts) == 1
        assert prompts[0].position == "after_intro"
