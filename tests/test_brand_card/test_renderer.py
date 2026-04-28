"""renderer — Jinja2 렌더링 + Playwright 호출 흐름 단위 테스트.

Playwright 자체는 mock — 실제 Chromium 호출은 Phase 2 통합 테스트에서.
HTML/CSS 변환 + 폰트 placeholder 치환 + overflow 검출 분기 검증.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from domain.brand_card.model import CardBlock, TextOverflowError
from domain.brand_card.renderer import (
    RenderContext,
    _prepare_html,
    cleanup_work_dir,
    render_card_to_png,
)
from domain.brand_card.template_registry import get_template


def _block(card_type: str = "hero", headline: str = "체질부터 보는 관리") -> CardBlock:
    return CardBlock(
        card_type=card_type,
        headline=headline,
        subcopy="맞춤 처방",
        bullets=["체질 분석", "생활 패턴", "한약 처방"],
        recommended_position="after_intro",
    )


class TestPrepareHtml:
    def test_html_and_css_written(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(), brand_name="대구한의원")
        html_path = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path)
        assert html_path.exists()
        css_path = tmp_path / "style.css"
        assert css_path.exists()

    def test_pretendard_url_replaced_in_css(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(), brand_name="대구한의원")
        _prepare_html(meta=meta, context=ctx, work_dir=tmp_path)
        css_text = (tmp_path / "style.css").read_text(encoding="utf-8")
        assert "PRETENDARD_URL" not in css_text
        assert "file://" in css_text or "Pretendard" in css_text

    def test_html_includes_brand_name_and_headline(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(headline="신뢰의 시작"), brand_name="대구한의원")
        html_path = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "대구한의원" in html
        assert "신뢰의 시작" in html

    def test_image_url_embedded_when_provided(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(
            block=_block(),
            brand_name="대구한의원",
            image_url="file:///path/to/photo.jpg",
        )
        html = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path).read_text(encoding="utf-8")
        assert "file:///path/to/photo.jpg" in html

    def test_image_placeholder_when_no_url(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(), brand_name="대구한의원")
        html = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path).read_text(encoding="utf-8")
        assert "card__image-placeholder" in html

    def test_card_type_class_applied(self, tmp_path: Path) -> None:
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(card_type="problem"), brand_name="브랜드")
        html = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path).read_text(encoding="utf-8")
        assert "card--problem" in html

    def test_data_text_block_attributes_present(self, tmp_path: Path) -> None:
        """렌더러의 overflow 검출용 data-text-block 속성이 HTML 에 있어야 한다."""
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=_block(), brand_name="브랜드")
        html = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path).read_text(encoding="utf-8")
        assert 'data-text-block="headline"' in html
        assert 'data-text-block="brand"' in html

    def test_subcopy_omitted_when_none(self, tmp_path: Path) -> None:
        block = CardBlock(
            card_type="hero",
            headline="제목",
            subcopy=None,
            bullets=[],
            recommended_position="after_intro",
        )
        meta = get_template("clinic_trust")
        ctx = RenderContext(block=block, brand_name="브랜드")
        html = _prepare_html(meta=meta, context=ctx, work_dir=tmp_path).read_text(encoding="utf-8")
        assert "card__subcopy" not in html


class TestRenderCardToPng:
    """Playwright mock — 호출 흐름 + overflow 분기."""

    def _patch_playwright(self, overflows: list[dict] | None = None) -> MagicMock:
        """sync_playwright().__enter__() 가 반환할 객체 mock."""
        page = MagicMock()
        page.evaluate.return_value = overflows or []

        context_mock = MagicMock()
        context_mock.new_page.return_value = page

        browser = MagicMock()
        browser.new_context.return_value = context_mock

        p = MagicMock()
        p.chromium.launch.return_value = browser

        sync_pw = MagicMock()
        sync_pw.__enter__.return_value = p
        sync_pw.__exit__.return_value = False

        return MagicMock(return_value=sync_pw)

    def test_overflow_detected_raises(self, tmp_path: Path) -> None:
        sync_pw_factory = self._patch_playwright(
            overflows=[{"block": "headline", "scrollW": 1200, "clientW": 1080}]
        )
        with patch("playwright.sync_api.sync_playwright", sync_pw_factory):
            ctx = RenderContext(block=_block(), brand_name="브랜드")
            with pytest.raises(TextOverflowError, match="text overflow"):
                render_card_to_png(
                    template_id="clinic_trust",
                    context=ctx,
                    output_path=tmp_path / "card.png",
                    work_dir=tmp_path / "work",
                )

    def test_no_overflow_screenshots_taken(self, tmp_path: Path) -> None:
        sync_pw_factory = self._patch_playwright(overflows=[])

        # Playwright 의 page.screenshot 이 실제 파일을 만들지 않으므로 호출 검증
        with patch("playwright.sync_api.sync_playwright", sync_pw_factory) as sp:
            ctx = RenderContext(block=_block(), brand_name="브랜드")
            output = tmp_path / "card.png"
            render_card_to_png(
                template_id="clinic_trust",
                context=ctx,
                output_path=output,
                work_dir=tmp_path / "work",
            )
            # Playwright 호출 발생 확인
            sp.assert_called_once()


class TestCleanupWorkDir:
    def test_removes_existing_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "work"
        target.mkdir()
        (target / "trash.txt").write_text("x")
        cleanup_work_dir(target)
        assert not target.exists()

    def test_silent_on_nonexistent(self, tmp_path: Path) -> None:
        cleanup_work_dir(tmp_path / "nonexistent")  # no raise
