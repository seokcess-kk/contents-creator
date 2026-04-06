"""카드 레이아웃 변이 레지스트리.

카드 타입별 5종 레이아웃의 이름, 설명, Gemini 프롬프트 지시문을 관리한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardLayoutSpec:
    """레이아웃 변이 스펙."""

    name: str
    card_type: str  # "intro" | "transition" | "cta"
    description_ko: str
    gemini_instruction: str
    font_style: str = "formal"  # "formal" | "handwriting" | "mixed"


# === intro 레이아웃 5종 ===

INTRO_LAYOUTS: list[CardLayoutSpec] = [
    CardLayoutSpec(
        name="quote_greeting",
        card_type="intro",
        description_ko="큰따옴표 인사말 + 원장명 서명",
        font_style="mixed",
        gemini_instruction=(
            "Layout: Start with large decorative quotation marks. "
            "Inside the quotes, a warm greeting message in handwriting-style font. "
            "Below the closing quote, right-aligned signature: representative name + company. "
            "Thin accent line separator. One-line body text in regular font below. "
            "Light warm background. Generous vertical padding (70px+)."
        ),
    ),
    CardLayoutSpec(
        name="magazine_header",
        card_type="intro",
        description_ko="매거진 헤더 - 대형 타이틀 + 서비스 배지",
        gemini_instruction=(
            "Layout: Bold oversized company name as title (28-32px, heavy weight). "
            "Thin accent line (40px wide, 3px) below title. "
            "Subtitle in lighter weight, muted color. "
            "Body text with generous line-height. "
            "Service tags as pill-shaped badges at bottom (rounded, tinted accent bg). "
            "Left-aligned, editorial magazine aesthetic."
        ),
    ),
    CardLayoutSpec(
        name="profile_namecard",
        card_type="intro",
        description_ko="명함 스타일 - 좌우 2단 구성",
        gemini_instruction=(
            "Layout: Two-column namecard style using flexbox. "
            "Left column (40%): company name large, region small below, accent line. "
            "Right column (60%): service items as a clean vertical list with numbering. "
            "Bottom: one-line USP or body text spanning full width. "
            "Light background, minimal decoration, professional."
        ),
    ),
    CardLayoutSpec(
        name="brand_statement",
        card_type="intro",
        description_ko="브랜드 선언문 - 중앙 정렬 슬로건",
        gemini_instruction=(
            "Layout: Center-aligned brand manifesto style. "
            "Small uppercase label at top (company name, letter-spacing 4px+). "
            "Large bold title as brand statement (28px+). "
            "Thin horizontal accent line (centered, 60px wide). "
            "Body text below in muted color, centered. "
            "Clean white or off-white background, symmetrical padding."
        ),
    ),
    CardLayoutSpec(
        name="story_opener",
        card_type="intro",
        description_ko="감성 질문 대형 텍스트 + 하단 업체 소개",
        font_style="mixed",
        gemini_instruction=(
            "Layout: Large empathetic question as hero text (24-28px, handwriting font). "
            "Generous whitespace around the question. "
            "Thin divider line. "
            "Below: small company intro block — company name + region + one-line USP. "
            "Warm tinted background. The question should feel personal and emotional."
        ),
    ),
]

# === transition 레이아웃 5종 ===

TRANSITION_LAYOUTS: list[CardLayoutSpec] = [
    CardLayoutSpec(
        name="hashtag_keycopy",
        card_type="transition",
        description_ko="해시태그 스타일 키카피 + 다크 배경",
        gemini_instruction=(
            "Layout: Dark rich background. "
            "Large title prefixed with '#' symbol in accent color (e.g. '#사람을 위한 다이어트'). "
            "Title font 26px+, bold. "
            "Below: body text in lighter opacity, 1-2 lines max. "
            "Accent line at top or bottom. Center-aligned. "
            "Cinematic, impactful feel."
        ),
    ),
    CardLayoutSpec(
        name="big_question",
        card_type="transition",
        description_ko="대형 질문 1줄 + 답변 티저",
        gemini_instruction=(
            "Layout: Dark background. "
            "Single large question as title (26-30px, bold, full width). "
            "Thin horizontal divider line below the question. "
            "Short answer teaser as body text (smaller, muted). "
            "Lots of vertical whitespace. Minimal elements."
        ),
    ),
    CardLayoutSpec(
        name="stat_highlight",
        card_type="transition",
        description_ko="통계/숫자 중앙 강조",
        gemini_instruction=(
            "Layout: Dark background. "
            "Badge text displayed as large centered number/stat (36-42px, accent color, bold). "
            "Small label above the number in uppercase. "
            "Title as context line below the number (18px, normal weight). "
            "Body text as footnote (small, muted). "
            "Dramatic focus on the central number."
        ),
    ),
    CardLayoutSpec(
        name="emotional_quote",
        card_type="transition",
        description_ko="감성 인용문 + 손글씨체",
        font_style="handwriting",
        gemini_instruction=(
            "Layout: Dark background. "
            "Large decorative opening quote mark in accent color. "
            "Title as emotional quote in handwriting-style font (24px+). "
            "No closing quote needed — let it feel open-ended. "
            "Body text below as attribution or context (small, muted). "
            "Accent line at bottom. Poetic, reflective mood."
        ),
    ),
    CardLayoutSpec(
        name="split_contrast",
        card_type="transition",
        description_ko="상하 2분할 대비 (문제/전환)",
        gemini_instruction=(
            "Layout: Vertically split into two halves. "
            "Top half: dark background, title text representing the problem/pain. "
            "Bottom half: light/accent-tinted background, body text as the transition/hope. "
            "Clear visual contrast between the two halves. "
            "Each half has its own padding (30px+). Thin accent line at the split point."
        ),
    ),
]

# === cta 레이아웃 5종 ===

CTA_LAYOUTS: list[CardLayoutSpec] = [
    CardLayoutSpec(
        name="service_grid",
        card_type="cta",
        description_ko="서비스 2열 그리드 + 연락처",
        gemini_instruction=(
            "Layout: Light or dark background. "
            "Title at top (CTA message, bold, 22px+). "
            "Below: service items displayed as 2-column grid cards "
            "(each with number prefix, border or subtle background). "
            "Bottom section: company name + phone + address in smaller text. "
            "Clean, organized, informational."
        ),
    ),
    CardLayoutSpec(
        name="single_action",
        card_type="cta",
        description_ko="대형 CTA + 전화번호 강조",
        gemini_instruction=(
            "Layout: Dark background. "
            "One bold CTA title (24-28px, centered). "
            "Phone number displayed large and prominent below (20px+, accent color). "
            "Company name small above or below phone. "
            "Minimal — no lists, no grid, just the core action. "
            "Optional: subtle accent line or dot separator."
        ),
    ),
    CardLayoutSpec(
        name="warm_invitation",
        card_type="cta",
        description_ko="따뜻한 초대 메시지 + 서명",
        font_style="mixed",
        gemini_instruction=(
            "Layout: Light warm background. "
            "Opening quote marks with invitation message in handwriting font. "
            "Below: representative name + company as signature (right-aligned). "
            "Bottom section: phone and address in small formal font. "
            "Feels like a personal letter or invitation card."
        ),
    ),
    CardLayoutSpec(
        name="info_stack",
        card_type="cta",
        description_ko="정보 블록 수직 스택",
        gemini_instruction=(
            "Layout: Dark background. "
            "Title as CTA message at top. "
            "Below: vertically stacked info blocks, each with a label and value. "
            "Blocks: company name, consultation hours (if available), phone, address. "
            "Each block separated by thin line or spacing. "
            "Left-aligned, structured, professional."
        ),
    ),
    CardLayoutSpec(
        name="brand_closing",
        card_type="cta",
        description_ko="브랜드명 대형 타이포 + 최소 연락처",
        gemini_instruction=(
            "Layout: Dark background. "
            "Company name as hero text (28-36px, bold, centered). "
            "Thin accent line below company name. "
            "One-line subtitle or USP (small, muted). "
            "Phone and region at bottom in minimal style. "
            "Brand-focused, memorable closing impression."
        ),
    ),
]

_ALL_LAYOUTS: dict[str, list[CardLayoutSpec]] = {
    "intro": INTRO_LAYOUTS,
    "transition": TRANSITION_LAYOUTS,
    "cta": CTA_LAYOUTS,
}


def get_layout_names(card_type: str) -> list[str]:
    """카드 타입의 레이아웃 이름 목록을 반환한다."""
    layouts = _ALL_LAYOUTS.get(card_type, [])
    return [spec.name for spec in layouts]


def get_layout_spec(card_type: str, layout_name: str) -> CardLayoutSpec | None:
    """특정 레이아웃 스펙을 반환한다."""
    layouts = _ALL_LAYOUTS.get(card_type, [])
    for spec in layouts:
        if spec.name == layout_name:
            return spec
    return None


def get_gemini_instructions(
    card_layouts: dict[str, str],
) -> dict[str, str]:
    """카드 타입별 Gemini 프롬프트 지시문을 반환한다."""
    result: dict[str, str] = {}
    for card_type, layout_name in card_layouts.items():
        spec = get_layout_spec(card_type, layout_name)
        if spec:
            result[card_type] = spec.gemini_instruction
    return result
