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

from config.settings import settings
from domain.analysis.pattern_card import PatternCard
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.usage import ApiUsage, record_usage
from domain.generation.model import (
    ImagePromptItem,
    KeywordPlan,
    Outline,
    OutlineSection,
)
from domain.generation.prompt_builder import build_outline_prompt

logger = logging.getLogger(__name__)


_TOOL_ENFORCE_HINT = (
    "\n\n[출력 규약]\n"
    "반드시 `{tool_name}` tool 을 호출해 구조화된 결과를 반환하라.\n"
    "자유 텍스트·마크다운·설명 없이 tool_use 블록만 응답하라."
)


def generate_outline(
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
    feedback: str | None = None,
) -> Outline:
    """[6] 아웃라인 + 도입부 + image_prompts 생성.

    Opus 에 tool_use 로 구조화 출력을 강제한다.
    feedback 가 있으면 이전 생성 결과의 문제점을 프롬프트에 추가한다.

    outline_thinking_budget > 0 이면 Extended Thinking 활성 + tool_choice=auto.
    thinking 과 tool 이름 강제는 Anthropic 규약상 비호환이므로, auto 에서도
    프롬프트로 tool 사용을 강제하고 tool_use 블록이 없으면 1회 재호출한다.
    """
    messages, tool_schema = build_outline_prompt(pattern_card, compliance_rules)
    if feedback:
        messages[0]["content"] += f"\n\n[이전 생성 결과 피드백]\n{feedback}"

    thinking_budget = settings.outline_thinking_budget
    if thinking_budget > 0:
        # thinking 경로 — tool_choice=auto + 프롬프트 강제 + tool_use 누락 시 1회 재시도
        messages[-1]["content"] += _TOOL_ENFORCE_HINT.format(tool_name=tool_schema["name"])
        response = _invoke(
            tool_schema=tool_schema,
            messages=messages,
            thinking_budget=thinking_budget,
        )
        tool_input = _try_extract_tool_input(response)
        if tool_input is None:
            # thinking off + tool 이름 강제 폴백 (확정적 tool_use 응답)
            logger.warning("outline tool_use missing under thinking; falling back")
            response = _invoke(
                tool_schema=tool_schema,
                messages=messages,
                thinking_budget=0,
            )
            tool_input = _extract_tool_input(response)
    else:
        response = _invoke(tool_schema=tool_schema, messages=messages, thinking_budget=0)
        tool_input = _extract_tool_input(response)

    return _parse_outline(tool_input)


def _invoke(
    *,
    tool_schema: dict[str, Any],
    messages: list[dict[str, Any]],
    thinking_budget: int,
) -> Any:
    """Anthropic 호출 + usage 기록. thinking_budget 에 따라 tool_choice 결정.

    최신 Anthropic API (4.7+) 는 thinking.type.enabled + budget_tokens 대신
    thinking.type.adaptive + output_config.effort 조합을 쓴다. thinking_budget 는
    on/off 플래그로만 남기고, 실제 사고 깊이는 effort 로 고정한다 (SEO 품질 우선).
    """
    client = build_client()
    extra_kwargs: dict[str, Any] = {}
    if thinking_budget > 0:
        extra_kwargs["thinking"] = {"type": "adaptive"}
        extra_kwargs["output_config"] = {"effort": "high"}
        max_tokens = 8192
        tool_choice: dict[str, Any] = {"type": "auto"}
    else:
        max_tokens = 4096
        tool_choice = {"type": "tool", "name": tool_schema["name"]}

    response = messages_create_with_retry(
        client,
        model=settings.model_opus,
        max_tokens=max_tokens,
        tools=[tool_schema],
        tool_choice=tool_choice,
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
    return response


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출. 없으면 ValueError."""
    tool_input = _try_extract_tool_input(response)
    if tool_input is None:
        raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (outline)")
    return tool_input


def _try_extract_tool_input(response: Any) -> dict[str, Any] | None:
    """tool_use 블록에서 input 추출. 없으면 None (재시도 판단용)."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    return None


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
