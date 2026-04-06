"""브랜디드 카드 시스템 퍼블릭 API.

3종 카드(intro, transition, cta)를 생성하고 삽입 위치를 반환한다.
HTML 생성 실패 시 하드코딩 템플릿으로 폴백한다.
"""

from __future__ import annotations

import logging

from domain.analysis.model import PatternCard
from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.generation.card_compositions import CARD_TYPES, get_card_positions
from domain.generation.card_content_generator import generate_card_contents
from domain.generation.card_html_generator import generate_card_htmls
from domain.generation.card_layout_registry import get_gemini_instructions
from domain.generation.card_templates import (
    pick_style,
    render_card_html,
)
from domain.generation.model import CardContent, CardLayoutSet, DesignCard, VariationConfig
from domain.generation.newsletter_theme import get_theme
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)


def generate_branded_cards(
    keyword: str,
    title: str,
    structure_name: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
    variation_config: VariationConfig | None = None,
) -> tuple[list[DesignCard], dict[str, int]]:
    """브랜디드 카드 3종을 생성하고 삽입 위치를 반환한다.

    1. 카드 삽입 위치 결정
    2. LLM으로 카드 콘텐츠 일괄 생성
    3. LLM으로 HTML/CSS 디자인 생성 (실패 시 템플릿 폴백)

    Returns:
        (DesignCard 리스트, 삽입 위치 딕셔너리) 튜플
    """
    # 1. 카드 삽입 위치
    positions = get_card_positions(structure_name, profile)
    logger.info(
        "카드 삽입 위치: %s",
        ", ".join(f"{k}={v}" for k, v in positions.items()),
    )

    # 2. 카드 시퀀스 구성
    sequence = list(CARD_TYPES)  # intro, transition, cta
    if profile.is_medical():
        sequence.append("disclaimer")

    logger.info("카드 시퀀스 (%d장): %s", len(sequence), " -> ".join(sequence))

    # 3. LLM 콘텐츠 생성
    contents = generate_card_contents(
        sequence,
        keyword,
        pattern_card,
        profile,
    )
    content_map = {c.card_type: c for c in contents}
    if "disclaimer" in sequence and "disclaimer" not in content_map:
        content_map["disclaimer"] = CardContent(
            card_type="disclaimer",
            body_text=DISCLAIMER_TEMPLATE,
        )

    ordered_contents = [content_map.get(ct, CardContent(card_type=ct)) for ct in sequence]

    # 4. 색상 팔레트 (테마 우선, 없으면 패턴 카드)
    colors = _resolve_colors(pattern_card, variation_config)

    # 5. 레이아웃 스펙 구성
    card_layouts = variation_config.card_layouts if variation_config else CardLayoutSet()
    layout_specs = get_gemini_instructions(card_layouts.model_dump(exclude_defaults=True))

    # 6. LLM HTML 디자인 생성
    html_list = _generate_htmls_with_fallback(
        ordered_contents,
        profile,
        colors,
        layout_specs=layout_specs,
        card_layouts=card_layouts,
    )

    # 6. DesignCard 조합
    cards: list[DesignCard] = []
    for i, card_type in enumerate(sequence):
        content = ordered_contents[i]
        cards.append(
            DesignCard(
                card_type=card_type,
                html=html_list[i],
                title=content.title,
                subtitle=content.subtitle,
                color_primary=colors["primary"],
                color_background=colors["background"],
                color_accent=colors["accent"],
            ),
        )

    logger.info("브랜디드 카드 생성 완료: %d장", len(cards))
    return cards, positions


def _generate_htmls_with_fallback(
    contents: list[CardContent],
    profile: ClientProfile,
    colors: dict[str, str],
    layout_specs: dict[str, str] | None = None,
    card_layouts: CardLayoutSet | None = None,
) -> list[str]:
    """LLM HTML 생성을 시도하고, 실패한 카드는 템플릿 폴백."""
    try:
        html_list = generate_card_htmls(contents, profile, colors, layout_specs)
    except Exception:
        logger.warning("LLM HTML 생성 실패, 전체 템플릿 폴백")
        html_list = [""] * len(contents)

    needs_fallback = any(not h.strip() for h in html_list)
    if needs_fallback:
        fallback_count = sum(1 for h in html_list if not h.strip())
        logger.info("템플릿 폴백: %d장", fallback_count)

        style = pick_style()
        accent = colors["accent"]
        total = len(contents)

        for i, html in enumerate(html_list):
            if not html.strip():
                layout_name = ""
                if card_layouts:
                    layout_name = getattr(card_layouts, contents[i].card_type, "")
                html_list[i] = render_card_html(
                    contents[i],
                    style,
                    accent,
                    profile,
                    card_index=i,
                    total_cards=total,
                    layout_name=layout_name,
                )

    return html_list


def _resolve_colors(
    pattern_card: PatternCard,
    variation_config: VariationConfig | None,
) -> dict[str, str]:
    """테마 색상 우선, 없으면 패턴 카드 팔레트를 사용한다."""
    if variation_config and variation_config.newsletter_theme:
        theme = get_theme(variation_config.newsletter_theme)
        if theme:
            return {
                "primary": theme.text_heading,
                "background": theme.bg_card_light,
                "accent": theme.accent,
            }

    palette = pattern_card.visual_pattern.get(
        "color_palette",
        ["#333333", "#ffffff", "#4a90d9"],
    )
    return {
        "primary": palette[0] if palette else "#333333",
        "background": palette[1] if len(palette) > 1 else "#ffffff",
        "accent": palette[2] if len(palette) > 2 else "#4a90d9",
    }
