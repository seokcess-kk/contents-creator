"""intro 카드 레이아웃 렌더러 5종.

quote_greeting, magazine_header, profile_namecard, brand_statement, story_opener
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
    get_label,
    label_style,
    title_style,
)
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile


def _photo_b64(profile: ClientProfile) -> str:
    """프로필 사진을 base64 문자열로 반환한다. 없으면 빈 문자열."""
    import base64
    from pathlib import Path

    if not profile.photo_path:
        return ""
    p = Path(profile.photo_path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("ascii")


def _photo_html(
    b64: str,
    size: str = "80px",
    radius: str = "50%",
) -> str:
    """원형 사진 HTML을 반환한다."""
    if not b64:
        return ""
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:{size};height:{size};border-radius:{radius};'
        f'object-fit:cover;display:block;" alt="photo">'
    )


def render_quote_greeting(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """큰따옴표 인사말 + 원장명 서명 + 손글씨체 (+ 사진)."""
    bg = style.bg_light
    color = style.text_on_light
    rep = profile.representative or profile.company_name
    company = profile.company_name or content.title
    greeting = content.body_text or f"{content.title} 고민이세요?"

    photo = _photo_html(_photo_b64(profile))
    photo_block = ""
    if photo:
        photo_block = f'<div style="text-align:center;margin:0 0 20px;">{photo}</div>'

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}">
  {photo_block}
  <div style="font-size:48px;color:{accent};opacity:0.3;\
line-height:1;margin:0 0 8px;font-family:Georgia,serif;">\u201c</div>
  <p style="font-size:22px;color:{color};font-family:{FONT_HANDWRITING};\
line-height:1.8;margin:0 0 4px;word-break:keep-all;">\
{greeting}</p>
  <div style="font-size:48px;color:{accent};opacity:0.3;\
line-height:1;margin:0 0 20px;text-align:right;\
font-family:Georgia,serif;">\u201d</div>
  <p style="font-size:14px;color:{color};opacity:0.6;\
text-align:right;margin:0;letter-spacing:0.5px;">\
{company} {rep}</p>
  <div style="width:40px;height:2px;background:{accent};\
margin:24px auto 0;opacity:0.4;"></div>
</div>"""


def render_magazine_header(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """매거진 헤더 - 대형 타이틀 + 서브라인 + pill badges."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title
    lbl = get_label(style, "intro")
    line = accent_line(accent, style, card_index)
    line_b = accent_line_bottom(accent, style, card_index)

    lbl_html = ""
    if lbl:
        lbl_html = f'<p style="{label_style(accent, style)}">{lbl}</p>'

    sub = content.subtitle or profile.usp or ""
    sub_html = ""
    if sub:
        sub_html = (
            f'<p style="font-size:15px;color:{color};opacity:0.6;'
            f'margin:0 0 16px;line-height:1.5;">{sub}</p>'
        )

    tags = _service_tags(profile, accent)

    return f"""\
<div style="{base_style(bg, color, style, "60px 48px")}">
  {lbl_html}
  <h1 style="{title_style(color, style, "30px")}">{company}</h1>
  {sub_html}
  {line}
  <p style="{body_style(color)}margin-top:16px;\
opacity:0.8;">{content.body_text}</p>
  {tags}
  {line_b}
</div>"""


def render_profile_namecard(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """명함 스타일 - 좌우 2단 구성."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title
    region = profile.region or ""

    svc_items = ""
    for i, s in enumerate(profile.services[:4], 1):
        svc_items += (
            f'<div style="padding:8px 0;border-bottom:1px solid {color}15;">'
            f'<span style="color:{accent};font-weight:700;'
            f'margin-right:8px;">{i:02d}</span>'
            f'<span style="font-size:14px;color:{color};">{s.name}</span></div>'
        )

    body = content.body_text or profile.usp or ""

    return f"""\
<div style="{base_style(bg, color, style, "50px 48px")}">
  <div style="display:flex;gap:32px;align-items:flex-start;">
    <div style="flex:0 0 38%;">
      <h2 style="font-size:24px;color:{color};\
font-weight:{style.font_weight_title};\
margin:0 0 8px;word-break:keep-all;">{company}</h2>
      <p style="font-size:13px;color:{color};opacity:0.5;\
margin:0 0 16px;">{region}</p>
      <div style="width:30px;height:3px;background:{accent};"></div>
    </div>
    <div style="flex:1;">{svc_items}</div>
  </div>
  <p style="{body_style(color)}margin-top:24px;\
opacity:0.7;">{body}</p>
</div>"""


def render_brand_statement(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """브랜드 선언문 - 중앙 정렬 슬로건."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title
    statement = content.title or company
    body = content.body_text or profile.usp or ""

    return f"""\
<div style="width:100%;max-width:720px;padding:70px 48px;\
background:{bg};text-align:center;font-family:{FONT_PRIMARY};\
box-sizing:border-box;">
  <p style="font-size:11px;color:{accent};letter-spacing:5px;\
font-weight:600;margin:0 0 20px;text-transform:uppercase;">\
{company}</p>
  <h1 style="font-size:28px;color:{color};\
font-weight:{style.font_weight_title};\
line-height:1.5;margin:0 0 20px;word-break:keep-all;">\
{statement}</h1>
  <div style="width:60px;height:2px;background:{accent};\
margin:0 auto 20px;"></div>
  <p style="font-size:15px;color:{color};opacity:0.6;\
line-height:1.8;margin:0;">{body}</p>
</div>"""


def render_story_opener(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """감성 질문 대형 텍스트 + 하단 업체 소개."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title
    question = content.body_text or content.title
    region = profile.region or ""
    usp = profile.usp or content.subtitle or ""

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}">
  <p style="font-size:24px;color:{color};font-family:{FONT_HANDWRITING};\
line-height:1.8;margin:0 0 32px;word-break:keep-all;">\
{question}</p>
  <div style="width:40px;height:2px;background:{accent};\
opacity:0.4;margin:0 0 24px;"></div>
  <p style="font-size:14px;color:{color};opacity:0.5;\
margin:0 0 4px;font-weight:600;">{company}</p>
  <p style="font-size:13px;color:{color};opacity:0.4;\
margin:0;">{region} {usp}</p>
</div>"""


def _service_tags(profile: ClientProfile, accent: str) -> str:
    """서비스 태그 pill badges를 생성한다."""
    if not profile.services:
        return ""
    badges = [
        f'<span style="display:inline-block;padding:6px 14px;'
        f"background:{accent}15;color:{accent};border-radius:20px;"
        f"font-size:12px;font-weight:600;"
        f'letter-spacing:0.5px;margin:4px;">{s.name}</span>'
        for s in profile.services[:5]
    ]
    return f'<div style="margin-top:20px;">{"".join(badges)}</div>'


INTRO_RENDERERS: dict[str, Callable[..., str]] = {
    "quote_greeting": render_quote_greeting,
    "magazine_header": render_magazine_header,
    "profile_namecard": render_profile_namecard,
    "brand_statement": render_brand_statement,
    "story_opener": render_story_opener,
}
