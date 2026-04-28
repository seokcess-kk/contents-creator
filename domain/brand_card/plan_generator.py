"""[B5] 카드 기획안 생성 — LLM tool_use 로 구조화 출력.

asset_merge.MergedAssets + reuse_guard.ReuseCheckResult 통합 호출 후
BRAND_LENIENT 룰을 프롬프트에 사전 주입(1차 방어)한다.
이미지 생성·렌더 호출 없음 — 텍스트 기획안만 생성, status=draft.

SPEC-BRAND-CARD §11 (모델) + §12 [B5] + §7 (표현 강도) + §8 (BRAND_LENIENT)
구현. SEO 트랙 prompt_builder 와 분리 (도메인 격리).
"""

from __future__ import annotations

import logging
from typing import Any

from anthropic.types import (
    Message,
    TextBlockParam,
    ToolParam,
    ToolUseBlock,
)

from config.settings import settings
from domain.brand_card.asset_merge import MergedAssets
from domain.brand_card.model import (
    BrandCardError,
    BrandCardPlan,
    CardBlock,
)
from domain.brand_card.reuse_guard import ReuseCheckResult
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.usage import ApiUsage, record_usage
from domain.compliance.rules import CompliancePolicy, get_rules

logger = logging.getLogger(__name__)


_TOOL_NAME = "submit_brand_card_plan"


class PlanGenerationError(BrandCardError):
    """LLM 응답이 tool_use 누락 또는 schema 위반."""


def generate_brand_card_plan(
    *,
    brand_id: str,
    keyword: str,
    strategy: str,
    expression_level: str,
    template_id: str,
    merged_assets: MergedAssets,
    reuse_check: ReuseCheckResult,
    reuse_group_id: str | None = None,
) -> BrandCardPlan:
    """카드 기획안 1건 생성 (단일 strategy/template).

    여러 variant 는 application 레이어가 본 함수를 N회 호출 + 다른 strategy
    조합. 반환된 plan 의 status=draft — 사용자 승인 게이트 통과 전까지
    이미지 생성·렌더 호출 금지 (D3).
    """
    system = _build_system_prompt(expression_level)
    user = _build_user_prompt(
        keyword=keyword,
        strategy=strategy,
        template_id=template_id,
        expression_level=expression_level,
        merged_assets=merged_assets,
        reuse_check=reuse_check,
    )
    tool_schema = _build_tool_schema()

    response = _invoke(system=system, user=user, tool_schema=tool_schema)
    tool_input = _extract_tool_input(response)
    return _parse_plan(
        tool_input,
        brand_id=brand_id,
        keyword=keyword,
        strategy=strategy,
        expression_level=expression_level,
        template_id=template_id,
        reuse_group_id=reuse_group_id,
    )


# ── 프롬프트 빌더 ─────────────────────────────────────────────


def _build_system_prompt(expression_level: str) -> str:
    """시스템 프롬프트 — BRAND_LENIENT 룰 + 표현 강도 가이드."""
    compliance_text = _format_compliance_rules()
    expression_guide = _format_expression_guide(expression_level)
    return (
        "당신은 한국 의료 브랜드 카드 기획자다. 주어진 키워드와 브랜드 자산으로 "
        "신뢰·전환을 보조하는 4~6장의 카드 기획안을 만든다.\n\n"
        "🔴 의료광고법 BRAND_LENIENT 정책 — 다음 표현은 절대 사용 금지:\n"
        f"{compliance_text}\n\n"
        f"🎯 표현 강도: {expression_level}\n"
        f"{expression_guide}\n\n"
        "🔧 출력 규약: submit_brand_card_plan tool 을 호출해 구조화된 결과만 반환. "
        "자유 텍스트·마크다운·설명 없음."
    )


def _format_compliance_rules() -> str:
    """BRAND_LENIENT 룰 (9종) 의 description 을 bullet 형식으로."""
    rules = get_rules(CompliancePolicy.BRAND_LENIENT)
    lines = [f"- {r.description}" for r in rules]
    return "\n".join(lines)


