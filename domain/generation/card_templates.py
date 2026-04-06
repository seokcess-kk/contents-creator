"""카드 공통 스타일 유틸 + 디스패처.

VisualStyle 풀, 공통 CSS 빌더, 카드 타입별 디스패처를 제공한다.
레이아웃별 렌더러는 card_layout_intro/transition/cta.py에 분리되어 있다.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile

# === 폰트 상수 ===

FONT_PRIMARY = "'Pretendard', 'Nanum Gothic', 'Malgun Gothic', sans-serif"
FONT_HANDWRITING = "'Nanum Pen Script', 'Nanum Gothic', cursive"

# === 라벨 사전 ===

LABELS_EN: dict[str, str] = {
    "intro": "ABOUT",
    "transition": "",
    "cta": "CONTACT",
    "disclaimer": "DISCLAIMER",
}

LABELS_KO: dict[str, str] = {
    "intro": "",
    "transition": "",
    "cta": "",
    "disclaimer": "",
}


@dataclass
class VisualStyle:
    """비주얼 스타일 세트."""

    name: str
    bg_light: str
    bg_dark: str
    text_on_light: str
    text_on_dark: str
    text_align: str  # left | center
    border_radius: str
    font_weight_title: str
    label_lang: str = "en"
    label_spacing: str = "3px"
    title_spacing: str = "-0.5px"
    line_positions: list[str] = field(
        default_factory=lambda: ["top", "left", "bottom", "top"],
    )


STYLE_POOL: list[VisualStyle] = [
    VisualStyle(
        name="magazine",
        bg_light="linear-gradient(180deg, #ffffff 0%, #f7f7f7 100%)",
        bg_dark="linear-gradient(180deg, #1a1a1a 0%, #111111 100%)",
        text_on_light="#1a1a1a",
        text_on_dark="#f0f0f0",
        text_align="left",
        border_radius="0",
        font_weight_title="800",
        label_lang="en",
        label_spacing="4px",
        title_spacing="-0.3px",
        line_positions=["top", "left", "bottom", "top"],
    ),
    VisualStyle(
        name="minimal_center",
        bg_light="linear-gradient(180deg, #fafafa 0%, #f3f3f3 100%)",
        bg_dark="linear-gradient(180deg, #2c2c2c 0%, #1e1e1e 100%)",
        text_on_light="#333333",
        text_on_dark="#e8e8e8",
        text_align="center",
        border_radius="0",
        font_weight_title="700",
        label_lang="ko",
        label_spacing="6px",
        title_spacing="0px",
        line_positions=["center", "center", "center", "center"],
    ),
    VisualStyle(
        name="warm_card",
        bg_light="linear-gradient(180deg, #fdf8f3 0%, #f5ede3 100%)",
        bg_dark="linear-gradient(180deg, #3e2f23 0%, #2c2018 100%)",
        text_on_light="#4a3728",
        text_on_dark="#f0e6d9",
        text_align="left",
        border_radius="16px",
        font_weight_title="700",
        label_lang="ko",
        label_spacing="5px",
        title_spacing="-0.3px",
        line_positions=["left", "top", "left", "bottom"],
    ),
    VisualStyle(
        name="bold_contrast",
        bg_light="linear-gradient(180deg, #f0f0f0 0%, #e4e4e4 100%)",
        bg_dark="linear-gradient(180deg, #0d0d0d 0%, #1a1a1a 100%)",
        text_on_light="#0d0d0d",
        text_on_dark="#ffffff",
        text_align="center",
        border_radius="0",
        font_weight_title="900",
        label_lang="en",
        label_spacing="5px",
        title_spacing="-0.5px",
        line_positions=["top", "bottom", "top", "center"],
    ),
]


def pick_style() -> VisualStyle:
    """스타일 풀에서 랜덤 선택한다."""
    return random.choice(STYLE_POOL)


def get_label(
    style: VisualStyle,
    card_type: str,
    content_badge: str = "",
) -> str:
    """카드 타입의 섹션 라벨을 반환한다."""
    if content_badge:
        return content_badge
    labels = LABELS_KO if style.label_lang == "ko" else LABELS_EN
    return labels.get(card_type, "")


# === 공통 스타일 빌더 ===


def base_style(
    bg: str,
    color: str,
    style: VisualStyle,
    padding: str = "50px 40px",
    font: str = "",
) -> str:
    """공통 컨테이너 스타일."""
    f = font or FONT_PRIMARY
    return (
        f"width:100%;max-width:720px;padding:{padding};background:{bg};"
        f"text-align:{style.text_align};font-family:{f};"
        f"box-sizing:border-box;"
    )


def title_style(
    color: str,
    style: VisualStyle,
    size: str = "26px",
) -> str:
    """제목 스타일."""
    return (
        f"font-size:{size};color:{color};"
        f"font-weight:{style.font_weight_title};"
        f"letter-spacing:{style.title_spacing};"
        f"line-height:1.4;margin:0 0 12px;"
        f"word-break:keep-all;"
    )


def title_dark_style(
    color: str,
    style: VisualStyle,
    size: str = "26px",
) -> str:
    """다크 배경 전용 제목 스타일."""
    return (
        f"font-size:{size};color:{color};"
        f"font-weight:{style.font_weight_title};"
        f"letter-spacing:{style.title_spacing};"
        f"line-height:1.4;margin:0 0 12px;"
        f"word-break:keep-all;"
        f"text-shadow:0 1px 2px rgba(0,0,0,0.3);"
    )


def label_style(color: str, style: VisualStyle) -> str:
    """섹션 라벨 스타일."""
    return (
        f"font-size:12px;color:{color};"
        f"letter-spacing:{style.label_spacing};"
        f"font-weight:600;margin:0 0 14px;"
        f"text-transform:uppercase;"
    )


def body_style(color: str) -> str:
    """본문 스타일."""
    return f"font-size:15px;color:{color};line-height:1.8;margin:0;word-break:keep-all;"


def accent_line(
    accent: str,
    style: VisualStyle,
    card_index: int,
) -> str:
    """카드 인덱스에 따라 악센트 라인 위치를 결정한다."""
    pos = style.line_positions[card_index % len(style.line_positions)]
    center = "auto" if style.text_align == "center" else "0"

    if pos == "top":
        return (
            f'<div style="width:40px;height:3px;background:{accent};margin:0 {center} 20px;"></div>'
        )
    if pos == "left":
        return f'<div style="width:3px;height:40px;background:{accent};margin:0 0 20px;"></div>'
    if pos == "bottom":
        return ""
    return f'<div style="width:40px;height:3px;background:{accent};margin:0 auto 20px;"></div>'


def accent_line_bottom(
    accent: str,
    style: VisualStyle,
    card_index: int,
) -> str:
    """하단 악센트 라인 (필요시에만)."""
    pos = style.line_positions[card_index % len(style.line_positions)]
    if pos != "bottom":
        return ""
    center = "auto" if style.text_align == "center" else "0"
    return f'<div style="width:40px;height:3px;background:{accent};margin:20px {center} 0;"></div>'


# === disclaimer (고정) ===


def render_disclaimer(style: VisualStyle) -> str:
    """disclaimer 카드: 의료법 면책 고지 (고정 템플릿)."""
    lbl = get_label(style, "disclaimer")
    return f"""\
