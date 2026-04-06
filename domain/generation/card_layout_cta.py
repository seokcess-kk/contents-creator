"""cta 카드 레이아웃 렌더러 5종.

service_grid, single_action, warm_invitation, info_stack, brand_closing
"""

from __future__ import annotations

from collections.abc import Callable

from domain.generation.card_templates import (
    FONT_HANDWRITING,
    VisualStyle,
    accent_line,
    base_style,
    title_dark_style,
)
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile


def render_service_grid(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """서비스 2열 그리드 + 연락처."""
    bg = style.bg_light
    color = style.text_on_light
    company = profile.company_name or content.title

    items = content.items or [s.name for s in profile.services[:4]]
    grid_cells = ""
    for i, item in enumerate(items[:4], 1):
        grid_cells += (
            f'<div style="padding:14px 16px;background:{color}08;'
            f'border:1px solid {color}10;border-radius:8px;">'
            f'<span style="color:{accent};font-weight:700;'
            f'margin-right:8px;font-size:14px;">{i:02d}</span>'
            f'<span style="font-size:14px;color:{color};">'
            f"{item}</span></div>"
        )

    contact = _contact_block(profile, color, "0.6")

    return f"""\
<div style="{base_style(bg, color, style, "60px 48px")}">
  <h2 style="font-size:22px;color:{color};\
font-weight:{style.font_weight_title};\
margin:0 0 24px;word-break:keep-all;">{content.title}</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;\
gap:10px;margin:0 0 28px;">{grid_cells}</div>
  <div style="width:40px;height:2px;background:{accent};\
margin:0 0 20px;opacity:0.4;"></div>
  <p style="font-size:16px;color:{color};font-weight:700;\
margin:0 0 8px;">{company}</p>
  {contact}
</div>"""


def render_single_action(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """대형 CTA + 전화번호 강조."""
    bg = style.bg_dark
    color = style.text_on_dark
    phone = profile.phone or ""
    company = profile.company_name or content.title

    phone_html = ""
    if phone:
        phone_html = (
            f'<p style="font-size:22px;color:{accent};font-weight:700;'
            f'margin:24px 0 0;letter-spacing:1px;">{phone}</p>'
        )

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}text-align:center;">
  <p style="font-size:13px;color:{color};opacity:0.4;\
margin:0 0 16px;letter-spacing:3px;font-weight:600;">\
{company}</p>
  <h2 style="font-size:26px;color:{color};\
font-weight:{style.font_weight_title};\
line-height:1.5;margin:0;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.3);">{content.title}</h2>
  {phone_html}
</div>"""


def render_warm_invitation(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """따뜻한 초대 메시지 + 서명 + 연락처."""
    bg = style.bg_light
    color = style.text_on_light
    rep = profile.representative or profile.company_name
    company = profile.company_name or content.title
    invitation = content.body_text or content.title

    contact = _contact_block(profile, color, "0.5")

    return f"""\
<div style="{base_style(bg, color, style, "60px 48px")}">
  <div style="font-size:42px;color:{accent};opacity:0.3;\
line-height:1;margin:0 0 8px;font-family:Georgia,serif;">\u201c</div>
  <p style="font-size:20px;color:{color};font-family:{FONT_HANDWRITING};\
line-height:1.8;margin:0 0 4px;word-break:keep-all;">\
{invitation}</p>
  <div style="font-size:42px;color:{accent};opacity:0.3;\
line-height:1;margin:0 0 20px;text-align:right;\
font-family:Georgia,serif;">\u201d</div>
  <p style="font-size:14px;color:{color};opacity:0.6;\
text-align:right;margin:0 0 24px;">{company} {rep}</p>
  <div style="width:40px;height:2px;background:{accent};\
margin:0 0 16px;opacity:0.3;"></div>
  {contact}
</div>"""


def render_info_stack(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """정보 블록 수직 스택."""
    bg = style.bg_dark
    color = style.text_on_dark
    company = profile.company_name or content.title
    line = accent_line(accent, style, card_index)

    rows: list[tuple[str, str]] = [("", company)]
    if profile.phone:
        rows.append(("T.", profile.phone))
    if profile.address:
        rows.append(("", profile.address))
    elif profile.region:
        rows.append(("", profile.region))

    stack_html = ""
    for label, value in rows:
        lbl = (
            f'<span style="color:{accent};font-size:12px;font-weight:600;\
margin-right:8px;letter-spacing:1px;">{label}</span>'
            if label
            else ""
        )
        stack_html += (
            f'<div style="padding:12px 0;border-bottom:1px solid {color}15;">'
            f"{lbl}"
            f'<span style="font-size:15px;color:{color};opacity:0.8;">'
            f"{value}</span></div>"
        )

    return f"""\
<div style="{base_style(bg, color, style, "60px 48px")}">
  {line}
  <h2 style="{title_dark_style(color, style, "22px")}\
margin-bottom:24px;">{content.title}</h2>
  <div>{stack_html}</div>
</div>"""


def render_brand_closing(
    content: CardContent,
    style: VisualStyle,
    accent: str,
    profile: ClientProfile,
    card_index: int = 0,
    total_cards: int = 1,
) -> str:
    """브랜드명 대형 타이포 + 최소 연락처."""
    bg = style.bg_dark
    color = style.text_on_dark
    company = profile.company_name or content.title
    sub = content.subtitle or profile.usp or ""

    contact_parts: list[str] = []
    if profile.phone:
        contact_parts.append(profile.phone)
    if profile.region:
        contact_parts.append(profile.region)
    contact_text = " | ".join(contact_parts)

    return f"""\
<div style="{base_style(bg, color, style, "70px 48px")}text-align:center;">
  <h1 style="font-size:32px;color:{color};\
font-weight:900;letter-spacing:-0.5px;\
margin:0 0 16px;word-break:keep-all;\
text-shadow:0 1px 2px rgba(0,0,0,0.3);">{company}</h1>
  <div style="width:50px;height:2px;background:{accent};\
margin:0 auto 16px;"></div>
  <p style="font-size:14px;color:{color};opacity:0.6;\
margin:0 0 20px;line-height:1.6;">{sub}</p>
  <p style="font-size:13px;color:{color};opacity:0.4;\
margin:0;letter-spacing:0.5px;">{contact_text}</p>
</div>"""


def _contact_block(
    profile: ClientProfile,
    color: str,
    opacity: str,
) -> str:
    """연락처 블록을 생성한다."""
    lines: list[str] = []
    if profile.phone:
        lines.append(f"T. {profile.phone}")
    if profile.address:
        lines.append(profile.address)
    elif profile.region:
        lines.append(profile.region)
    if not lines:
        return ""
    items = "".join(
        f'<p style="font-size:13px;color:{color};opacity:{opacity};margin:3px 0;">{cl}</p>'
        for cl in lines
    )
    return f"<div>{items}</div>"


CTA_RENDERERS: dict[str, Callable[..., str]] = {
    "service_grid": render_service_grid,
    "single_action": render_single_action,
    "warm_invitation": render_warm_invitation,
    "info_stack": render_info_stack,
    "brand_closing": render_brand_closing,
}
