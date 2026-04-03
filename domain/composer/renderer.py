"""Playwright HTML → PNG 렌더링. 디자인 카드를 이미지로 변환한다."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def render_html_to_png(
    html: str,
    output_path: Path,
    *,
    width: int = 720,
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
    width: int = 720,
    scale: int = 2,
) -> bool:
    """render_html_to_png의 동기 래퍼."""
    import asyncio

    return asyncio.run(render_html_to_png(html, output_path, width=width, scale=scale))


async def render_batch(
    html_list: list[tuple[str, Path]],
    *,
    width: int = 720,
    scale: int = 2,
) -> list[bool]:
    """여러 HTML을 단일 브라우저로 배치 렌더링한다.

    Args:
        html_list: (html, output_path) 튜플 리스트
        width: 뷰포트 너비
        scale: 디바이스 스케일 팩터

    Returns:
        각 항목의 성공 여부 리스트
    """
    from playwright.async_api import async_playwright

    if not html_list:
        return []

    results: list[bool] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": width, "height": 400},
                device_scale_factor=scale,
            )
            page = await context.new_page()

            for html, output_path in html_list:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                full_html = (
                    "<!DOCTYPE html><html><head>"
                    '<meta charset="utf-8">'
                    "<style>body{margin:0;padding:0;}</style>"
                    f"</head><body>{html}</body></html>"
                )
                try:
                    await page.set_content(full_html, wait_until="networkidle")
                    element = await page.query_selector("body > div")
                    if element:
                        await element.screenshot(path=str(output_path))
                    else:
                        await page.screenshot(
                            path=str(output_path),
                            full_page=True,
                        )
                    results.append(True)
                    logger.info("PNG 렌더링 완료: %s", output_path)
                except Exception as e:
                    logger.error("PNG 렌더링 실패 (%s): %s", output_path, e)
                    results.append(False)

            await browser.close()

    except Exception as e:
        logger.error("배치 렌더링 브라우저 실패: %s", e)
        results.extend([False] * (len(html_list) - len(results)))

    return results


def render_batch_sync(
    html_list: list[tuple[str, Path]],
    *,
    width: int = 720,
    scale: int = 2,
) -> list[bool]:
    """render_batch의 동기 래퍼."""
    import asyncio

    return asyncio.run(render_batch(html_list, width=width, scale=scale))
