"""Gemini 기반 카드 HTML 디자인 생성.

콘텐츠 + 디자인 지시를 받아 Gemini가 반응형 HTML/CSS를 직접 생성한다.
3종 카드(intro, transition, cta)만 생성한다.
"""

from __future__ import annotations

import logging
import re

from domain.common import gemini_client
from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)

CARD_HTML_SYSTEM = """\
You are a professional web designer specializing in branded image cards \
for Korean Naver blog posts.

MANDATORY RULES:
- Use width:100% with max-width:720px. Wrap each card in a single <div>
- Inline CSS ONLY (no <style> tags)
- Font system (choose per card based on layout instruction):
  - Primary: 'Pretendard', 'Nanum Gothic', 'Malgun Gothic', sans-serif
  - Handwriting: 'Nanum Pen Script', 'Nanum Gothic', cursive \
(use for quotes, greetings, emotional text only)
- NO emoji, NO icon fonts, NO external resources
- FOLLOW the LAYOUT STRUCTURE instruction for each card exactly
- Subtle gradients, refined spacing, clear visual hierarchy
- Maintain visual consistency across all cards (one cohesive series)
- Generous padding (60px+ vertical, 48px horizontal)
- NO buttons or button-like elements (no "상담 예약", "예약하기" buttons). \
CTA cards should end with text information only (company name, phone, address)
- Separate each card with === CARD N === delimiter
- Return ONLY HTML code. No explanations, no comments

IMPORTANT COLOR GUIDANCE:
- The provided palette colors are a starting point. \
Derive a harmonious color scheme from them
- Ensure sufficient contrast between text and background
- Use tints and shades of the accent color, not raw hex values
- Dark cards should use deep, rich tones (not pure black)
- Light cards should use warm off-whites or subtle tinted backgrounds
"""

MEDICAL_HTML_INJECTION = """
Medical advertising law compliance:
- Never include prohibited expressions like "100% cure", \
"guaranteed results", "the best"
- Disclaimer card MUST include the provided disclaimer text
"""


def _build_html_prompt(
    contents: list[CardContent],
    profile: ClientProfile,
    colors: dict[str, str],
    layout_specs: dict[str, str] | None = None,
) -> str:
    """카드 HTML 생성 프롬프트를 구성한다."""
    cards_desc = []
    for i, c in enumerate(contents, 1):
        desc = f"--- Card {i}: {c.card_type.upper()} ---\n"
        if c.card_type == "disclaimer":
            desc += f"Disclaimer text: {DISCLAIMER_TEMPLATE}\n"
        else:
            if c.title:
                desc += f"Title: {c.title}\n"
            if c.subtitle:
                desc += f"Subtitle: {c.subtitle}\n"
            if c.body_text:
                desc += f"Body: {c.body_text}\n"
            if c.items:
                desc += "Items:\n"
                for j, item in enumerate(c.items, 1):
                    desc += f"  {j:02d}. {item}\n"
            if c.badge_text:
                desc += f"Badge: {c.badge_text}\n"

            # 레이아웃 구조 지시 주입
            if layout_specs and c.card_type in layout_specs:
                desc += f"LAYOUT STRUCTURE:\n{layout_specs[c.card_type]}\n"

            # 카드 타입별 추가 정보
            if c.card_type in ("greeting", "intro"):
                services = ", ".join(s.name for s in profile.services[:5])
                if services:
                    desc += f"Service tags: {services}\n"
                desc += f"Company: {profile.company_name}\n"
                if profile.photo_path:
                    desc += (
                        "NOTE: Include a circular photo placeholder (80px) "
                        "at the top of this card.\n"
                    )
            elif c.card_type == "service":
                services = ", ".join(s.name for s in profile.services[:5])
                desc += f"Services: {services}\n"
                desc += f"USP: {profile.usp}\n"
            elif c.card_type in ("cta",):
                if profile.phone:
                    desc += f"Phone: {profile.phone}\n"
                if profile.address:
                    desc += f"Address: {profile.address}\n"
                elif profile.region:
                    desc += f"Region: {profile.region}\n"
                desc += f"Company: {profile.company_name}\n"

        cards_desc.append(desc)

    return f"""\
Design {len(contents)} branded cards as independent HTML blocks.
Each card should use width:100% with max-width:720px.
All cards must look like one cohesive visual series.

These cards will be inserted WITHIN a blog text flow, \
not stacked at the top. Design them to blend naturally with surrounding text.

Color palette (starting point — derive harmonious shades):
- Primary: {colors.get("primary", "#333333")}
- Background: {colors.get("background", "#FAFAF8")}
- Accent: {colors.get("accent", "#4a90d9")}

Business: {profile.company_name} ({profile.industry} > {profile.sub_category})
Tone: {profile.tone_and_manner or "professional yet warm"}

{"".join(cards_desc)}
Separate each card with === CARD N === delimiter.
"""


