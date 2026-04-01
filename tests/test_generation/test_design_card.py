"""디자인 카드 테스트."""

from __future__ import annotations

from domain.analysis.model import PatternCard
from domain.generation.design_card import generate_cta_card, generate_header_card
from domain.profile.model import ClientProfile


def _make_card_and_profile() -> tuple[PatternCard, ClientProfile]:
    card = PatternCard(
        keyword="강남 피부과",
        visual_pattern={"color_palette": ["#2c3e50", "#ecf0f1", "#3498db"]},
    )
    profile = ClientProfile(
        company_name="클리어스킨 피부과",
        region="서울 강남구",
        usp="20년 경력 피부과 전문의의 1:1 맞춤 케어",
    )
    return card, profile


class TestHeaderCard:
    def test_generates_html(self) -> None:
        card, profile = _make_card_and_profile()
        result = generate_header_card("강남 피부과", "여드름 관리법", card, profile)
        assert result.card_type == "header"
        assert "680px" in result.html
        assert "클리어스킨" in result.html

    def test_uses_palette_colors(self) -> None:
        card, profile = _make_card_and_profile()
        result = generate_header_card("test", "test title", card, profile)
        assert "#2c3e50" in result.html


class TestCtaCard:
    def test_generates_html(self) -> None:
        card, profile = _make_card_and_profile()
        result = generate_cta_card(card, profile)
        assert result.card_type == "cta"
        assert "680px" in result.html
        assert "상담" in result.html

    def test_includes_company_name(self) -> None:
        card, profile = _make_card_and_profile()
        result = generate_cta_card(card, profile)
        assert "클리어스킨" in result.html
