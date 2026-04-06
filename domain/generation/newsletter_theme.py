"""뉴스레터 테마 프리셋.

카드 + 본문 HTML이 동일한 디자인 토큰을 공유하도록 한다.
각 테마는 색상, 타이포, 장식 요소를 하나의 세트로 정의한다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class NewsletterTheme:
    """뉴스레터 디자인 테마."""

    name: str

    # 색상
    bg_primary: str  # 본문 배경
    bg_section: str  # 섹션 배경 (교차용)
    bg_card_light: str  # 카드 라이트 배경
    bg_card_dark: str  # 카드 다크 배경
    text_primary: str  # 본문 텍스트
    text_heading: str  # 제목 색상
    text_muted: str  # 보조 텍스트
    accent: str  # 악센트 (하이라이트, 구분선, 불릿)
    accent_light: str  # 악센트 연한 버전

    # 타이포
    font_heading: str  # 제목 폰트
    font_body: str  # 본문 폰트
    heading_weight: str  # 제목 두께
    heading_size: str  # h1 크기
    subheading_size: str  # h2 크기

    # 장식
    highlight_bg: str  # 형광펜 배경
    quote_bg: str  # 인용문 배경
    divider_style: str  # 구분선 유형: "line" | "dot" | "accent"
    border_radius: str  # 섹션/카드 둥글기


THEMES: list[NewsletterTheme] = [
    # 1. Classic Editorial — 세리프 제목, 깔끔한 흑백 + 블루 악센트
    NewsletterTheme(
        name="classic_editorial",
        bg_primary="#ffffff",
        bg_section="#f8f9fa",
        bg_card_light="#f8f9fa",
        bg_card_dark="#1a1a2e",
        text_primary="#333333",
        text_heading="#111111",
        text_muted="#888888",
        accent="#2E54FF",
        accent_light="rgba(46,84,255,0.08)",
        font_heading="Georgia,'Nanum Myeongjo',serif",
        font_body="'Pretendard','Nanum Gothic',sans-serif",
        heading_weight="700",
        heading_size="28px",
        subheading_size="21px",
        highlight_bg="rgba(46,84,255,0.12)",
        quote_bg="#f0f2f8",
        divider_style="line",
        border_radius="8px",
    ),
    # 2. Warm Earth — 따뜻한 톤, 브라운/골드 악센트
    NewsletterTheme(
        name="warm_earth",
        bg_primary="#faf6f0",
        bg_section="#f0ebe3",
        bg_card_light="#faf6f0",
        bg_card_dark="#3d2b1f",
        text_primary="#3d3330",
        text_heading="#2a1f17",
        text_muted="#8a7d74",
        accent="#c4956a",
        accent_light="rgba(196,149,106,0.12)",
        font_heading="'Pretendard','Nanum Gothic',sans-serif",
        font_body="'Pretendard','Nanum Gothic',sans-serif",
        heading_weight="800",
        heading_size="28px",
        subheading_size="21px",
        highlight_bg="rgba(196,149,106,0.2)",
        quote_bg="#f5ede3",
        divider_style="accent",
        border_radius="16px",
    ),
    # 3. Modern Minimal — 무채색 + 기하학 악센트
    NewsletterTheme(
        name="modern_minimal",
        bg_primary="#ffffff",
        bg_section="#f5f5f5",
        bg_card_light="#f5f5f5",
        bg_card_dark="#111111",
        text_primary="#222222",
        text_heading="#000000",
        text_muted="#999999",
        accent="#222222",
        accent_light="rgba(0,0,0,0.04)",
        font_heading="'Pretendard','Nanum Gothic',sans-serif",
        font_body="'Pretendard','Nanum Gothic',sans-serif",
        heading_weight="900",
        heading_size="30px",
        subheading_size="22px",
        highlight_bg="rgba(0,0,0,0.06)",
        quote_bg="#f0f0f0",
        divider_style="line",
        border_radius="0",
    ),
    # 4. Soft Sage — 세이지 그린, 자연스러운 차분함
    NewsletterTheme(
        name="soft_sage",
        bg_primary="#f9faf7",
        bg_section="#f0f3ec",
        bg_card_light="#f4f6f0",
        bg_card_dark="#2c3527",
        text_primary="#3a3d36",
        text_heading="#1e2119",
        text_muted="#7d8574",
        accent="#6b8f5e",
        accent_light="rgba(107,143,94,0.1)",
        font_heading="Georgia,'Nanum Myeongjo',serif",
        font_body="'Pretendard','Nanum Gothic',sans-serif",
        heading_weight="700",
        heading_size="27px",
        subheading_size="20px",
        highlight_bg="rgba(107,143,94,0.15)",
        quote_bg="#eef2ea",
        divider_style="dot",
        border_radius="12px",
    ),
    # 5. Deep Navy — 네이비 악센트, 전문적 권위감
    NewsletterTheme(
        name="deep_navy",
        bg_primary="#ffffff",
        bg_section="#f4f6f9",
        bg_card_light="#f4f6f9",
        bg_card_dark="#0f1b33",
        text_primary="#2c3e50",
        text_heading="#0f1b33",
        text_muted="#7f8c9b",
        accent="#1a3a6b",
        accent_light="rgba(26,58,107,0.06)",
        font_heading="'Pretendard','Nanum Gothic',sans-serif",
        font_body="'Pretendard','Nanum Gothic',sans-serif",
        heading_weight="800",
        heading_size="28px",
        subheading_size="21px",
        highlight_bg="rgba(26,58,107,0.1)",
        quote_bg="#edf0f7",
        divider_style="accent",
        border_radius="10px",
    ),
]

_THEME_MAP: dict[str, NewsletterTheme] = {t.name: t for t in THEMES}


def pick_theme() -> NewsletterTheme:
    """테마를 랜덤 선택한다."""
    return random.choice(THEMES)


def get_theme(name: str) -> NewsletterTheme | None:
    """이름으로 테마를 조회한다."""
    return _THEME_MAP.get(name)


def get_theme_names() -> list[str]:
    """사용 가능한 테마 이름 목록을 반환한다."""
    return [t.name for t in THEMES]