<div style="width:100%;max-width:720px;padding:30px 40px;\
background:linear-gradient(180deg, #f5f5f5 0%, #efefef 100%);\
font-family:{FONT_PRIMARY};box-sizing:border-box;">
  <p style="font-size:10px;color:#aaa;margin:0 0 8px;\
letter-spacing:{style.label_spacing};\
font-weight:600;">{lbl}</p>
  <p style="font-size:12px;color:#999;line-height:1.8;\
margin:0;word-break:keep-all;">{DISCLAIMER_TEMPLATE}</p>
</div>"""


# === 디스패처 ===


def render_card_html(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
    layout_name: str = "",
) -> str:
    """카드 타입과 레이아웃에 따라 적절한 렌더러를 호출한다."""
    if content.card_type == "disclaimer":
        return render_disclaimer(style)

    renderer = _resolve_renderer(content.card_type, layout_name)
    if renderer:
        return renderer(
            content=content,
            style=style,
            accent=accent,
            profile=profile,
            card_index=card_index,
            total_cards=total_cards,
        )

    # 최종 폴백: 기본 div
    return f"""\
<div style="{base_style(style.bg_light, style.text_on_light, style)}">
  <h2 style="{title_style(style.text_on_light, style)}">\
{content.title}</h2>
  <p style="{body_style(style.text_on_light)}">\
{content.body_text}</p>
</div>"""


def _resolve_renderer(
    card_type: str,
    layout_name: str,
) -> Callable[..., str] | None:
    """레이아웃 이름으로 렌더러 함수를 찾는다."""
    from domain.generation.card_layout_cta import CTA_RENDERERS
    from domain.generation.card_layout_intro import INTRO_RENDERERS
    from domain.generation.card_layout_transition import TRANSITION_RENDERERS

    registry = {
        # 5종 브랜드 카드 → 기존 렌더러 매핑
        "greeting": INTRO_RENDERERS,
        "empathy": TRANSITION_RENDERERS,
        "service": CTA_RENDERERS,  # service_grid 등
        "trust": TRANSITION_RENDERERS,  # stat_highlight 등
        "cta": CTA_RENDERERS,
        # 하위호환
        "intro": INTRO_RENDERERS,
        "transition": TRANSITION_RENDERERS,
    }

    renderers = registry.get(card_type, {})

    # 지정된 레이아웃이 있으면 해당 렌더러 사용
    if layout_name and layout_name in renderers:
        return renderers[layout_name]

    # 레이아웃 미지정 시 첫 번째 렌더러를 기본값으로
    if renderers:
        first_key = next(iter(renderers))
        return renderers[first_key]

    return None
