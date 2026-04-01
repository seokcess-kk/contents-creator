"""디자인 카드 HTML 생성. 헤더/CTA 이미지를 HTML로 생성한다.

패턴 카드의 색상 팔레트와 클라이언트 프로필 기반.
680px 너비 고정 (네이버 블로그 기준).
"""

from __future__ import annotations

from domain.analysis.model import PatternCard
from domain.generation.model import DesignCard
from domain.profile.model import ClientProfile


def generate_header_card(
    keyword: str,
    title: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> DesignCard:
    """헤더 디자인 카드 HTML을 생성한다."""
    palette = pattern_card.visual_pattern.get("color_palette", ["#333333", "#ffffff"])
    primary = palette[0] if palette else "#333333"
    bg = palette[1] if len(palette) > 1 else "#f5f5f5"
    accent = palette[2] if len(palette) > 2 else "#4a90d9"

    html = f"""\
<div style="width:680px;padding:60px 40px;background:{bg};text-align:center;font-family:'Nanum Gothic',sans-serif;">
  <p style="font-size:14px;color:{accent};margin:0 0 12px;letter-spacing:2px;">
    {profile.company_name or keyword}
  </p>
  <h1 style="font-size:28px;color:{primary};margin:0 0 16px;line-height:1.4;font-weight:700;">
    {title}
  </h1>
  <p style="font-size:15px;color:#666;margin:0;">
    {profile.usp or keyword}
  </p>
</div>"""

    return DesignCard(
        card_type="header",
        html=html,
        title=title,
        subtitle=profile.usp or keyword,
        color_primary=primary,
        color_background=bg,
        color_accent=accent,
    )


def generate_cta_card(
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> DesignCard:
    """CTA 디자인 카드 HTML을 생성한다."""
    palette = pattern_card.visual_pattern.get("color_palette", ["#333333", "#ffffff"])
    accent = palette[2] if len(palette) > 2 else "#4a90d9"
    bg = palette[1] if len(palette) > 1 else "#f0f4f8"

    company = profile.company_name or "문의하기"
    region = profile.region or ""
    cta_text = f"{company} 상담 예약"

    html = f"""\
<div style="width:680px;padding:40px;background:{bg};text-align:center;font-family:'Nanum Gothic',sans-serif;">
  <p style="font-size:20px;color:#333;margin:0 0 12px;font-weight:700;">
    지금 바로 상담받아 보세요
  </p>
  <p style="font-size:15px;color:#666;margin:0 0 24px;">
    {region} {company}
  </p>
  <div style="display:inline-block;padding:14px 40px;background:{accent};color:#fff;border-radius:8px;font-size:16px;font-weight:600;">
    {cta_text}
  </div>
</div>"""

    return DesignCard(
        card_type="cta",
        html=html,
        title=cta_text,
        color_primary="#333333",
        color_background=bg,
        color_accent=accent,
    )
