"""최종 콘텐츠 조합. 텍스트 + 디자인 카드 + 이미지 → HTML + PNG."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from domain.common.config import settings
from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.composer.model import ComposedOutput, RenderedImage
from domain.composer.naver_formatter import insert_disclaimer, markdown_to_naver_html
from domain.composer.renderer import render_html_to_png_sync
from domain.generation.model import GeneratedContent

logger = logging.getLogger(__name__)


def assemble(content: GeneratedContent) -> ComposedOutput:
    """생성된 콘텐츠를 최종 출력물로 조합한다.

    1. 마크다운 → 네이버 에디터 HTML 변환
    2. 디자인 카드 HTML → PNG 렌더링
    3. Disclaimer 삽입
    4. output/ 디렉터리에 파일 저장

    Args:
        content: 생성된 콘텐츠

    Returns:
        ComposedOutput
    """
    # 출력 디렉터리
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    safe_keyword = content.keyword.replace(" ", "_")[:30]
    output_dir = settings.output_dir / f"{safe_keyword}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    images: list[RenderedImage] = []

    # 1. 디자인 카드 렌더링
    for card in content.design_cards:
        png_path = images_dir / f"{card.card_type}.png"
        success = render_html_to_png_sync(card.html, png_path)
        images.append(
            RenderedImage(
                image_type=card.card_type,
                source_html=card.html,
                output_path=str(png_path),
                success=success,
                error="" if success else "렌더링 실패",
            )
        )

    # 2. 마크다운 → HTML 변환
    naver_html = markdown_to_naver_html(content.seo_text)

    # 3. Disclaimer 삽입
    naver_html = insert_disclaimer(naver_html, DISCLAIMER_TEMPLATE)

    # 4. 최종 HTML 저장
    final_html = _build_full_html(naver_html, images)
    final_path = output_dir / "final.html"
    final_path.write_text(final_html, encoding="utf-8")

    # 5. 붙여넣기용 HTML
    paste_path = output_dir / "paste_ready.html"
    paste_path.write_text(naver_html, encoding="utf-8")

    # 6. 요약 메타데이터
    summary = {
        "keyword": content.keyword,
        "title": content.title,
        "variation": content.variation_config.model_dump(),
        "compliance_status": content.compliance_status,
        "image_count": len(images),
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


def _build_full_html(body_html: str, images: list[RenderedImage]) -> str:
    """이미지 참조를 포함한 전체 HTML을 생성한다."""
    # 헤더 이미지를 본문 앞에 삽입
    header_imgs = [i for i in images if i.image_type == "header" and i.success]
    cta_imgs = [i for i in images if i.image_type == "cta" and i.success]

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8"></head><body>',
    ]

    for img in header_imgs:
        parts.append(f'<img src="{img.output_path}" style="width:680px;display:block;">')

    parts.append(body_html)

    for img in cta_imgs:
        parts.append(f'<img src="{img.output_path}" style="width:680px;display:block;">')

    parts.append("</body></html>")
    return "\n".join(parts)
