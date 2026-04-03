"""디자인 카드 테스트."""

from __future__ import annotations

from domain.generation.card_templates import (
    STYLE_POOL,
    render_card_html,
    render_cta,
    render_intro,
    render_transition,
)
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile


def _make_profile() -> ClientProfile:
    return ClientProfile(
        company_name="클리어스킨 피부과",
        region="서울 강남구",
        industry="의료",
        sub_category="피부과",
        usp="20년 경력 피부과 전문의의 1:1 맞춤 케어",
        phone="02-1234-5678",
    )


class TestIntroCard:
    def test_generates_html(self) -> None:
        content = CardContent(
            card_type="intro",
            title="클리어스킨 피부과",
            subtitle="20년 경력 전문의",
            body_text="강남 피부과 전문의가 알려드립니다.",
        )
        style = STYLE_POOL[0]
        profile = _make_profile()
        html = render_intro(content, style, "#3498db", profile)
        assert "max-width:720px" in html
        assert "클리어스킨" in html

    def test_has_gradient_background(self) -> None:
        content = CardContent(card_type="intro", title="테스트")
        style = STYLE_POOL[0]
        profile = _make_profile()
        html = render_intro(content, style, "#3498db", profile)
        assert "linear-gradient" in html


class TestTransitionCard:
    def test_generates_html(self) -> None:
        content = CardContent(
            card_type="transition",
            title="이제 달라질 수 있습니다",
            body_text="고민에서 솔루션으로.",
        )
        style = STYLE_POOL[0]
        html = render_transition(content, style, "#3498db")
        assert "max-width:720px" in html
        assert "달라질" in html

    def test_dark_background(self) -> None:
        content = CardContent(card_type="transition", title="전환")
        style = STYLE_POOL[0]
        html = render_transition(content, style, "#3498db")
        assert "text-shadow" in html


class TestCtaCard:
    def test_generates_html(self) -> None:
        content = CardContent(
            card_type="cta",
            title="지금 바로 상담받아 보세요",
            body_text="전문 상담이 기다립니다.",
        )
        style = STYLE_POOL[0]
        profile = _make_profile()
        html = render_cta(content, style, "#3498db", profile)
        assert "max-width:720px" in html
        assert "클리어스킨" in html

    def test_includes_phone(self) -> None:
        content = CardContent(card_type="cta", title="상담")
        style = STYLE_POOL[0]
        profile = _make_profile()
        html = render_cta(content, style, "#3498db", profile)
        assert "02-1234-5678" in html

    def test_dark_has_text_shadow(self) -> None:
        content = CardContent(card_type="cta", title="상담")
        style = STYLE_POOL[0]
        profile = _make_profile()
        html = render_cta(content, style, "#3498db", profile)
        assert "text-shadow" in html


class TestRenderCardHtml:
    def test_dispatches_intro(self) -> None:
        content = CardContent(card_type="intro", title="테스트")
        profile = _make_profile()
        style = STYLE_POOL[0]  # magazine, label_lang=en
        html = render_card_html(content, style, "#3498db", profile)
        assert "max-width:720px" in html
        assert "ABOUT" in html

    def test_ko_label_style(self) -> None:
        content = CardContent(card_type="intro", title="테스트")
        profile = _make_profile()
        style = STYLE_POOL[1]  # minimal_center, label_lang=ko
        html = render_card_html(content, style, "#3498db", profile)
        assert "max-width:720px" in html
        assert "ABOUT" not in html

    def test_disclaimer_uses_fixed_template(self) -> None:
        content = CardContent(card_type="disclaimer")
        profile = _make_profile()
        style = STYLE_POOL[0]
        html = render_card_html(content, style, "#3498db", profile)
        assert "DISCLAIMER" in html
        assert "전문의와 상담" in html

    def test_card_index_affects_accent_line(self) -> None:
        content = CardContent(card_type="intro", title="테스트")
        profile = _make_profile()
        style = STYLE_POOL[0]
        html0 = render_card_html(
            content,
            style,
            "#3498db",
            profile,
            card_index=0,
            total_cards=3,
        )
        html2 = render_card_html(
            content,
            style,
            "#3498db",
            profile,
            card_index=2,
            total_cards=3,
        )
        assert "max-width:720px" in html0
        assert "max-width:720px" in html2
