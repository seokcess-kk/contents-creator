"""[6] 아웃라인 + 도입부 확정 생성 (Opus).

SPEC-SEO-TEXT.md §3 [6] 구현.
패턴 카드를 기반으로 아웃라인 + 도입부 200~300자 + image_prompts 동시 생성.
도입부는 톤 락(tone lock) 역할이며 [7] 에서 재생성하지 않는다.

프롬프트는 prompt_builder 단일 진입점에서 빌드한다.

Extended Thinking: settings.outline_thinking_budget > 0 일 때 활성. 제목 CTR·
도입부 훅·섹션 구조·의료법·키워드 밀도·DIA+ 배치 등 제약 동시 충족을 위한
사고 시간을 확보한다. SEO 성과 단일 최대 지렛대 지점.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.analysis.pattern_card import PatternCard
from domain.common.usage import ApiUsage, record_usage
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
    feedback: str | None = None,
) -> Outline:
    """[6] 아웃라인 + 도입부 + image_prompts 생성.

    Opus 에 tool_use 로 구조화 출력을 강제한다.
    feedback 가 있으면 이전 생성 결과의 문제점을 프롬프트에 추가한다.
    outline_thinking_budget > 0 이면 Extended Thinking 활성.
    """
    messages, tool_schema = build_outline_prompt(pattern_card, compliance_rules)
    if feedback:
        messages[0]["content"] += f"\n\n[이전 생성 결과 피드백]\n{feedback}"

    client = anthropic.Anthropic(api_key=require("anthropic_api_key"))

    # thinking 활성 시: max_tokens 는 thinking 예산 + 실제 응답 합계 이상이어야 한다.
    # tool_use 응답은 통상 ~1500 tokens, 여유 포함해 thinking + 4000 으로 설정.
    thinking_budget = settings.outline_thinking_budget
    extra_kwargs: dict[str, Any] = {}
    if thinking_budget > 0:
        extra_kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }
        max_tokens = thinking_budget + 4000
    else:
        max_tokens = 4096

    # Anthropic 규칙: Extended Thinking 과 tool 이름 강제(`{type: tool, name: X}`)는
    # 동시 사용 불가. tool 이 단 1개 전달되므로 `any` 로 두어도 실질 효과는 동일하다.
    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_opus,
        max_tokens=max_tokens,
        tools=[tool_schema],
        tool_choice={"type": "any"},
        messages=messages,
        **extra_kwargs,
    )

    record_usage(
        ApiUsage(
            provider="anthropic",
            model=settings.model_opus,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
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
