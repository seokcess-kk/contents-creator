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
    plan = _parse_plan(
        tool_input,
        brand_id=brand_id,
        keyword=keyword,
        strategy=strategy,
        expression_level=expression_level,
        template_id=template_id,
        reuse_group_id=reuse_group_id,
    )
    # 2026-05-11 post-process — LLM 환각 ID / 빈 ai_image_prompt 폴백.
    return _sanitize_image_fields(plan, merged_assets)


def _sanitize_image_fields(plan: BrandCardPlan, merged: MergedAssets) -> BrandCardPlan:
    """블록의 image_asset_id / ai_image_prompt 정합성 후처리.

    1) image_asset_id 가 미디어 라이브러리에 없는 ID 면 None 으로 정정 (환각 제거)
    2) image_asset_id 와 ai_image_prompt 가 둘 다 비어있으면 카드 타입 기반
       default ai_image_prompt 자동 생성 (placeholder 빈 카드 방지).

    renderer 가 image_asset_id 우선 → ai_image_prompt fallback 이라 환각 ID 가
    남아있으면 매칭 실패 후 prompt 도 없어 빈 placeholder 로 떨어졌음.
    """
    valid_ids = {a.id for a in merged.media_assets if a.id}
    fixed_blocks: list[CardBlock] = []
    for b in plan.blocks:
        new_asset_id = b.image_asset_id
        if new_asset_id and new_asset_id not in valid_ids:
            logger.warning(
                "plan_generator.invalid_image_asset_id=%s — None 으로 정정", new_asset_id
            )
            new_asset_id = None
        new_prompt = (b.ai_image_prompt or "").strip() or None
        if new_asset_id is None and new_prompt is None:
            new_prompt = _default_ai_image_prompt(b.card_type)
        fixed_blocks.append(b.model_copy(update={
            "image_asset_id": new_asset_id,
            "ai_image_prompt": new_prompt,
        }))
    return plan.model_copy(update={"blocks": fixed_blocks})


_DEFAULT_AI_IMAGE_PROMPTS: dict[str, str] = {
    "hero": (
        "soft pastel gradient abstract background, calm warm tones, no text, "
        "no people, korean medical aesthetic, minimal"
    ),
    "problem": (
        "abstract muted illustration symbolizing concern and care, soft blues "
        "and beige, no text, no people, korean wellness mood"
    ),
    "solution": (
        "abstract icon-style illustration of holistic care, soft greens, no text, "
        "no people, calm professional medical clinic mood"
    ),
    "differentiator": (
        "minimal abstract emblem representing trust and expertise, premium feel, "
        "no text, no people, korean medical clinic brand"
    ),
    "process": (
        "minimal flat illustration of step-by-step flow, three soft circles, "
        "warm pastel palette, no text, no people"
    ),
    "trust_closing": (
        "soft warm gradient with subtle leaf or seal motif, premium clean look, "
        "no text, no people, korean wellness brand"
    ),
}


def _default_ai_image_prompt(card_type: str) -> str:
    """카드 타입별 안전한 default AI 이미지 prompt (영문, 인물 없음, 텍스트 없음).

    SPEC §12 의 의료 맥락 영구 금지 + Gemini 한글 텍스트 깨짐 방지 정책을
    충족하도록 안전한 추상 표현으로만 구성. compliance.image_prompt 검증을
    통과하도록 'no text, no people' 명시.
    """
    return _DEFAULT_AI_IMAGE_PROMPTS.get(
        card_type,
        "soft abstract pastel illustration, calm tones, no text, no people, "
        "korean wellness brand aesthetic",
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
    parts.append(_format_media_assets(merged_assets))
    parts.append(_format_reuse_constraints(reuse_check, merged_assets))
    parts.append(
        "위 자산을 우선순위 순서대로 반영해 4~6장의 카드 기획안을 만들고, "
        "submit_brand_card_plan tool 로 반환하라. 의료진/시설/장비 묘사는 "
        "image_asset_id 로만 참조 (AI 생성 금지). 추상 일러스트·아이콘·배경만 "
        "ai_image_prompt 사용. "
        # 2026-05-11 강화 — 환각 ID + 빈 ai_image_prompt 동시 차단:
        "[필수 규칙] (1) image_asset_id 는 반드시 위의 [사용 가능한 미디어 자산] "
        "단락에 명시된 ID 중 하나만 사용. 그 목록에 없는 ID 는 절대 만들어내지 말 것. "
        "(2) image_asset_id 가 null 인 모든 블록은 ai_image_prompt 를 반드시 "
        "비어있지 않은 영문 prompt 로 채워야 함 (예: 'soft pastel abstract illustration "
        "of healthy lifestyle, no text, no people, calm colors'). "
        "둘 다 null 또는 빈 문자열인 블록을 만들면 카드 이미지가 빈 placeholder "
        "로 렌더링됨."
    )
    return "\n\n".join(parts)


def _format_media_assets(m: MergedAssets) -> str:
    """LLM 에게 노출할 브랜드 미디어 자산 목록.

    2026-05-11 — 이전엔 LLM 이 미디어 라이브러리 컨텍스트 없이 image_asset_id
    를 채워 환각 ID 가 생성되던 문제 차단. 목록이 비어있으면 그 사실을 명시
    해 LLM 이 모든 블록을 ai_image_prompt 로만 채우도록 유도.
    """
    if not m.media_assets:
        return (
            "[사용 가능한 미디어 자산]\n"
            "(브랜드 미디어 라이브러리가 비어있음 — 모든 블록의 image_asset_id 는 "
            "반드시 null 로 두고, ai_image_prompt 로만 시각 표현)"
        )
    lines = ["[사용 가능한 미디어 자산 (image_asset_id 만 이 목록에서 선택)]"]
    for a in m.media_assets:
        if not a.id:
            continue
        title = a.title or "(제목 없음)"
        type_label = a.type or "other"
        lines.append(f"  - id={a.id} type={type_label} title={title!r}")
    return "\n".join(lines)


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
