"""최종 콘텐츠 조합. 리치 HTML + 카드 PNG → 마커 기반 삽입."""

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

    1. 브랜디드 카드 HTML -> PNG 배치 렌더링
    2. PNG -> base64 인코딩
    3. 마크다운 -> 네이버 에디터 리치 HTML 변환
    4. <!-- CARD:type --> 마커를 base64 이미지로 교체
    5. Disclaimer HTML 텍스트 삽입 (의료 업종)
    6. output/ 디렉터리에 파일 저장
    """
    # 출력 디렉터리
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    safe_keyword = content.keyword.replace(" ", "_")[:30]
    output_dir = settings.output_dir / f"{safe_keyword}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # 1. 배치 렌더링 준비 (disclaimer 제외 — HTML 텍스트로 처리)
    render_cards = [c for c in content.design_cards if c.card_type != "disclaimer"]
    render_jobs: list[tuple[str, Path]] = []
    for i, card in enumerate(render_cards):
        png_path = images_dir / f"{i:02d}_{card.card_type}.png"
        render_jobs.append((card.html, png_path))

    # 2. 배치 렌더링 (브라우저 1회)
    logger.info("브랜디드 카드 렌더링 중 (%d장)...", len(render_jobs))
    results = render_batch_sync(render_jobs)

    # 3. base64 인코딩 + RenderedImage 생성
    images: list[RenderedImage] = []
    card_b64_map: dict[str, str] = {}
    for i, (card, (html, png_path), success) in enumerate(
        zip(render_cards, render_jobs, results),
    ):
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
            card_b64_map[card.card_type] = b64

    # 4. 마크다운 -> 리치 HTML 변환 (테마 적용)
    formatter_theme = _extract_formatter_theme(content)
    naver_html = markdown_to_naver_html(content.seo_text, theme=formatter_theme)

    # 5. <!-- CARD:type --> 마커를 base64 이미지로 교체
    naver_html = _replace_card_markers(naver_html, card_b64_map)

    # 6. Disclaimer — SEO 텍스트에 이미 포함되므로 별도 삽입하지 않음

    # 7. 최종 HTML 빌드
    final_html = _build_full_html(naver_html)
    final_path = output_dir / "final.html"
    final_path.write_text(final_html, encoding="utf-8")

    # 8. 붙여넣기용 HTML
    paste_path = output_dir / "paste_ready.html"
    paste_path.write_text(naver_html, encoding="utf-8")

    # 9. 요약 메타데이터
    summary = {
        "keyword": content.keyword,
        "title": content.title,
        "variation": content.variation_config.model_dump(),
        "compliance_status": content.compliance_status,
        "image_count": len(images),
        "card_types": [c.card_type for c in content.design_cards],
        "card_positions": content.card_positions,
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


def _replace_card_markers(
    html: str,
    card_b64_map: dict[str, str],
) -> str:
    """<!-- CARD:type --> 마커를 base64 이미지로 교체한다."""

    def _replacer(match: re.Match[str]) -> str:
        card_type = match.group(1)
        b64 = card_b64_map.get(card_type, "")
        if not b64:
            return ""
        return (
            f'<div style="text-align:center;margin:40px 0;">'
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="{card_type}" style="max-width:100%;'
            f"border-radius:12px;"
            f'box-shadow:0 4px 20px rgba(0,0,0,0.08);"></div>'
        )

    return re.sub(r"<!--\s*CARD:(\w+)\s*-->", _replacer, html)


def _extract_formatter_theme(content: GeneratedContent) -> FormatterTheme | None:
    """GeneratedContent의 variation_config에서 테마 토큰을 추출한다."""
    theme_name = content.variation_config.newsletter_theme
    if not theme_name:
        return None

    # generation 도메인의 테마 데이터를 dict로 전달받아 FormatterTheme 생성
    # 도메인 간 직접 import 대신 JSON-serializable 데이터로 전달
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
    """리치 HTML을 감싸는 전체 HTML 문서."""
    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard\
@v1.3.9/dist/web/static/pretendard.min.css" rel="stylesheet">
  <style>
    body {{ margin: 0; padding: 0; background: #fff; }}
    article {{ max-width: 720px; margin: 0 auto; padding: 20px 24px 60px; }}
  </style>
</head>
<body>
<article>
  {body_html}
</article>
</body>
</html>"""
