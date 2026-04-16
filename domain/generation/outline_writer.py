"""[6] 아웃라인 + 도입부 확정 생성 (Opus 4.6).

SPEC-SEO-TEXT.md §3 [6] 구현.
패턴 카드를 기반으로 아웃라인 + 도입부 200~300자 + image_prompts 동시 생성.
도입부는 톤 락(tone lock) 역할이며 [7] 에서 재생성하지 않는다.

프롬프트는 prompt_builder 단일 진입점에서 빌드한다.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.analysis.pattern_card import PatternCard
from domain.generation.model import (
    ImagePromptItem,
    KeywordPlan,
    Outline,
    OutlineSection,
)
from domain.generation.prompt_builder import build_outline_prompt

logger = logging.getLogger(__name__)


def generate_outline(
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
) -> Outline:
    """[6] 아웃라인 + 도입부 + image_prompts 생성.

    Opus 4.6 에 tool_use 로 구조화 출력을 강제한다.
    """
    messages, tool_schema = build_outline_prompt(pattern_card, compliance_rules)

    client = anthropic.Anthropic(api_key=require("anthropic_api_key"))
    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_opus,
        max_tokens=4096,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=messages,
    )

    tool_input = _extract_tool_input(response)
    return _parse_outline(tool_input)


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (outline)")


def _parse_outline(data: dict[str, Any]) -> Outline:
    """tool_use 응답 → Outline Pydantic 모델."""
    sections = [OutlineSection(**s) for s in data.get("sections", [])]
    image_prompts = [ImagePromptItem(**ip) for ip in data.get("image_prompts", [])]
    kp = data.get("keyword_plan", {})

    return Outline(
        title=data["title"],
        title_pattern=data["title_pattern"],
        target_chars=data["target_chars"],
        suggested_tags=data.get("suggested_tags", []),
        image_prompts=image_prompts,
        intro=data["intro"],
        sections=sections,
        keyword_plan=KeywordPlan(**kp),
    )
