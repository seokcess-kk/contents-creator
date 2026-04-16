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
                        "aspect_ratio",
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
                        "aspect_ratio": {
                            "type": "string",
                            "enum": ["1:1", "3:4", "4:3", "9:16", "16:9"],
                            "description": "이미지 종횡비",
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
    image_block = _format_image_instructions(pc)

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
    """DIA+ 7개 요소 전체를 커버. 임계값 0.3 (30% 이상 사용 시 지시)."""
    lines: list[str] = []
    if dia.get("tables", 0.0) > 0.3:
        lines.append("- 표 1개 이상 포함")
    if dia.get("qa_sections", 0.0) > 0.3:
        lines.append("- Q&A 섹션 포함")
    if dia.get("lists", 0.0) > 0.3:
        lines.append("- 리스트 2개 이상 포함")
    if dia.get("statistics", 0.0) > 0.3:
        lines.append("- 통계 데이터 최소 2회 포함")
    bold_ratio = dia.get("bold", 0.0)
    if bold_ratio > 0.3:
        instruction = "- 핵심 키워드나 중요 포인트에 **볼드** 처리"
        if bold_ratio > 0.5:
            instruction += " (섹션당 2~3회 권장)"
        lines.append(instruction)
    if dia.get("blockquotes", 0.0) > 0.3:
        lines.append("- 인용구 또는 핵심 요약에 > 인용 블록 사용")
    if dia.get("separators", 0.0) > 0.3:
        lines.append("- 섹션 간 구분선(---) 사용")
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


def _format_image_instructions(pc: PatternCard) -> str:
    avg = pc.image_pattern.avg_count_per_post
    if avg > 0:
        target = max(3, round(avg))  # 하한 3, 상한은 [9] 예산 가드가 제어
        avg_note = f"상위 글 평균 이미지 수: {avg:.1f}개 (실사 포함)\n"
    else:
        target = 3
        avg_note = ""

    position_note = _format_image_position_guide(pc)
    seed_hint = _pick_variation_seed()

    return (
        "[AI 이미지 prompt 생성]\n"
        f"{avg_note}"
        f"AI 생성 이미지 목표 개수: {target}개\n\n"
        "image_prompts 필드에 이미지 prompt 리스트를 출력하라.\n\n"
        f"[이미지 배치 패턴 — 분석 결과 기반]\n{position_note}\n\n"
        "[alt_text SEO 최적화]\n"
        f'- alt_text 에 주 키워드 "{pc.keyword}" 또는 '
        "연관 키워드를 자연스럽게 포함하라\n"
        "- 단순 키워드 나열 금지. 이미지 내용을 구체적으로 "
        "묘사하면서 키워드를 녹여라\n"
        '- 예: "강남 다이어트 한의원에서 활용하는 한약재" (X, 홍보성)\n'
        '  → "다이어트 한의원에서 자주 쓰이는 한방 약재 모음" (O, 정보성)\n'
        "- 모든 alt_text 는 한국어로 작성\n\n"
        "[정형화 금지]\n"
        "- 같은 업종이라도 매번 동일한 이미지 순서 금지\n"
        "- 이미지 타입(photo, illustration, infographic)을 "
        "다양하게 섞어라\n"
        f"- 이번 실행 분위기 힌트: '{seed_hint}'\n\n"
        "[형태 다양화]\n"
        "- aspect_ratio 필드로 종횡비를 지정하라 (프롬프트 텍스트에 쓰지 말 것)\n"
        "  정사각(1:1), 가로형(16:9, 4:3), 세로형(3:4, 9:16)\n"
        "- 콜라주(2~4컷 분할), 슬라이드형(넓은 배너)도 가능\n\n"
        "[prompt 작성법 — Gemini 공식 가이드]\n"
        "프롬프트는 키워드 나열이 아닌 장면을 묘사하는 문장으로 작성하라.\n\n"
        "사실적 사진 템플릿:\n"
        "  'A photorealistic [shot type] of [subject], [action], "
        "set in [environment]. Illuminated by [lighting], "
        "creating [mood]. Captured with [camera/lens]. "
        "No text, no letters.'\n\n"
        "일러스트/인포그래픽 템플릿:\n"
        "  'A [style] illustration of [subject], featuring "
        "[characteristics] and [color palette]. [line style] "
        "and [shading]. No text, no letters.'\n\n"
        "[소재 자유도]\n"
        "원고 내용에 적합하다면 어떤 소재든 자유롭게 사용 가능:\n"
        "- 인물: 한국인 일상, 운동, 식사, 상담, 진료 대기 등\n"
        "- 음식: 한식, 건강식, 한방차, 다이어트 식단 등\n"
        "- 공간: 한의원 내부, 약장, 진료실, 대기실 인테리어 등\n"
        "- 재료: 한약재, 침, 뜸, 약첩 등 한의학 도구\n"
        "- 라이프스타일: 운동, 산책, 요가, 수면, 체중 측정 등\n"
        "- 개념: 체질 비교, 대사 원리, 식단 구성 등 인포그래픽\n"
        "원고의 각 섹션 내용에 가장 어울리는 소재를 선택하라.\n\n"
        "[필수 규칙 — 이것만 지키면 됨]\n"
        "1. 언어: 영어 (장면 묘사형 문장)\n"
        "2. 'No text, no letters' 반드시 포함\n"
        "3. 인물은 무조건 한국인 — 모든 인물 prompt 에 'Korean' 포함 필수 (예외 없음)\n"
        "4. 금지 소재 (부정형으로도 넣지 말 것):\n"
        "   - 환자 묘사 (patient, injured, sick)\n"
        "   - 시술 장면 (surgery, injection, treatment scene)\n"
        "   - 전후 비교 (before/after, comparison)\n"
        "   - 신체 노출 (naked, nude, body comparison)\n"
        "5. aspect_ratio 필드에 종횡비 지정\n"
        "6. 카메라 각도, 조명, 분위기를 구체적으로 묘사"
    )


def _format_image_position_guide(pc: PatternCard) -> str:
    """분석된 이미지 위치 분포를 프롬프트 가이드로 변환한다."""
    dist = pc.image_pattern.position_dist
    if dist.front == 0 and dist.mid == 0 and dist.end == 0:
        return "- 도입부 직후 1장 + 본문 중간 균등 배치 (기본값)"

    lines: list[str] = []
    if dist.front >= 1:
        lines.append(f"- 글 앞부분(도입 직후): 평균 {dist.front:.1f}장 배치")
    if dist.mid >= 1:
        lines.append(f"- 본문 중반(섹션 사이): 평균 {dist.mid:.1f}장 배치")
    if dist.end >= 0.5:
        lines.append(f"- 글 후반(마무리 근처): 평균 {dist.end:.1f}장 배치")
    lines.append("- 이 분포를 참고해 position 을 결정하되, AI 이미지 수에 맞게 비율 조정")
    return "\n".join(lines)


def _pick_variation_seed() -> str:
    import random

    return random.choice(_IMAGE_VARIATION_SEEDS)


# 매 실행마다 다른 이미지 구성을 유도하는 분위기 시드 풀
_IMAGE_VARIATION_SEEDS = [
    "따뜻한 자연광 / 아날로그 감성 / 오프화이트 톤",
    "시원한 블루 계열 / 클린 미니멀 / 도시적 세련미",
    "포근한 가을 팔레트 / 어스 톤 / 내추럴 라이프",
    "생동감 있는 컬러풀 / 에너지 넘치는 / 다이내믹 구도",
    "차분한 모노톤 / 젠 스타일 / 여백의 미",
    "빈티지 필름 톤 / 레트로 감성 / 따뜻한 그레인",
    "밝고 경쾌한 파스텔 / 소프트 라이트 / 봄 느낌",
    "고급스러운 다크 톤 / 무드 라이팅 / 프리미엄 느낌",
    "일러스트 믹스 / 사진+그래픽 혼합 / 에디토리얼",
    "항공뷰+클로즈업 교차 / 스케일 대비 / 시네마틱",
]


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
