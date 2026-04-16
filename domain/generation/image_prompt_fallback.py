"""이미지 프롬프트 폴백 생성.

LLM이 image_prompts를 0개로 반환할 때, 섹션 구조 기반으로
기본 이미지 프롬프트를 코드로 생성한다.
"""

from __future__ import annotations

import random

from domain.generation.model import ImagePromptItem, Outline

# 섹션 역할별 기본 이미지 시나리오
_ROLE_SCENARIOS: dict[str, list[str]] = {
    "도입/공감": [
        "A Korean person looking at a smartphone with a thoughtful expression, soft natural light",
        "A cozy Korean cafe scene with a warm cup of tea and a notebook",
    ],
    "원인분석": [
        "A clean minimalist infographic-style illustration showing cause and effect",
        "A flat illustration of interconnected puzzle pieces in pastel colors",
    ],
    "방법제시": [
        "A photorealistic shot of healthy Korean meal preparation with fresh ingredients",
        "A Korean woman doing gentle stretching in a bright living room",
    ],
    "비교분석": [
        "A side-by-side comparison infographic with warm color palette",
        "A flat illustration showing two different approaches with visual contrast",
    ],
    "정보제공": [
        "A clean workspace with Korean herbal medicine ingredients on a wooden tray",
        "A modern Korean clinic interior with warm natural lighting",
    ],
    "요약": [
        "A peaceful park scene with a Korean person walking on a tree-lined path",
        "A minimalist checklist illustration in soft pastel tones",
    ],
}

_DEFAULT_SCENARIO = [
    "A photorealistic lifestyle scene with warm natural lighting, no text, no letters",
    "A flat illustration in soft pastel colors with clean minimal design, no text",
]


def generate_fallback_image_prompts(
    outline: Outline,
    target_count: int,
) -> list[ImagePromptItem]:
    """섹션 구조 기반으로 기본 이미지 프롬프트를 생성한다."""
    sections = [s for s in outline.sections if not s.is_intro]
    count = min(target_count, len(sections) + 1)  # 섹션 수 + 1(도입 후)

    prompts: list[ImagePromptItem] = []

    for i in range(count):
        if i == 0:
            position = "after_intro"
            role = "도입/공감"
        elif i <= len(sections):
            position = f"section_{sections[i - 1].index}_end"
            role = sections[i - 1].role
        else:
            position = "before_conclusion"
            role = "요약"

        scenarios = _ROLE_SCENARIOS.get(role, _DEFAULT_SCENARIO)
        base_prompt = random.choice(scenarios)
        aspect = random.choice(["1:1", "4:3", "16:9", "3:4"])

        prompts.append(
            ImagePromptItem(
                sequence=i + 1,
                position=position,
                prompt=f"{base_prompt}. No text, no letters.",
                alt_text=f"{outline.title} 관련 이미지",
                image_type="photo" if "photorealistic" in base_prompt else "illustration",
                aspect_ratio=aspect,
                rationale=f"섹션 '{role}' 기반 자동 생성 (LLM 폴백)",
            )
        )

    return prompts
