"""프롬프트 빌더 — generation 도메인 단일 진입점.

모든 LLM 프롬프트는 이 파일에서만 빌드한다.
outline_writer.py, body_writer.py 는 직접 프롬프트를 조립하지 않는다.
의료법 규칙 주입(1차 방어)도 이 파일에서만 발생한다.

SPEC-SEO-TEXT.md §3 [6][7], .claude/skills/generation/SKILL.md 참조.
"""

from __future__ import annotations

import logging
from typing import Any

from domain.analysis.model import SECTION_ROLES
from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline, OutlineSection

logger = logging.getLogger(__name__)


# ── tool_use JSON 스키마 ──


OUTLINE_TOOL: dict[str, Any] = {
    "name": "record_outline",
    "description": "SEO 원고 아웃라인 + 도입부 + image_prompts 를 기록한다.",
    "input_schema": {
        "type": "object",
        "required": [
            "title",
            "title_pattern",
            "target_chars",
            "suggested_tags",
            "image_prompts",
            "intro",
            "sections",
            "keyword_plan",
        ],
        "properties": {
            "title": {"type": "string"},
            "title_pattern": {
                "type": "string",
                "enum": ["질문형", "숫자형", "감정형", "방법론형"],
            },
            "target_chars": {"type": "integer", "minimum": 0},
            "suggested_tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "image_prompts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "sequence",
                        "position",
                        "prompt",
                        "alt_text",
                        "image_type",
                        "rationale",
                    ],
                    "properties": {
                        "sequence": {"type": "integer", "minimum": 1},
                        "position": {"type": "string"},
                        "prompt": {"type": "string"},
                        "alt_text": {"type": "string"},
                        "image_type": {
                            "type": "string",
                            "enum": [
                                "photo",
                                "illustration",
                                "infographic",
                                "diagram",
                            ],
                        },
                        "rationale": {"type": "string"},
                    },
                },
            },
            "intro": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["index", "role", "subtitle"],
                    "properties": {
                        "index": {"type": "integer", "minimum": 1},
                        "role": {"type": "string", "enum": SECTION_ROLES},
                        "subtitle": {"type": "string"},
                        "summary": {"type": "string"},
                        "target_chars": {"type": "integer", "minimum": 0},
                        "dia_markers": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "is_intro": {"type": "boolean"},
                    },
                },
            },
            "keyword_plan": {
                "type": "object",
                "required": [
                    "main_keyword_target_count",
                    "subtitle_inclusion_target",
                ],
                "properties": {
                    "main_keyword_target_count": {
                        "type": "integer",
                        "minimum": 0,
                    },
                    "subtitle_inclusion_target": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        },
    },
}


BODY_TOOL: dict[str, Any] = {
    "name": "record_body",
    "description": "SEO 원고 본문 섹션들을 기록한다.",
    "input_schema": {
        "type": "object",
        "required": ["body_sections"],
        "properties": {
            "body_sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["index", "subtitle", "content_md"],
                    "properties": {
                        "index": {"type": "integer", "minimum": 1},
                        "subtitle": {"type": "string"},
                        "content_md": {"type": "string"},
                    },
                },
            },
        },
    },
}


# ── 프롬프트 빌드 함수 ──


