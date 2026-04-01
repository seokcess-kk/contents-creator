"""패턴 카드 생성. L1 + L2 + 비주얼 분석 결과를 통합한다.

패턴 카드는 "분석 1번, 생성 N번" 원칙의 핵심 자산이다.
"""

from __future__ import annotations

import logging
import statistics

from domain.analysis.model import (
    L1Analysis,
    L2Analysis,
    PatternCard,
    VisualAnalysis,
)

logger = logging.getLogger(__name__)

# 패턴 카드가 제어하는 것 (뼈대)
SKELETON_FIELDS = [
    "section_order",
    "char_range",
    "subtitle_count",
    "title_formulas",
    "required_keywords",
    "color_palette",
    "layout_pattern",
    "image_count_range",
]

# 패턴 카드가 제어하지 않는 것 (살)
FREE_FIELDS = [
    "sentences",
    "stories",
    "details",
    "specific_expressions",
    "episode_content",
]


def build_pattern_card(
    keyword: str,
    l1: L1Analysis,
    l2: L2Analysis,
    visual: VisualAnalysis,
) -> PatternCard:
    """분석 결과를 통합하여 패턴 카드를 생성한다.

    Args:
        keyword: 분석 키워드
        l1: L1 구조 분석 결과
        l2: L2 카피 분석 결과
        visual: 비주얼 분석 결과

    Returns:
        PatternCard
    """
    # 텍스트 패턴
    char_values = [p.total_chars for p in l1.per_post if p.total_chars > 0]
    char_range = _p25_p75(char_values) if char_values else [1500, 3500]

    subtitle_values = [p.subtitle_count for p in l1.per_post]
    subtitle_range = _p25_p75(subtitle_values) if subtitle_values else [3, 6]

    # 제목 공식: 상위 2~3개
    title_formulas = [
        {"type": tp.type, "template": "", "weight": tp.weight}
        for tp in sorted(l2.title_patterns, key=lambda x: x.count, reverse=True)[:3]
    ]

    # 훅 유형: 상위 2개
    hook_types = [
        hp.type for hp in sorted(l2.hook_patterns, key=lambda x: x.count, reverse=True)[:2]
    ]

    # 설득 구조: 최다 1개
    persuasion = l2.persuasion_structures[0] if l2.persuasion_structures else ""

    # 섹션 순서 추론
    section_order = _infer_section_order(l1, l2)

    text_pattern = {
        "char_range": char_range,
        "subtitle_count": subtitle_range,
        "title_formulas": title_formulas,
        "hook_types": hook_types,
        "persuasion_structure": persuasion,
        "required_keywords": l2.related_keywords[:5],
        "related_keywords": l2.related_keywords,
        "lsi_keywords": l2.lsi_keywords,
        "section_order": section_order,
    }

    # 비주얼 패턴
    image_count_values = [p.image_count for p in l1.per_post if p.image_count > 0]
    image_range = _p25_p75(image_count_values) if image_count_values else [3, 8]

    visual_pattern = {
        "color_palette": visual.dominant_palette,
        "layout_pattern": visual.layout_pattern,
        "image_types": visual.image_type_distribution
        or {"실사": 0.5, "AI생성": 0.3, "디자인카드": 0.2},
        "image_count_range": image_range,
        "mood": visual.mood,
    }

    # 신뢰도
    confidence = "high" if l1.post_count >= 5 else "low"

    card = PatternCard(
        keyword=keyword,
        text_pattern=text_pattern,
        visual_pattern=visual_pattern,
        constraints={"skeleton": SKELETON_FIELDS, "free": FREE_FIELDS},
        confidence=confidence,
        source_post_count=l1.post_count,
    )

    logger.info(
        "패턴 카드 생성: '%s' (포스트 %d개, 신뢰도 %s)",
        keyword,
        l1.post_count,
        confidence,
    )
    return card


def _p25_p75(values: list[int | float]) -> list[int]:
    """P25~P75 범위를 반환한다."""
    if len(values) < 2:
        return [int(values[0] * 0.8), int(values[0] * 1.2)] if values else [0, 0]

    sorted_vals = sorted(values)
    q1 = statistics.quantiles(sorted_vals, n=4)[0]
    q3 = statistics.quantiles(sorted_vals, n=4)[2]
    return [int(q1), int(q3)]


def _infer_section_order(l1: L1Analysis, l2: L2Analysis) -> list[str]:
    """분석 결과에서 섹션 순서를 추론한다."""
    # 기본 구조: 설득 구조 기반
    persuasion = l2.persuasion_structures[0] if l2.persuasion_structures else ""

    order_map = {
        "AIDA": ["도입(주의)", "관심", "욕구", "행동(CTA)"],
        "PAS": ["문제", "강조", "솔루션", "CTA"],
        "문제-원인-솔루션": ["도입", "문제제기", "원인", "솔루션", "차별점", "CTA"],
        "비포-애프터": ["도입", "비포(문제)", "전환", "애프터(결과)", "CTA"],
    }

    return order_map.get(persuasion, ["도입", "문제제기", "솔루션", "차별점", "사례", "CTA"])
