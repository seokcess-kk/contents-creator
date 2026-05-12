"""[4c] 사용자 의도(intent) 추출 (LLM, Haiku 4.5).

SPEC-SEO-TEXT.md §3 [4c] 구현 (P1, 2026-05-12 추가).
[4a] 의미 분석 + [4b] 소구 포인트 와 분리된 별도 LLM 호출 — 분리 원칙 준수.

상위 노출 블로그가 답하고 있는 **사용자 진짜 질문/의도** 를 2~5개 추출한다.
키워드 빈도가 아니라 독자가 그 글에서 얻고 싶어한 구체적 결정·정보가 기준.
cross_analyzer 가 페이지별 결과를 빈도순 dedup 후 PatternCard.intents 상위 5개 주입.

모델: settings.model_haiku (Sonnet 대비 ~1/3, Opus 대비 ~1/15 비용).
단순 분류·추출 작업이므로 Haiku 로 충분 (사용자 결정, 2026-05-12).
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from domain.analysis.physical_extractor import extract_body_text
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.usage import ApiUsage, record_usage
from domain.crawler.model import BlogPage

logger = logging.getLogger(__name__)

_MAX_BODY_CHARS = 6000
_MAX_INTENT_CHARS = 60

INTENT_TOOL = {
    "name": "record_user_intents",
    "description": "블로그 글이 답하고 있는 사용자 진짜 질문/의도 2~5개를 기록한다.",
    "input_schema": {
        "type": "object",
        "required": ["intents"],
        "properties": {
            "intents": {
                "type": "array",
                "minItems": 2,
                "maxItems": 5,
                "items": {
                    "type": "string",
                    "maxLength": _MAX_INTENT_CHARS,
                    "description": "독자가 가졌을 구체적 질문/의도 1건. 키워드 단순 재배열 금지.",
                },
            },
        },
    },
}

_SYSTEM_INSTRUCTIONS = """너는 네이버 블로그 상위 노출 글이 **답하고 있는 사용자 진짜 질문/의도** 를 추출하는 분석가다.

[추출 기준]
- 표면 키워드 재배열 금지. 예: "강남 임플란트 추천" 키워드에서 "강남 임플란트 추천이란?" 같은 무의미한 추출 금지.
- 독자가 그 글을 읽고 얻고 싶어한 구체적 결정/정보를 추출한다.
- 좋은 예: "회사 근처 점심시간 진료 가능한가요?", "비용은 얼마인가요?", "보철물 종류별 차이는?"
- 본문에 명시되지 않아도 글 전반의 흐름·강조점에서 합리적으로 추론 가능하면 포함.
- 의료법 위반 표현(완치·최고·100% 등) 은 의도에 포함 금지. 중립적 질문 형태로 표현.

[개수]
- 2~5개. 글이 다루는 의도가 1개뿐이면 2개까지만 (관련 의도 1개 추가). 5개 초과 금지.

[형식]
- 한국어. 60자 이내.
- 의문형 또는 결정형 모두 허용. 예: "비용은 얼마인가요?" / "보철물 종류 선택 기준"

반드시 record_user_intents 도구를 사용해 JSON 으로 기록하라."""


def extract_intents(
    page: BlogPage,
    keyword: str,
) -> list[str]:
    """단일 블로그에서 사용자 의도 2~5개 추출 (Haiku 4.5, tool_use).

    [4a]/[4b]/[4c] 분리 원칙 — 별도 LLM 호출. 실패 시 빈 리스트 반환
    (graceful — raise 금지, 파이프라인 계속).
    """
    body_text = extract_body_text(page)
    if len(body_text) > _MAX_BODY_CHARS:
        body_text = body_text[:_MAX_BODY_CHARS] + "\n[이하 생략]"

    user_content = _build_user_content(keyword, body_text)

    try:
        client = build_client()
        response = messages_create_with_retry(
            client,
            model=settings.model_haiku,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_INSTRUCTIONS,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[INTENT_TOOL],
            tool_choice={"type": "tool", "name": INTENT_TOOL["name"]},
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception:
        logger.warning("intent_extraction.failed url=%s", page.url, exc_info=True)
        return []

    record_usage(
        ApiUsage(
            provider="anthropic",
            model=settings.model_haiku,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    )

    tool_input = _try_extract_tool_input(response)
    if tool_input is None:
        return []
    return _parse_intents(tool_input)


def _build_user_content(keyword: str, body_text: str) -> str:
    return f"키워드: {keyword}\n\n--- 본문 ---\n{body_text}\n--- 끝 ---"


def _try_extract_tool_input(response: Any) -> dict[str, Any] | None:
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    return None


def _parse_intents(tool_input: dict[str, Any]) -> list[str]:
    """tool_use 응답에서 intents 리스트 추출. 잘못된 형식이면 빈 리스트."""
    raw = tool_input.get("intents")
    if not isinstance(raw, list):
        return []
    intents: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned or len(cleaned) > _MAX_INTENT_CHARS:
            continue
        intents.append(cleaned)
    return intents[:5]