def build_outline_prompt(
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """[6] 아웃라인+도입부+image_prompts 프롬프트 빌드.

    Returns:
        (messages, tool_schema) 튜플.
    """
    pc = pattern_card
    system = _build_outline_system(pc, compliance_rules)
    user = "위 지시에 따라 record_outline 도구로 아웃라인을 기록하라."
    messages: list[dict[str, str]] = [
        {"role": "user", "content": f"[시스템 지시]\n{system}\n\n{user}"},
    ]
    return messages, OUTLINE_TOOL


def build_body_prompt(
    outline_without_intro: Outline,
    intro_tone_hint: str,
    pattern_card: PatternCard,
    compliance_rules: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """[7] 본문 프롬프트 빌드. M2: intro 원문 미포함.

    Returns:
        (messages, tool_schema) 튜플.
    """
    system = _build_body_system(
        outline_without_intro, intro_tone_hint, pattern_card, compliance_rules
    )
    user = "위 지시에 따라 record_body 도구로 본문을 기록하라."
    messages: list[dict[str, str]] = [
        {"role": "user", "content": f"[시스템 지시]\n{system}\n\n{user}"},
    ]
    return messages, BODY_TOOL


# ── 내부 헬퍼 ──


def _build_outline_system(
    pc: PatternCard,
    compliance_rules: str | None,
) -> str:
    """[6] 시스템 프롬프트 조립."""
    sections = pc.sections
    stats = pc.stats
    reader = pc.target_reader
    tags = pc.aggregated_tags
    appeal = pc.aggregated_appeal_points
    dia = pc.dia_plus

    top_structures_str = _format_top_structures(pc)
    dia_instructions = _format_dia_instructions(dia)
    compliance_block = _format_compliance(compliance_rules)
    tag_block = _format_tag_instructions(tags)
    image_block = _format_image_instructions()

    intro_type = _select_intro_type(pc.distributions)

    return (
        "너는 네이버 블로그 SEO 전문 콘텐츠 기획자다.\n"
        "상위 노출 글의 분석 데이터를 기반으로 검색 최적화된 "
        "아웃라인을 작성한다.\n"
        "특정 업체를 홍보하거나 광고하는 내용을 포함하지 않는다.\n\n"
        f"[상위 글 구조]\n{top_structures_str}\n"
        f"필수 섹션: {sections.required}\n"
        f"빈출 섹션: {sections.frequent}\n"
        f"차별화 가능 (최대 2개 선택): {sections.differentiating}\n\n"
        f"[타겟 독자]\n"
        f"고민: {reader.concerns}\n"
        f"검색 의도: {reader.search_intent}\n"
        f"정보 수준: {reader.expertise_level}\n\n"
        f"[구조 규칙]\n"
        f"총 글자수: {stats.chars.min:.0f}~{stats.chars.max:.0f}자\n"
        f"소제목: {stats.subtitles.avg:.0f}개\n"
        f"도입 방식: {intro_type}\n\n"
        f"[DIA+ 요소 지시]\n{dia_instructions}\n\n"
        f"[키워드]\n"
        f"주: {pc.keyword}\n"
        f"연관: {pc.related_keywords}\n"
        f"목표 밀도: {stats.keyword_density.avg:.3f}\n"
        f"소제목 포함율 목표: {stats.subtitle_keyword_ratio}\n\n"
        f"[소구 포인트 중립화]\n"
        "아래는 상위 글이 공통적으로 강조하는 가치다. "
        "업체 주체가 아닌 일반화된 정보로 재서술하라.\n"
        f"공통 소구 포인트: {appeal.common}\n\n"
        f"{tag_block}\n\n"
        f"{image_block}\n\n"
        f"{compliance_block}\n\n"
        "[핵심 지시]\n"
        "1. 필수 섹션 모두 포함 + 차별화 섹션 0~2개 추가\n"
        "2. 상위 글 구조를 참조하되 그대로 복제하지 말 것\n"
        "3. 도입부 본문 200~300자를 확정본으로 작성 "
        "(본문 생성 단계에서 재생성하지 않음)\n"
        "4. 업체명/브랜드명/1인칭 표현 금지\n"
        "5. 리스트를 중첩하지 말 것. "
        "하위 분류 필요 시 별도 섹션이나 소제목으로 분리"
    )


def _build_body_system(
    outline: Outline,
    intro_tone_hint: str,
    pc: PatternCard,
    compliance_rules: str | None,
) -> str:
    """[7] 시스템 프롬프트 조립. M2: intro 원문 미포함."""
    stats = pc.stats
    sections_text = _format_body_sections(outline.sections)
    dia_markers = _collect_dia_markers(outline.sections)
    compliance_block = _format_compliance(compliance_rules)

    return (
        "아래 아웃라인을 기반으로 블로그 본문을 작성한다.\n"
        "이미 작성된 글의 첫 부분이 있으므로 다시 작성하지 않는다.\n"
        "2번째 섹션부터 작성하며, 중립적 정보 콘텐츠로 서술한다.\n\n"
        f"[톤 힌트]\n{intro_tone_hint}\n"
        "이어지는 본문은 동일한 톤을 유지할 것.\n\n"
        f"[아웃라인 (2번째 섹션부터)]\n{sections_text}\n\n"
        f"[키워드 배치 규칙]\n"
        f'주 키워드 "{pc.keyword}":\n'
        f"  - 소제목 "
        f"{outline.keyword_plan.subtitle_inclusion_target * 100:.0f}% "
        "이상 포함\n"
        f"  - 전체 밀도 {stats.keyword_density.avg:.3f}\n"
        f"연관 키워드: {pc.related_keywords} - 자연스럽게 분산\n"
        '일반화 부사("일반적으로", "보통", "대부분") '
        "단락당 1회 이내\n\n"
        f"[문단 규칙]\n"
        f"문단당 {stats.paragraph_avg_chars:.0f}자 내외\n\n"
        f"[DIA+ 요소 삽입 지시]\n{dia_markers}\n\n"
        "[금지 사항]\n"
        "- 업체명/브랜드명 언급 금지\n"
        '- "저희", "우리 병원" 등 1인칭 금지\n'
        "- CTA (예약, 전화, 상담) 표현 금지\n"
        "- 리스트를 중첩하지 말 것. "
        "하위 분류 필요 시 별도 섹션이나 소제목으로 분리\n"
        f"{compliance_block}\n\n"
        "[출력 지시]\n"
        "각 섹션을 순서대로 생성할 것."
    )


def _format_top_structures(pc: PatternCard) -> str:
    lines: list[str] = []
    for ts in pc.top_structures[:3]:
        lines.append(f"  {ts.rank}위: {' -> '.join(ts.sequence)}")
    return "\n".join(lines) if lines else "(없음)"


def _format_dia_instructions(dia: dict[str, float]) -> str:
    lines: list[str] = []
    table_ratio = dia.get("tables", 0.0)
    if table_ratio > 0.5:
        lines.append("- 표 1개 이상 포함")
    qa_ratio = dia.get("qa_sections", 0.0)
    if qa_ratio > 0.5:
        lines.append("- Q&A 섹션 포함")
    list_ratio = dia.get("lists", 0.0)
    if list_ratio > 0.7:
        lines.append("- 리스트 2개 이상 포함")
    stats_ratio = dia.get("statistics", 0.0)
    if stats_ratio > 0.5:
        lines.append("- 통계 데이터 최소 2회 포함")
    return "\n".join(lines) if lines else "- 특별 지시 없음"


def _format_compliance(rules: str | None) -> str:
    if not rules:
        return (
            "[의료법 사전 규칙]\n"
            "- 치료 효과 보장 표현 금지\n"
            '- 비교/우위 표현 금지 ("최고", "유일한", "가장 좋은")\n'
            "- 전후 사진 언급 시 주의\n"
            '- 1인칭 ("저희", "우리 병원") 금지'
        )
    return f"[의료법 사전 규칙]\n{rules}"


def _format_tag_instructions(tags: Any) -> str:
    avg_count = tags.avg_tag_count_per_post
    return (
        "[SEO 태그 제안]\n"
        f"상위 글 공통 태그(80%+): {tags.common}\n"
        f"빈출 태그(50%+): {tags.frequent}\n"
        f"평균 태그 개수: {avg_count}\n\n"
        "suggested_tags 필드에 태그 리스트를 출력하라. "
        "개수는 분석 결과 그대로 따른다:\n"
        f"- 목표 개수 = round({avg_count}) = {round(avg_count)}\n"
        "- Naver 물리적 상한(30개)만 예외 처리\n"
        "- 채우는 순서: (a) common 태그 전부 -> "
        "(b) frequent 태그에서 관련도 높은 순 -> "
        "(c) 주 키워드/연관 키워드 중 없는 1~2개\n"
        "- 중복 제거, 의료법 금지 표현 배제"
    )


def _format_image_instructions() -> str:
    return (
        "[AI 이미지 prompt 생성]\n"
        "image_prompts 필드에 이미지 prompt 리스트를 출력하라. "
        "개수는 3개를 기본으로 한다.\n\n"
        "각 prompt 규칙:\n"
        "1. 언어: 영어\n"
        "2. 텍스트 절대 금지 - no text, no letters 명시\n"
        "3. 인물 등장 시 Korean 키워드 필수 "
        "(예: Korean woman, Korean man)\n"
        "4. 의료 맥락 금지 - patient, before/after, "
        "medical procedure, surgery, injection, "
        "body comparison, naked 등\n"
        "5. 권장 시나리오: 한식, 한방 재료, 한국 자연, "
        "라이프스타일(요가, 산책, 명상)\n"
        "6. 권장 스타일: realistic photography, "
        "lifestyle photography, flat illustration, "
        "minimalist infographic\n"
        "7. 종횡비: 1024x1024\n"
        "8. 각 prompt 에 반드시 포함: 스타일 1개 + "
        "시나리오 + 색감 + no text (인물 시 Korean)"
    )


def _select_intro_type(distributions: dict[str, dict[str, float]]) -> str:
    intro_dist = distributions.get("intro_type", {})
    if not intro_dist:
        return "공감형"
    return max(intro_dist, key=lambda k: intro_dist[k])


def _format_body_sections(sections: list[OutlineSection]) -> str:
    lines: list[str] = []
    for s in sections:
        markers = f" [DIA+: {', '.join(s.dia_markers)}]" if s.dia_markers else ""
        lines.append(
            f"섹션 {s.index}: [{s.role}] {s.subtitle}\n"
            f"  요약: {s.summary}\n"
            f"  목표 글자수: {s.target_chars}자{markers}"
        )
    return "\n".join(lines) if lines else "(없음)"


def _collect_dia_markers(sections: list[OutlineSection]) -> str:
    markers: list[str] = []
    for s in sections:
        for m in s.dia_markers:
            if m == "table":
                markers.append(f"- 섹션 {s.index}에 표 삽입")
            elif m == "list":
                markers.append(f"- 섹션 {s.index}에 리스트 삽입 (중첩 금지)")
            elif m == "statistics":
                markers.append(f"- 섹션 {s.index}에 통계 데이터 포함")
            elif m == "qa":
                markers.append(f"- 섹션 {s.index}에 Q&A 포함")
            elif m == "blockquote":
                markers.append(f"- 섹션 {s.index}에 인용구 삽입")
            else:
                markers.append(f"- 섹션 {s.index}에 {m} 삽입")
    return "\n".join(markers) if markers else "- 특별 지시 없음"
