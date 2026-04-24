"""[7] 본문 생성 (Sonnet 초안 + 약한 섹션 Opus 보정). M2 불변 + 섹션 병렬.

SPEC-SEO-TEXT.md §3 [7] 구현.
2번째 섹션부터 각 섹션을 **병렬**로 생성한다.

비용 최적화: 초안은 `settings.model_sonnet`, body_quality_enforcer 가 약한
섹션만 `settings.model_editor`(Opus) 로 재작성 (하이브리드). SEO 품질은 구조·
키워드 배치·약한 단락 보정에 좌우되므로 초안을 Opus 로 쓰는 것은 과투자였다.

M2 불변 규칙:
  - 이 파일은 intro 원문 파라미터를 받지 않는다.
  - 허용: intro_tone_hint (str, 힌트만)
  - 프롬프트에도 intro 원문을 삽입하지 않는다.
  - 최종 조립은 composer/assembler.py 가 수행한다.

병렬 전략:
  - 섹션별 독립 호출 (ThreadPool 4 워커 기본)
  - 공용 system 블록에 Anthropic Prompt Caching 적용 → 섹션 수-1 만큼 cache hit
  - 각 섹션이 max_tokens 3000 수준으로 충분. 전체 지연 ~40~60% 단축 기대
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config.settings import settings
from domain.analysis.pattern_card import PatternCard
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.usage import ApiUsage, record_usage
from domain.generation.model import BodyResult, BodySection, Outline, OutlineSection
from domain.generation.prompt_builder import build_body_section_prompt

logger = logging.getLogger(__name__)

_SECTION_MAX_TOKENS = 3000
_DEFAULT_PARALLEL_WORKERS = 4


def generate_body(
    outline_without_intro: Outline,
    intro_tone_hint: str,
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
) -> BodyResult:
    """[7] 본문 생성 — 섹션별 병렬 호출 후 index 순 조합.

    Args:
        outline_without_intro: is_intro=True 섹션이 제거된 Outline.
        intro_tone_hint: 톤 힌트 문자열.
        pattern_card: 분석 결과 패턴 카드.
        compliance_rules: 의료법 사전 규칙 (None 이면 기본값).

    Returns:
        BodyResult: index 오름차순 정렬된 본문 섹션.
    """
    sections = outline_without_intro.sections
    if not sections:
        return BodyResult(body_sections=[])

    workers = min(_DEFAULT_PARALLEL_WORKERS, len(sections))
    logger.info("body_generation.parallel sections=%d workers=%d", len(sections), workers)

    results: dict[int, BodySection] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _generate_section,
                section,
                outline_without_intro,
                intro_tone_hint,
                pattern_card,
                compliance_rules,
            ): section
            for section in sections
        }
        for future in as_completed(futures):
            section = futures[future]
            try:
                body_section = future.result()
                results[body_section.index] = body_section
            except Exception:
                logger.exception("body section failed index=%d", section.index)
                raise

    ordered = [results[s.index] for s in sections if s.index in results]
    return BodyResult(body_sections=ordered)


def _generate_section(
    section: OutlineSection,
    outline: Outline,
    intro_tone_hint: str,
    pattern_card: PatternCard,
    compliance_rules: str | None,
) -> BodySection:
    """단일 섹션을 Sonnet 으로 초안 생성한다 (하이브리드 초안).

    품질이 기준 미달이면 `body_quality_enforcer` + `_fix_weak_sections` 가
    `settings.model_editor` (Opus) 로 해당 섹션만 재작성한다.
    """
    shared_system, messages, tool_schema = build_body_section_prompt(
        section, outline, intro_tone_hint, pattern_card, compliance_rules
    )

    client = build_client()
    response = messages_create_with_retry(
        client,
        model=settings.model_sonnet,
        max_tokens=_SECTION_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": shared_system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=messages,
    )
    record_usage(
        ApiUsage(
            provider="anthropic",
            model=settings.model_sonnet,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    )
    tool_input = _extract_tool_input(response)
    # LLM 이 index 를 다르게 반환할 수 있어 outline 기준으로 보정
    tool_input["index"] = section.index
    return BodySection(**tool_input)


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (body)")
