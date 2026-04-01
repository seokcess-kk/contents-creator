"""5개 층위 변이 엔진.

"같은 생산자 느낌"을 원천 차단하는 핵심 모듈.
"""

from __future__ import annotations

import random

from domain.analysis.model import PatternCard
from domain.generation.model import VariationConfig
from domain.generation.structure_templates import get_all_template_names

# ② 도입부 스타일 풀
INTRO_STYLES = [
    "사연형",  # "OO님은 매일 아침 거울을 보며..."
    "통계형",  # "최근 조사에 따르면 10명 중 7명이..."
    "질문형",  # "혹시 이런 고민을 하고 계신가요?"
    "계절형",  # "날씨가 추워지면서 OO 고민이..."
    "공감형",  # "많은 분들이 OO 때문에 걱정하시죠"
    "반전형",  # "OO가 오히려 해로울 수 있다는 사실..."
]

# ③ 소제목 스타일 풀
SUBTITLE_STYLES = [
    "질문형",  # "왜 OO가 중요할까요?"
    "숫자포함형",  # "3가지 핵심 포인트"
    "감정유발형",  # "놓치면 후회하는 OO"
    "상황묘사형",  # "아침에 일어났더니 피부가..."
    "결과중심형",  # "2주 만에 달라진 피부결"
]

# ⑤ 이미지 배치 패턴 풀
IMAGE_PLACEMENT_STYLES = [
    "헤더집중형",  # 헤더 이미지 1장 + 본문 텍스트 위주
    "균등분산형",  # 2~3문단마다 1장씩
    "솔루션강조형",  # 문제 섹션 텍스트만 → 솔루션에 이미지 집중
    "전후대비형",  # 도입부 1장 + 결론부 1장
    "CTA집중형",  # 본문 최소 → CTA 주변 이미지 다수
]


def recommend_variation(
    pattern_card: PatternCard,
    *,
    exclude_configs: list[VariationConfig] | None = None,
) -> VariationConfig:
    """패턴 카드 기반으로 변이 조합을 추천한다.

    이전에 사용된 조합(exclude_configs)과 겹치지 않도록 선택한다.

    Args:
        pattern_card: 분석 패턴 카드
        exclude_configs: 제외할 이전 변이 조합 목록

    Returns:
        추천된 VariationConfig
    """
    exclude = exclude_configs or []
    used_structures = {c.structure for c in exclude}
    used_intros = {c.intro for c in exclude}

    # ① 구조: 패턴 카드의 설득 구조와 매칭되는 템플릿 우선
    persuasion = pattern_card.text_pattern.get("persuasion_structure", "")
    structure = _pick_structure(persuasion, used_structures)

    # ② 도입부: 패턴 카드의 hook_types 우선
    hook_types = pattern_card.text_pattern.get("hook_types", [])
    intro = _pick_intro(hook_types, used_intros)

    # ③ 소제목: 랜덤
    subtitle_style = random.choice(SUBTITLE_STYLES)

    # ④ 표현 톤: 패턴 카드의 톤 분포에서 선택 (생성 시 expression_filter가 후처리)
    expression_tone = "자연스러운"

    # ⑤ 이미지 배치: 랜덤
    image_placement = random.choice(IMAGE_PLACEMENT_STYLES)

    return VariationConfig(
        structure=structure,
        intro=intro,
        subtitle_style=subtitle_style,
        expression_tone=expression_tone,
        image_placement=image_placement,
    )


def format_variation_preview(config: VariationConfig) -> str:
    """사용자 승인용 변이 조합 미리보기를 생성한다."""
    return (
        "[변이 조합 제안]\n"
        f"① 구조: {config.structure}\n"
        f"② 도입부: {config.intro}\n"
        f"③ 소제목 스타일: {config.subtitle_style}\n"
        f"④ 표현 톤: {config.expression_tone}\n"
        f"⑤ 이미지 배치: {config.image_placement}\n"
        "\n[승인/수정/재추천] 중 선택해 주세요."
    )


def _pick_structure(persuasion: str, used: set[str]) -> str:
    """설득 구조에 맞는 템플릿을 선택한다."""
    # 설득 구조 → 템플릿 매핑
    mapping: dict[str, str] = {
        "문제-원인-솔루션": "문제해결형",
        "AIDA": "스토리공감형",
        "PAS": "문제해결형",
        "비포-애프터": "비포애프터형",
    }

    preferred = mapping.get(persuasion, "")
    all_names = get_all_template_names()
    available = [n for n in all_names if n not in used]

    if not available:
        available = all_names  # 모두 사용됨 → 리셋

    if preferred and preferred in available:
        return preferred

    return random.choice(available)


def _pick_intro(hook_types: list[str], used: set[str]) -> str:
    """도입부 스타일을 선택한다."""
    # 패턴 카드의 hook_types와 도입부 스타일 매핑
    mapping: dict[str, str] = {
        "공감형": "공감형",
        "통계형": "통계형",
        "질문형": "질문형",
        "스토리형": "사연형",
        "시즌형": "계절형",
    }

    available = [s for s in INTRO_STYLES if s not in used]
    if not available:
        available = INTRO_STYLES

    # 패턴 카드 우선
    for hook in hook_types:
        mapped = mapping.get(hook, "")
        if mapped and mapped in available:
            return mapped

    return random.choice(available)
