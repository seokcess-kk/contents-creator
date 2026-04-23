"""[7] 본문 생성 (Opus 4.6). M2 불변 규칙 적용.

SPEC-SEO-TEXT.md §3 [7] 구현.
2번째 섹션부터 본문을 생성한다.

M2 불변 규칙:
  - 이 파일은 intro 원문 파라미터를 받지 않는다.
  - 허용: intro_tone_hint (str, 힌트만)
  - 프롬프트에도 intro 원문을 삽입하지 않는다.
  - 최종 조립은 composer/assembler.py 가 수행한다.

프롬프트는 prompt_builder 단일 진입점에서 빌드한다.
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from domain.analysis.pattern_card import PatternCard
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.usage import ApiUsage, record_usage
from domain.generation.model import BodyResult, BodySection, Outline
from domain.generation.prompt_builder import build_body_prompt

logger = logging.getLogger(__name__)


def generate_body(
    outline_without_intro: Outline,
    intro_tone_hint: str,
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
) -> BodyResult:
    """[7] 본문 생성 (2번째 섹션부터).

    Args:
        outline_without_intro: is_intro=True 섹션이 제거된 Outline.
        intro_tone_hint: 톤 힌트 문자열 (예: "공감형, 친근한 톤 유지").
        pattern_card: 분석 결과 패턴 카드.
        compliance_rules: 의료법 사전 규칙 (None 이면 기본값).

    Returns:
        BodyResult: 2번째 섹션부터의 본문.
    """
    messages, tool_schema = build_body_prompt(
        outline_without_intro, intro_tone_hint, pattern_card, compliance_rules
    )

    client = build_client()
    response = messages_create_with_retry(
        client,
        model=settings.model_opus,
        max_tokens=8192,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=messages,
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
    return _parse_body(tool_input)


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (body)")


def _parse_body(data: dict[str, Any]) -> BodyResult:
    """tool_use 응답 -> BodyResult Pydantic 모델."""
    sections = [BodySection(**s) for s in data.get("body_sections", [])]
    return BodyResult(body_sections=sections)
