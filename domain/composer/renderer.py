"""Playwright HTML → PNG 렌더링. 디자인 카드를 이미지로 변환한다."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def render_html_to_png(
    html: str,
    output_path: Path,
    *,
    width: int = 680,
    scale: int = 2,
) -> bool:
    """HTML 문자열을 PNG로 렌더링한다.

    Args:
        html: 렌더링할 HTML
        output_path: PNG 저장 경로
        width: 뷰포트 너비
        scale: 디바이스 스케일 팩터 (레티나 대응)

    Returns:
        성공 여부
    """
    from playwright.async_api import async_playwright

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 자체 포함 HTML 생성
    full_html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>body{{margin:0;padding:0;}}</style></head>
<body>{html}</body>
</html>"""

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": width, "height": 400},
                device_scale_factor=scale,
            )
            page = await context.new_page()
            await page.set_content(full_html, wait_until="networkidle")

            # 콘텐츠 크기에 맞춰 캡처
            element = await page.query_selector("body > div")
            if element:
                await element.screenshot(path=str(output_path))
            else:
                await page.screenshot(path=str(output_path), full_page=True)

            await browser.close()

        logger.info("PNG 렌더링 완료: %s", output_path)
        return True

    except Exception as e:
        logger.error("PNG 렌더링 실패: %s", e)
        return False


def render_html_to_png_sync(
    html: str,
    output_path: Path,
    *,
    width: int = 680,
    scale: int = 2,
) -> bool:
    """render_html_to_png의 동기 래퍼."""
    import asyncio

    return asyncio.run(render_html_to_png(html, output_path, width=width, scale=scale))
