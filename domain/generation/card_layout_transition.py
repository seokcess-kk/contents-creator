"""transition 카드 레이아웃 렌더러 5종.

hashtag_keycopy, big_question, stat_highlight, emotional_quote, split_contrast
"""

from __future__ import annotations

from collections.abc import Callable

from domain.generation.card_templates import (
    FONT_HANDWRITING,
    FONT_PRIMARY,
    VisualStyle,
    accent_line,
    accent_line_bottom,
    base_style,
    body_style,
    title_dark_style,
)
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile


def render_hashtag_keycopy(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """해시태그 스타일 키카피 + 다크 배경."""
    bg = style.bg_dark
    color = style.text_on_dark
    title = content.title or ""
    line = accent_line(accent, style, card_index)

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}text-align:center;">
  {line}
  <h2 style="font-size:28px;color:{color};\
font-weight:{style.font_weight_title};\
line-height:1.5;margin:0 0 16px;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.3);">\
<span style="color:{accent};">#</span>{title}</h2>
  <p style="{body_style(color)}opacity:0.7;\
text-shadow:0 1px 1px rgba(0,0,0,0.2);">{content.body_text}</p>
</div>"""


def render_big_question(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """대형 질문 1줄 + 구분선 + 답변 티저."""
    bg = style.bg_dark
    color = style.text_on_dark

    return f"""\
<div style="{base_style(bg, color, style, "80px 48px")}text-align:center;">
  <h2 style="font-size:28px;color:{color};\
font-weight:{style.font_weight_title};\
line-height:1.5;margin:0 0 24px;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.3);">{content.title}</h2>
  <div style="width:50px;height:2px;background:{accent};\
margin:0 auto 24px;"></div>
  <p style="font-size:15px;color:{color};opacity:0.6;\
line-height:1.8;margin:0;word-break:keep-all;">\
{content.body_text}</p>
</div>"""


def render_stat_highlight(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """통계/숫자 중앙 강조."""
    bg = style.bg_dark
    color = style.text_on_dark
    stat = content.badge_text or content.subtitle or ""

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}text-align:center;">
  <p style="font-size:11px;color:{color};opacity:0.5;\
letter-spacing:4px;font-weight:600;margin:0 0 12px;\
text-transform:uppercase;">DATA</p>
  <p style="font-size:42px;color:{accent};font-weight:900;\
margin:0 0 12px;letter-spacing:-1px;\
font-family:{FONT_PRIMARY};">{stat}</p>
  <h3 style="{title_dark_style(color, style, "20px")}\
margin:0 0 16px;">{content.title}</h3>
  <p style="font-size:14px;color:{color};opacity:0.5;\
line-height:1.6;margin:0;">{content.body_text}</p>
</div>"""


def render_emotional_quote(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """감성 인용문 + 손글씨체 + 다크 배경."""
    bg = style.bg_dark
    color = style.text_on_dark
    line_b = accent_line_bottom(accent, style, card_index)

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}">
  <div style="font-size:52px;color:{accent};opacity:0.4;\
line-height:1;margin:0 0 8px;font-family:Georgia,serif;">\u201c</div>
  <p style="font-size:24px;color:{color};font-family:{FONT_HANDWRITING};\
line-height:1.8;margin:0 0 20px;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.2);">{content.title}</p>
  <p style="font-size:14px;color:{color};opacity:0.5;\
margin:0;">{content.body_text}</p>
  {line_b}
</div>"""


def render_split_contrast(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """상하 2분할 대비 (문제/전환)."""
    dark_bg = style.bg_dark
    dark_color = style.text_on_dark
    light_bg = style.bg_light
    light_color = style.text_on_light

    return f"""\
<div style="width:100%;max-width:720px;font-family:{FONT_PRIMARY};\
box-sizing:border-box;">
  <div style="padding:50px 48px;background:{dark_bg};">
    <p style="font-size:22px;color:{dark_color};\
font-weight:{style.font_weight_title};\
line-height:1.5;margin:0;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.3);">{content.title}</p>
  </div>
  <div style="width:60px;height:3px;background:{accent};\
margin:0 auto;position:relative;top:-1px;"></div>
  <div style="padding:40px 48px;background:{light_bg};">
    <p style="font-size:16px;color:{light_color};\
line-height:1.8;margin:0;word-break:keep-all;opacity:0.8;">\
{content.body_text}</p>
  </div>
</div>"""


TRANSITION_RENDERERS: dict[str, Callable[..., str]] = {
    "hashtag_keycopy": render_hashtag_keycopy,
    "big_question": render_big_question,
    "stat_highlight": render_stat_highlight,
    "emotional_quote": render_emotional_quote,
    "split_contrast": render_split_contrast,
}
