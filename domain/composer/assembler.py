"""최종 콘텐츠 조합. 브랜드 이미지 섹션 + SEO 원고 섹션."""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from domain.common.config import settings
from domain.composer.model import ComposedOutput, RenderedImage
from domain.composer.naver_formatter import (
    FormatterTheme,
    markdown_to_naver_html,
)
from domain.composer.renderer import render_batch_sync
from domain.generation.model import GeneratedContent

logger = logging.getLogger(__name__)


def assemble(content: GeneratedContent) -> ComposedOutput:
    """생성된 콘텐츠를 최종 출력물로 조합한다.

    구조:
      [브랜드 이미지 섹션] — 카드 PNG 순서대로 나열
      [SEO 원고 섹션] — 네이버 포맷터 HTML + AI 이미지
    """
    # 출력 디렉터리
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    safe_keyword = content.keyword.replace(" ", "_")[:30]
    output_dir = settings.output_dir / f"{safe_keyword}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # === 1. 브랜드 카드 → PNG 배치 렌더링 ===
    render_cards = [c for c in content.brand_cards if c.card_type != "disclaimer"]
    render_jobs: list[tuple[str, Path]] = []
    for i, card in enumerate(render_cards):
        png_path = images_dir / f"brand_{i:02d}_{card.card_type}.png"
        render_jobs.append((card.html, png_path))

    logger.info("브랜드 카드 렌더링 중 (%d장)...", len(render_jobs))
    results = render_batch_sync(render_jobs)

    # base64 인코딩 + RenderedImage
    images: list[RenderedImage] = []
    brand_b64_list: list[tuple[str, str]] = []  # (card_type, b64)

    for card, (_, png_path), success in zip(render_cards, render_jobs, results):
        b64 = ""
        if success and png_path.exists():
            b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")

        images.append(
            RenderedImage(
                image_type=card.card_type,
                source_html=card.html,
                output_path=str(png_path),
                base64_data=b64,
                success=success,
                error="" if success else "렌더링 실패",
            ),
        )
        if b64:
            brand_b64_list.append((card.card_type, b64))

    # === 2. 브랜드 이미지 섹션 HTML ===
    brand_html = _build_brand_section(brand_b64_list)

    # === 3. SEO 원고 → 네이버 HTML ===
    formatter_theme = _extract_formatter_theme(content)
    seo_html = markdown_to_naver_html(content.seo_text, theme=formatter_theme)

    # === 4. IMAGE 마커 → AI 이미지 교체 ===
    seo_html = _replace_image_markers(seo_html, content, images_dir)

    # === 5. 합체: 브랜드 + SEO ===
    body_html = brand_html + "\n" + seo_html

    # === 6. 파일 저장 ===
    final_html = _build_full_html(body_html)
    final_path = output_dir / "final.html"
    final_path.write_text(final_html, encoding="utf-8")

    paste_path = output_dir / "paste_ready.html"
    paste_path.write_text(body_html, encoding="utf-8")

    summary = {
        "keyword": content.keyword,
        "title": content.title,
        "variation": content.variation_config.model_dump(),
        "compliance_status": content.compliance_status,
        "brand_card_count": len(brand_b64_list),
        "ai_image_count": len(content.generated_images),
        "card_types": [c.card_type for c in content.brand_cards],
        "created_at": timestamp,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("최종 조합 완료: %s", output_dir)

    return ComposedOutput(
        keyword=content.keyword,
        output_dir=str(output_dir),
        final_html_path=str(final_path),
        paste_ready_path=str(paste_path),
        images=images,
        summary=summary,
    )


def _build_brand_section(brand_b64_list: list[tuple[str, str]]) -> str:
    """브랜드 카드 이미지를 순서대로 나열한 HTML 섹션."""
    if not brand_b64_list:
        return ""

    cards_html = ""
    for card_type, b64 in brand_b64_list:
        cards_html += (
            f'<div style="text-align:center;margin:0;">'
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="{card_type}" style="max-width:100%;display:block;"></div>'
        )

    return cards_html


def _replace_image_markers(
    html: str,
    content: GeneratedContent,
    images_dir: Path,
) -> str:
    """<!-- IMAGE:N --> 마커를 AI 생성 이미지로 교체한다."""
    gen_images = content.generated_images

    def _img_replacer(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        desc = match.group(2) or ""

        if idx < len(gen_images) and gen_images[idx].success:
            img = gen_images[idx]
            img_path = images_dir / f"ai_{idx:02d}.png"
            img_path.write_bytes(img.image_bytes)

            b64 = base64.b64encode(img.image_bytes).decode("ascii")
            return (
                f'<div style="text-align:center;margin:32px 0;">'
                f'<img src="data:image/png;base64,{b64}" '
                f'alt="{desc}" style="max-width:100%;'
                f"border-radius:12px;"
                f'box-shadow:0 4px 20px rgba(0,0,0,0.08);"></div>'
            )

        return (
            f'<div style="border:2px dashed #ddd;padding:48px;'
            f"border-radius:12px;text-align:center;color:#aaa;"
            f'margin:32px 0;font-size:14px;">{desc}</div>'
        )

    return re.sub(
        r"<!--\s*IMAGE:(\d+)\s*desc=([^>]*?)\s*-->",
        _img_replacer,
        html,
    )


def _extract_formatter_theme(content: GeneratedContent) -> FormatterTheme | None:
    """variation_config에서 테마 토큰을 추출한다."""
    theme_name = content.variation_config.newsletter_theme
    if not theme_name:
        return None

    try:
        from domain.generation.newsletter_theme import get_theme

        theme = get_theme(theme_name)
        if not theme:
            return None
        return FormatterTheme(
            bg_primary=theme.bg_primary,
            bg_section=theme.bg_section,
            text_primary=theme.text_primary,
            text_heading=theme.text_heading,
            text_muted=theme.text_muted,
            accent=theme.accent,
            font_heading=theme.font_heading,
            font_body=theme.font_body,
            heading_weight=theme.heading_weight,
            heading_size=theme.heading_size,
            subheading_size=theme.subheading_size,
            highlight_bg=theme.highlight_bg,
            quote_bg=theme.quote_bg,
            divider_style=theme.divider_style,
            border_radius=theme.border_radius,
        )
    except ImportError:
        logger.warning("뉴스레터 테마 로드 실패, 기본 테마 사용")
        return None


def _build_full_html(body_html: str) -> str:
    """전체 HTML 문서."""
    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard\
@v1.3.9/dist/web/static/pretendard.min.css" rel="stylesheet">
  <style>
    body {{ margin: 0; padding: 0; background: #fff; }}
    article {{ max-width: 720px; margin: 0 auto; padding: 0 0 60px; }}
  </style>
</head>
<body>
<article>
  {body_html}
</article>
</body>
</html>"""