def _parse_cards(raw: str, expected_count: int) -> list[str]:
    """LLM 응답에서 개별 카드 HTML을 추출한다."""
    # 마크다운 코드 블록 제거
    cleaned = re.sub(r"```html?\s*\n?", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)

    # === CARD N === 구분자로 분리
    parts = re.split(r"===\s*CARD\s*\d+\s*===", cleaned)
    parts = [p.strip() for p in parts if p.strip()]

    html_cards: list[str] = []
    for part in parts:
        extracted = _extract_top_div(part)
        if extracted:
            html_cards.append(extracted)

    # 구분자 없이 연속된 <div> 블록일 수도 있음
    if len(html_cards) < expected_count and "<div" in cleaned:
        html_cards = _extract_all_top_divs(cleaned)

    return html_cards


def _extract_top_div(text: str) -> str:
    """텍스트에서 최상위 <div>...</div> 블록을 추출한다."""
    if "<div" not in text:
        return ""
    start = text.index("<div")
    depth = 0
    i = start
    while i < len(text):
        if text[i:].startswith("<div"):
            depth += 1
            i += 4
        elif text[i:].startswith("</div>"):
            depth -= 1
            i += 6
            if depth == 0:
                return text[start:i]
        else:
            i += 1
    if "</div>" in text:
        last_end = text.rindex("</div>") + 6
        return text[start:last_end]
    return ""


def _extract_all_top_divs(text: str) -> list[str]:
    """텍스트에서 모든 최상위 <div> 블록을 순서대로 추출한다."""
    cards: list[str] = []
    pos = 0
    while pos < len(text):
        idx = text.find("<div", pos)
        if idx == -1:
            break
        depth = 0
        i = idx
        found_end = False
        while i < len(text):
            if text[i:].startswith("<div"):
                depth += 1
                i += 4
            elif text[i:].startswith("</div>"):
                depth -= 1
                i += 6
                if depth == 0:
                    cards.append(text[idx:i])
                    pos = i
                    found_end = True
                    break
            else:
                i += 1
        if not found_end:
            break
    return cards


def generate_card_htmls(
    contents: list[CardContent],
    profile: ClientProfile,
    colors: dict[str, str],
    layout_specs: dict[str, str] | None = None,
) -> list[str]:
    """Gemini로 카드 HTML을 일괄 생성한다.

    Returns:
        카드별 HTML 문자열 리스트 (contents와 동일 순서)
    """
    if not contents:
        return []

    system = CARD_HTML_SYSTEM
    if profile.is_medical():
        system += MEDICAL_HTML_INJECTION

    prompt = _build_html_prompt(contents, profile, colors, layout_specs)

    logger.info("카드 HTML 디자인 생성 중 (Gemini, %d장)...", len(contents))
    raw = gemini_client.chat(
        prompt,
        system=system,
        max_tokens=16384,
        temperature=0.7,
    )

    logger.info(
        "Gemini 응답: %d자, <div> %d개",
        len(raw),
        raw.count("<div"),
    )

    html_cards = _parse_cards(raw, len(contents))

    if len(html_cards) < len(contents):
        logger.warning(
            "Gemini HTML 파싱: %d/%d장 추출 (부족분은 빈 문자열)",
            len(html_cards),
            len(contents),
        )
        html_cards.extend([""] * (len(contents) - len(html_cards)))

    logger.info("카드 HTML 생성 완료 (Gemini): %d장", len(html_cards))
    return html_cards[: len(contents)]