def _format_expression_guide(level: str) -> str:
    """SPEC §7 표현 강도별 가이드."""
    if level == "safe":
        return "병원 홈페이지 수준의 안정적 표현. 차별점·진료 원칙·전문성 위주, 감정 자극 자제."
    if level == "hooking":
        return (
            "문제 자극·공감형 질문·실패 경험·생활 패턴 강조 허용. "
            "예: '계속 실패했다면 방식부터 바꿔야 할 때'. "
            "단, 효과 보장·수치 감량·전후 비교 등은 여전히 금지."
        )
    return "신뢰와 후킹 균형. 차별점 + 공감 멘트 혼합."


def _build_user_prompt(
    *,
    keyword: str,
    strategy: str,
    template_id: str,
    expression_level: str,
    merged_assets: MergedAssets,
    reuse_check: ReuseCheckResult,
) -> str:
    """사용자 프롬프트 — 자산 우선순위 + 키워드 + 전략 + reuse 제약."""
    parts: list[str] = [
        f"[키워드] {keyword}",
        f"[전략] {strategy}",
        f"[템플릿] {template_id}",
        f"[표현 강도] {expression_level}",
    ]
    parts.append(_format_assets(merged_assets))
    parts.append(_format_reuse_constraints(reuse_check, merged_assets))
    parts.append(
        "위 자산을 우선순위 순서대로 반영해 4~6장의 카드 기획안을 만들고, "
        "submit_brand_card_plan tool 로 반환하라. 의료진/시설/장비 묘사는 "
        "image_asset_id 로만 참조 (AI 생성 금지). 추상 일러스트·아이콘·배경만 "
        "ai_image_prompt 사용."
    )
    return "\n\n".join(parts)


def _format_assets(m: MergedAssets) -> str:
    """SPEC §6 우선순위로 자산 단락 구성. 빈 단락은 명시적으로 표기."""
    sections: list[str] = []
    if m.user_brief:
        sections.append(f"[1순위 — 사용자 직접 입력]\n{m.user_brief}")
    if m.attached_files:
        joined = "\n\n".join(m.attached_files)
        sections.append(f"[2순위 — 첨부 파일]\n{joined}")
    if m.brand_common:
        joined = "\n\n".join(m.brand_common)
        sections.append(f"[3순위 — 브랜드 공통 자산]\n{joined}")
    if m.other_references:
        joined = "\n\n".join(m.other_references)
        sections.append(f"[4순위 — 기타 참고 자산]\n{joined}")
    if m.required_phrases:
        sections.append(f"[필수 포함 문구] {', '.join(m.required_phrases)}")
    if m.forbidden_phrases:
        sections.append(f"[추가 금지 문구] {', '.join(m.forbidden_phrases)}")
    if not sections:
        return "[자산 없음 — 키워드와 전략만으로 기획]"
    return "\n\n".join(sections)


def _format_reuse_constraints(rc: ReuseCheckResult, m: MergedAssets) -> str:
    """reuse_guard 결과를 LLM 제약 문구로 변환."""
    parts: list[str] = []
    if rc.blocked_headlines:
        joined = ", ".join(sorted(rc.blocked_headlines))
        parts.append(f"[차단된 헤드라인 — 30일 내 사용됨, 재사용 금지]\n{joined}")
    if rc.warning_template_id:
        parts.append(
            f"[경고] 템플릿 {rc.warning_template_id} 가 5회 연속 사용됨 — 다른 메시지 각도 권장"
        )
    if rc.warning_strategy:
        parts.append(f"[경고] 전략 {rc.warning_strategy} 가 5회 연속 사용됨 — 변형 필요")
    if rc.warning_overused_photo_ids:
        joined = ", ".join(sorted(rc.warning_overused_photo_ids))
        parts.append(f"[경고] 의료진 사진 {joined} 가 3 키워드 초과 사용됨 — 다른 사진 권장")
    if not parts:
        return "[재사용 제약 없음]"
    _ = m  # 향후 m.forbidden_phrases 와 reuse 룰 결합 시 사용 예정
    return "\n\n".join(parts)


# ── tool_use schema ────────────────────────────────────────


