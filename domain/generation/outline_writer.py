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

# tool_use 응답에 반드시 포함돼야 하는 최상위 필드. 이게 빠지면 [7]~[10] 진행 자체가 불가하다.
# image_prompts 는 의도적으로 제외 — [9] 이미지 생성은 옵션 단계라 누락 시 빈 list 폴백 후
# 이미지 없이 발행 가능. 운영 데이터상 system 프롬프트가 큰 키워드(예: 분석 input>90k tokens)
# 에서 응답 끝부분 메타 필드가 max_tokens 한도로 잘리며 image_prompts 가 자주 누락된다.
# 이런 케이스에서 콘텐츠 발행 자체를 막는 것보다 이미지 0개로 발행하는 편이 운영적으로 합리적.
_REQUIRED_OUTLINE_FIELDS = (
    "title",
    "title_pattern",
    "target_chars",
    "intro",
    "sections",
    "keyword_plan",
)
_OPTIONAL_OUTLINE_FIELDS = ("image_prompts",)


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
    프롬프트로 tool 사용을 강제한다.

    1차 호출 후 tool_use 가 없거나 required 필드가 누락되면 thinking off + tool 이름
    강제 + 누락 필드 피드백 주입으로 1회 재호출한다. thinking on/off 양쪽에 동일하게
    적용되는 안전망 — Opus 가 긴 system 제약 하에서 keyword_plan 같은 메타 필드를
    누락하는 산발적 케이스를 흡수한다.
    """
    shared_system, messages, tool_schema = build_outline_prompt(pattern_card, compliance_rules)
    if feedback:
        messages[-1]["content"] += f"\n\n[이전 생성 결과 피드백]\n{feedback}"

    thinking_budget = settings.outline_thinking_budget
    if thinking_budget > 0:
        messages[-1]["content"] += _TOOL_ENFORCE_HINT.format(tool_name=tool_schema["name"])

    response = _invoke(
        shared_system=shared_system,
        tool_schema=tool_schema,
        messages=messages,
        thinking_budget=thinking_budget,
    )
    tool_input = _try_extract_tool_input(response)

    if tool_input is None or not _has_required_fields(tool_input):
        # 폴백: thinking off + tool 이름 강제 + 누락 필드 피드백 주입.
        # 누락 필드 메시지에는 optional 까지 포함해 LLM 에게 모든 schema 필드를 채워달라고 요청.
        missing = (
            _missing_fields(tool_input, include_optional=True)
            if tool_input is not None
            else ["<tool_use missing>"]
        )
        logger.warning(
            "outline tool_use incomplete; retrying with feedback. missing=%s thinking_was_on=%s",
            missing,
            thinking_budget > 0,
        )
        retry_messages = [
            *messages[:-1],
            {
                **messages[-1],
                "content": messages[-1]["content"]
                + f"\n\n[필수 보정] 이전 응답에서 다음 tool_use 필드가 누락되었습니다: {missing}. "
                + "tool_schema 의 모든 required 필드를 빠짐없이 포함해 다시 응답하세요.",
            },
        ]
        response = _invoke(
            shared_system=shared_system,
            tool_schema=tool_schema,
            messages=retry_messages,
            thinking_budget=0,
        )
        tool_input = _extract_tool_input(response)

    _assert_required_fields(tool_input)
    return _parse_outline(tool_input)


def _has_required_fields(tool_input: dict[str, Any]) -> bool:
    return all(field in tool_input for field in _REQUIRED_OUTLINE_FIELDS)


def _missing_fields(tool_input: dict[str, Any], *, include_optional: bool = False) -> list[str]:
    fields = _REQUIRED_OUTLINE_FIELDS + (_OPTIONAL_OUTLINE_FIELDS if include_optional else ())
    return [f for f in fields if f not in tool_input]


def _assert_required_fields(tool_input: dict[str, Any]) -> None:
    missing = _missing_fields(tool_input)
    if missing:
        raise ValueError(f"outline tool_use 응답에 필수 필드 누락: {missing}")
    # optional 필드 누락은 raise 안 하고 warning + graceful (Outline 모델의 default_factory 활용).
    optional_missing = [f for f in _OPTIONAL_OUTLINE_FIELDS if f not in tool_input]
    if optional_missing:
        logger.warning(
            "outline tool_use optional 필드 누락 (graceful 폴백): %s — "
            "콘텐츠는 발행되지만 이미지 등 누락 필드 관련 산출물은 비어있음",
            optional_missing,
        )


def _invoke(
    *,
    shared_system: str,
    tool_schema: dict[str, Any],
    messages: list[dict[str, Any]],
    thinking_budget: int,
) -> Any:
    """Anthropic 호출 + usage 기록. thinking_budget 에 따라 tool_choice 결정.

    최신 Anthropic API (4.7+) 는 thinking.type.enabled + budget_tokens 대신
    thinking.type.adaptive + output_config.effort 조합을 쓴다. thinking_budget 는
    on/off 플래그로만 남기고, 실제 사고 깊이는 effort 로 고정한다 (SEO 품질 우선).

    shared_system 은 cache_control: ephemeral 로 전달해 재시도/연속 호출 시 cache hit.
    """
    client = build_client()
    extra_kwargs: dict[str, Any] = {}
    if thinking_budget > 0:
        extra_kwargs["thinking"] = {"type": "adaptive"}
        extra_kwargs["output_config"] = {"effort": "high"}
        max_tokens = 8192
        tool_choice: dict[str, Any] = {"type": "auto"}
    else:
        # 16384 는 Render Starter plan(512MB) 에서 OOM trigger.
        # Anthropic SDK httpx response buffer + Pydantic transient 메모리 spike 가
        # [1]~[5] 분석 누적 메모리와 합쳐져 한계 초과. 8192 로 되돌리고 image_prompts
        # 가 잘릴 경우엔 _OPTIONAL_OUTLINE_FIELDS graceful 폴백이 받아낸다.
        max_tokens = 8192
        tool_choice = {"type": "tool", "name": tool_schema["name"]}

    response = messages_create_with_retry(
        client,
        model=settings.model_opus,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": shared_system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[tool_schema],
        tool_choice=tool_choice,
        messages=messages,
        **extra_kwargs,
    )
    if getattr(response, "stop_reason", None) == "max_tokens":
        logger.warning(
            "outline response truncated by max_tokens (limit=%d output_tokens=%d) — "
            "응답 후반부 필드가 잘렸을 가능성. max_tokens 상향 검토 필요",
            max_tokens,
            response.usage.output_tokens,
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
