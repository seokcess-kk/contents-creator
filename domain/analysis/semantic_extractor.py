"""[4a] 의미적 구조 추출 (LLM, Sonnet 4.6).

SPEC-SEO-TEXT.md §3 [4a] 구현. 각 블로그 글의 섹션별 역할과
독자 특성을 분류한다. [4b] 와 분리된 별도 LLM 호출.

Anthropic SDK tool_use 로 JSON 스키마 강제. 텍스트 "JSON 답해" 금지.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.analysis.model import (
    SECTION_ROLES,
    SectionSemantic,
    SemanticAnalysis,
    TargetReader,
)
from domain.analysis.physical_extractor import extract_body_text
from domain.crawler.model import BlogPage

logger = logging.getLogger(__name__)

_MAX_BODY_CHARS = 6000

SEMANTIC_TOOL = {
    "name": "record_semantic_analysis",
    "description": "블로그 글의 의미적 구조 분석 결과를 기록한다.",
    "input_schema": {
        "type": "object",
        "required": [
            "semantic_structure",
            "title_pattern",
            "hook_type",
            "target_reader",
            "depth_assessment",
        ],
        "properties": {
            "semantic_structure": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["section", "role", "summary", "depth"],
                    "properties": {
                        "section": {"type": "integer", "minimum": 1},
                        "role": {
                            "type": "string",
                            "enum": SECTION_ROLES,
                        },
                        "summary": {"type": "string"},
                        "depth": {
                            "type": "string",
                            "enum": ["표면적", "중간", "전문적"],
                        },
                    },
                },
            },
            "title_pattern": {
                "type": "string",
                "enum": ["질문형", "숫자형", "감정형", "방법론형"],
            },
            "hook_type": {
                "type": "string",
                "enum": ["공감형", "통계형", "질문형", "스토리형"],
            },
            "target_reader": {
                "type": "object",
                "required": ["concerns", "search_intent", "expertise_level"],
                "properties": {
                    "concerns": {"type": "array", "items": {"type": "string"}},
                    "search_intent": {"type": "string"},
                    "expertise_level": {"type": "string"},
                },
            },
            "depth_assessment": {"type": "string"},
        },
    },
}


def extract_semantic(
    page: BlogPage,
    title: str,
    subtitle_count: int,
    main_keyword: str,
) -> SemanticAnalysis:
    """단일 블로그의 의미적 구조를 분석한다 (Sonnet 4.6, tool_use).

    예외 발생 시 호출자(stage_runner) 가 catch 해 해당 블로그를 스킵한다.
    """
    body_text = extract_body_text(page)
    if len(body_text) > _MAX_BODY_CHARS:
        body_text = body_text[:_MAX_BODY_CHARS] + "\n[이하 생략]"

    messages = _build_messages(title, body_text, subtitle_count, main_keyword)

    client = anthropic.Anthropic(api_key=require("anthropic_api_key"))
    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_sonnet,
        max_tokens=2048,
        tools=[SEMANTIC_TOOL],
        tool_choice={"type": "tool", "name": SEMANTIC_TOOL["name"]},
        messages=messages,
    )

    tool_input = _extract_tool_input(response)
    return _parse_response(tool_input, str(page.url))


def _build_messages(
    title: str,
    body_text: str,
    subtitle_count: int,
    main_keyword: str,
) -> list[dict[str, str]]:
    subtitle_guide = (
        "이 글은 소제목이 없이 작성된 단일 본문입니다. "
        "글 전체를 하나의 섹션으로 보고 가장 적합한 역할 1개를 부여하세요."
        if subtitle_count == 0
        else f"이 글은 소제목이 {subtitle_count}개 있습니다. "
        "각 소제목 구간을 하나의 섹션으로 분류하세요."
    )
    system = (
        "너는 네이버 블로그 콘텐츠 분석가다. "
        "블로그 글의 섹션별 역할, 독자 특성, 제목 패턴, 도입부 훅 유형을 분류한다."
    )
    user = (
        f"키워드: {main_keyword}\n"
        f"제목: {title}\n"
        f"{subtitle_guide}\n\n"
        f"--- 본문 ---\n{body_text}\n--- 끝 ---\n\n"
        "위 블로그 글을 분석하여 record_semantic_analysis 도구로 결과를 기록하라."
    )
    return [
        {"role": "user", "content": f"[시스템 지시]\n{system}\n\n{user}"},
    ]


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출. 없으면 ValueError."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (semantic)")


def _parse_response(tool_input: dict[str, Any], url: str) -> SemanticAnalysis:
    sections = [SectionSemantic(**s) for s in tool_input.get("semantic_structure", [])]
    tr = tool_input.get("target_reader", {})
    return SemanticAnalysis(
        url=url,  # type: ignore[arg-type]
        semantic_structure=sections,
        title_pattern=tool_input["title_pattern"],
        hook_type=tool_input["hook_type"],
        target_reader=TargetReader(**tr),
        depth_assessment=str(tool_input.get("depth_assessment", "")),
    )
