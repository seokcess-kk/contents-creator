"""[4b] 소구 포인트 + 홍보성 레벨 추출 (LLM, Sonnet 4.6).

SPEC-SEO-TEXT.md §3 [4b] 구현. [4a] 와 분리된 전용 LLM 호출.
홍보성 글의 "소구 포인트" 를 추출해 [6] 아웃라인에서 중립적 정보로
재서술할 근거를 확보한다.

Anthropic SDK tool_use 로 JSON 스키마 강제.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.analysis.model import AppealAnalysis, AppealPoint
from domain.analysis.physical_extractor import extract_body_text
from domain.common.usage import ApiUsage, record_usage
from domain.crawler.model import BlogPage

logger = logging.getLogger(__name__)

_MAX_BODY_CHARS = 6000

APPEAL_TOOL = {
    "name": "record_appeal_analysis",
    "description": "블로그 글의 소구 포인트와 홍보성 레벨을 기록한다.",
    "input_schema": {
        "type": "object",
        "required": [
            "appeal_points",
            "subject_type",
            "overall_promotional_level",
        ],
        "properties": {
            "appeal_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["point", "section", "promotional_level"],
                    "properties": {
                        "point": {"type": "string"},
                        "section": {"type": "integer", "minimum": 1},
                        "promotional_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                    },
                },
            },
            "subject_type": {
                "type": "string",
                "enum": ["업체 주체", "정보 주체", "혼재"],
            },
            "overall_promotional_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
        },
    },
}

# 고정 system prompt — 페이지마다 동일. Prompt caching 대상.
_SYSTEM_INSTRUCTIONS = """너는 네이버 블로그 콘텐츠 분석가다.
블로그 글에서 업체나 제품이 강조하는 가치, 효과, 차별점을 추출한다.

[소구 포인트(appeal_point) 정의]
업체·제품·서비스가 독자에게 내세우는 판매 포인트·효과·가치 주장. 정보성 문장에서도
독자를 특정 선택지로 유도하는 암시가 있으면 소구 포인트로 간주한다.

[홍보 강도 판정 기준]
- high: "저희가", "우리가", "당사가" 등 업체 주어 명시 + 효과 보장 뉘앙스
  예: "저희 병원은 95% 이상의 만족도를 기록했습니다"
- medium: 업체 직접 지칭은 없지만 특정 브랜드·제품·시설을 은유적으로 강조
  예: "이 시술은 평균 3회만에 효과가 나타납니다"
- low: 일반적 정보 서술. 특정 업체 유도 없음
  예: "이 성분은 보통 혈당 조절에 도움이 된다고 알려져 있습니다"

[주체 유형(subject_type) 판정]
- 업체 주체: 글 전반이 특정 업체·브랜드를 주어로 서술
- 정보 주체: 글 전반이 일반적 정보·현상·개념을 주어로 서술
- 혼재: 두 패턴이 섞인 경우

[전반적 홍보 레벨(overall_promotional_level)]
- high: 글의 50% 이상이 high 등급 소구 포인트
- medium: high/medium 이 섞여 있거나 medium 이 다수
- low: 대부분 low 등급

반드시 record_appeal_analysis 도구를 사용해 JSON 으로 기록하라."""


def extract_appeal(
    page: BlogPage,
    title: str,
    main_keyword: str,
) -> AppealAnalysis:
    """단일 블로그의 소구 포인트 + 홍보성 레벨을 추출 (Sonnet 4.6, tool_use).

    [4a] semantic_extractor 와 완전히 분리된 별도 LLM 호출.
    예외 발생 시 호출자(stage_runner) 가 catch 해 해당 블로그를 스킵한다.
    """
    body_text = extract_body_text(page)
    if len(body_text) > _MAX_BODY_CHARS:
        body_text = body_text[:_MAX_BODY_CHARS] + "\n[이하 생략]"

    user_content = _build_user_content(title, body_text, main_keyword)

    client = anthropic.Anthropic(api_key=require("anthropic_api_key"))
    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_sonnet,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_INSTRUCTIONS,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[APPEAL_TOOL],
        tool_choice={"type": "tool", "name": APPEAL_TOOL["name"]},
        messages=[{"role": "user", "content": user_content}],
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
    return _parse_response(tool_input, str(page.url))


def _build_user_content(
    title: str,
    body_text: str,
    main_keyword: str,
) -> str:
    """페이지별 동적 user 메시지만 조립. system 지시는 _SYSTEM_INSTRUCTIONS (캐시)."""
    return f"키워드: {main_keyword}\n제목: {title}\n\n--- 본문 ---\n{body_text}\n--- 끝 ---"


def _extract_tool_input(response: Any) -> dict[str, Any]:
    """tool_use 블록에서 input 추출."""
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise ValueError("LLM 응답에 tool_use 블록이 없습니다 (appeal)")


def _parse_response(tool_input: dict[str, Any], url: str) -> AppealAnalysis:
    points = [AppealPoint(**p) for p in tool_input.get("appeal_points", [])]
    return AppealAnalysis(
        url=url,  # type: ignore[arg-type]
        appeal_points=points,
        subject_type=tool_input.get("subject_type", "정보 주체"),
        overall_promotional_level=tool_input.get("overall_promotional_level", "low"),
    )
