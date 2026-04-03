"""카드 타입별 HTML 폴백 렌더러 + 비주얼 스타일 풀.

Gemini HTML 생성 실패 시 사용하는 하드코딩 템플릿.
3종 카드(intro, transition, cta) + disclaimer만 지원한다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile

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

_FONT = "'Nanum Gothic', 'Malgun Gothic', sans-serif"


def pick_style() -> VisualStyle:
    """스타일 풀에서 랜덤 선택한다."""
    return random.choice(STYLE_POOL)


def _get_label(
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


def _base(
    bg: str,
    color: str,
    style: VisualStyle,
    padding: str = "50px 40px",
) -> str:
    """공통 컨테이너 스타일."""
    return (
        f"width:100%;max-width:720px;padding:{padding};background:{bg};"
        f"text-align:{style.text_align};font-family:{_FONT};"
        f"box-sizing:border-box;"
    )


def _title_style(
    color: str,
    style: VisualStyle,
    size: str = "26px",
) -> str:
    return (
        f"font-size:{size};color:{color};"
        f"font-weight:{style.font_weight_title};"
        f"letter-spacing:{style.title_spacing};"
        f"line-height:1.4;margin:0 0 12px;"
        f"word-break:keep-all;"
    )


def _title_dark(
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


def _label_style(color: str, style: VisualStyle) -> str:
    """섹션 라벨 스타일."""
    return (
        f"font-size:12px;color:{color};"
        f"letter-spacing:{style.label_spacing};"
        f"font-weight:600;margin:0 0 14px;"
        f"text-transform:uppercase;"
    )


def _body_style(color: str) -> str:
    return f"font-size:15px;color:{color};line-height:1.8;margin:0;word-break:keep-all;"


def _accent_line(
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


def _accent_line_bottom(
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


# === 카드 타입별 렌더러 ===


def render_intro(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """intro 카드: 업체 소개 + 공감 질문."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title
    label = _get_label(style, "intro")
    line = _accent_line(accent, style, card_index)
    line_b = _accent_line_bottom(accent, style, card_index)

    label_html = ""
    if label:
        label_html = f'<p style="{_label_style(accent, style)}">{label}</p>'

    tags_html = ""
    if profile.services:
        badges = [
            f'<span style="display:inline-block;padding:6px 14px;'
            f"background:{accent}15;color:{accent};border-radius:20px;"
            f"font-size:12px;font-weight:600;"
            f'letter-spacing:0.5px;margin:4px;">{s.name}</span>'
            for s in profile.services[:5]
        ]
        tags_html = f'<div style="margin-top:20px;">{"".join(badges)}</div>'

    subtitle = content.subtitle or profile.usp or ""
    sub_html = ""
    if subtitle:
        sub_html = (
            f'<p style="font-size:15px;color:{color};opacity:0.6;'
            f"margin:0 0 12px;line-height:1.5;"
            f'letter-spacing:0.3px;">{subtitle}</p>'
        )

    return f"""\
<div style="{_base(bg, color, style)}">
  {label_html}
  <h1 style="font-size:28px;color:{color};\
font-weight:{style.font_weight_title};\
letter-spacing:{style.title_spacing};\
margin:0 0 10px;word-break:keep-all;">{company}</h1>
  {sub_html}
  {line}
  <p style="{_body_style(color)}margin-top:16px;\
opacity:0.8;">{content.body_text}</p>
  {tags_html}
  {line_b}
</div>"""


def render_transition(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """transition 카드: 고민 -> 솔루션 브릿지. 다크 배경."""
    bg = style.bg_dark
    color = style.text_on_dark
    line = _accent_line(accent, style, card_index)
    line_b = _accent_line_bottom(accent, style, card_index)

    return f"""\
<div style="{_base(bg, color, style, "60px 40px")}">
  {line}
  <h2 style="{_title_dark(color, style, "24px")}">\
{content.title}</h2>
  <p style="{_body_style(color)}opacity:0.8;\
text-shadow:0 1px 1px rgba(0,0,0,0.2);">{content.body_text}</p>
  {line_b}
</div>"""


def render_cta(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """cta 카드: 마지막 후킹 + 연락처."""
    bg = style.bg_dark
    color = style.text_on_dark
    company = profile.company_name or content.title
    label = _get_label(style, "cta", content.subtitle)
    line = _accent_line(accent, style, card_index)

    label_html = ""
    if label:
        label_html = f'<p style="{_label_style(accent, style)}">{label}</p>'

    contact_lines = []
    if profile.phone:
        contact_lines.append(f"T. {profile.phone}")
    if profile.address:
        contact_lines.append(profile.address)
    if profile.region and not profile.address:
        contact_lines.append(profile.region)

    contact_html = ""
    if contact_lines:
        items = "".join(
            f'<p style="font-size:13px;color:{color};opacity:0.55;'
            f'margin:4px 0;letter-spacing:0.3px;">{cl}</p>'
            for cl in contact_lines
        )
        contact_html = f'<div style="margin-top:20px;">{items}</div>'

    return f"""\
<div style="{_base(bg, color, style, "50px 40px")}">
  {line}
  {label_html}
  <h2 style="{_title_dark(color, style, "24px")}">\
{content.title}</h2>
  <p style="{_body_style(color)}opacity:0.75;\
text-shadow:0 1px 1px rgba(0,0,0,0.2);">{content.body_text}</p>
  <p style="font-size:20px;color:{color};font-weight:700;\
letter-spacing:{style.title_spacing};\
margin:24px 0 0;word-break:keep-all;">{company}</p>
  {contact_html}
</div>"""


def render_disclaimer(style: VisualStyle) -> str:
    """disclaimer 카드: 의료법 면책 고지 (고정 템플릿)."""
    label = _get_label(style, "disclaimer")
    return f"""\
<div style="width:100%;max-width:720px;padding:30px 40px;\
background:linear-gradient(180deg, #f5f5f5 0%, #efefef 100%);\
font-family:{_FONT};box-sizing:border-box;">
  <p style="font-size:10px;color:#aaa;margin:0 0 8px;\
letter-spacing:{style.label_spacing};\
font-weight:600;">{label}</p>
  <p style="font-size:12px;color:#999;line-height:1.8;\
margin:0;word-break:keep-all;">{DISCLAIMER_TEMPLATE}</p>
</div>"""


def render_card_html(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """카드 타입에 따라 적절한 렌더러를 호출한다."""
    ci = card_index
    tc = total_cards
    renderers = {
        "intro": lambda: render_intro(
            content,
            style,
            accent,
            profile,
            ci,
            tc,
        ),
        "transition": lambda: render_transition(
            content,
            style,
            accent,
            ci,
            tc,
        ),
        "cta": lambda: render_cta(
            content,
            style,
            accent,
            profile,
            ci,
            tc,
        ),
        "disclaimer": lambda: render_disclaimer(style),
    }

    renderer = renderers.get(content.card_type)
    if renderer:
        return renderer()

    return f"""\
<div style="{_base(style.bg_light, style.text_on_light, style)}">
  <h2 style="{_title_style(style.text_on_light, style)}">\
{content.title}</h2>
  <p style="{_body_style(style.text_on_light)}">\
{content.body_text}</p>
</div>"""