def _build_tool_schema() -> ToolParam:
    """submit_brand_card_plan tool — BrandCardPlan 의 LLM 출력 부분만."""
    return {
        "name": _TOOL_NAME,
        "description": "카드 기획안 (4~6 카드 블록) 을 구조화된 형식으로 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "angle": {
                    "type": "string",
                    "description": "이번 카드 세트의 핵심 메시지 각도 (1문장)",
                },
                "blocks": {
                    "type": "array",
                    "minItems": 4,
                    "maxItems": 6,
                    "items": {
                        "type": "object",
                        "properties": {
                            "card_type": {
                                "type": "string",
                                "enum": [
                                    "hero",
                                    "problem",
                                    "solution",
                                    "differentiator",
                                    "process",
                                    "trust_closing",
                                ],
                            },
                            "headline": {"type": "string", "maxLength": 30},
                            "subcopy": {
                                "type": ["string", "null"],
                                "maxLength": 60,
                            },
                            "bullets": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 30},
                                "maxItems": 5,
                            },
                            "image_asset_id": {"type": ["string", "null"]},
                            "ai_image_prompt": {"type": ["string", "null"]},
                            "recommended_position": {
                                "type": "string",
                                "enum": [
                                    "after_intro",
                                    "after_problem",
                                    "mid",
                                    "before_closing",
                                ],
                            },
                        },
                        "required": [
                            "card_type",
                            "headline",
                            "recommended_position",
                        ],
                    },
                },
                "required_phrases_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "forbidden_phrases_avoided": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["angle", "blocks"],
        },
    }


# ── LLM 호출 + 응답 파싱 ────────────────────────────────────


def _invoke(
    *,
    system: str,
    user: str,
    tool_schema: ToolParam,
) -> Message:
    """Sonnet + tool_use 강제. usage 기록."""
    client = build_client()
    system_blocks: list[TextBlockParam] = [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    response = messages_create_with_retry(
        client,
        model=settings.model_sonnet,
        max_tokens=4096,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )
    record_usage(
        ApiUsage(
            provider="anthropic",
            model=settings.model_sonnet,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    )
    return response


def _extract_tool_input(response: Message) -> dict[str, Any]:
    for block in response.content:
        if isinstance(block, ToolUseBlock) and block.name == _TOOL_NAME:
            return dict(block.input) if isinstance(block.input, dict) else {}
    raise PlanGenerationError(
        f"LLM 응답에 {_TOOL_NAME} tool_use 블록 없음. stop_reason={response.stop_reason}"
    )


def _parse_plan(
    tool_input: dict[str, Any],
    *,
    brand_id: str,
    keyword: str,
    strategy: str,
    expression_level: str,
    template_id: str,
    reuse_group_id: str | None,
) -> BrandCardPlan:
    """tool_use 응답 → BrandCardPlan Pydantic 인스턴스."""
    angle = tool_input.get("angle")
    blocks_raw = tool_input.get("blocks")
    if not isinstance(angle, str) or not isinstance(blocks_raw, list):
        raise PlanGenerationError(
            f"tool_input 필수 필드 누락: angle={angle!r} blocks_type={type(blocks_raw)}"
        )
    blocks = [_parse_block(b) for b in blocks_raw]
    return BrandCardPlan(
        brand_id=brand_id,
        keyword=keyword,
        strategy=strategy,
        expression_level=expression_level,
        template_id=template_id,
        angle=angle,
        blocks=blocks,
        required_phrases_used=list(tool_input.get("required_phrases_used") or []),
        forbidden_phrases_avoided=list(tool_input.get("forbidden_phrases_avoided") or []),
        reuse_group_id=reuse_group_id,
        status="draft",
    )


def _parse_block(d: dict[str, Any]) -> CardBlock:
    return CardBlock(
        card_type=d["card_type"],
        headline=d["headline"],
        subcopy=d.get("subcopy"),
        bullets=list(d.get("bullets") or []),
        image_asset_id=d.get("image_asset_id"),
        ai_image_prompt=d.get("ai_image_prompt"),
        recommended_position=d["recommended_position"],
    )
