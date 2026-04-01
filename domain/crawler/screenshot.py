"""Playwright로 블로그 풀페이지 스크린샷을 캡처한다."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 네이버 블로그 모바일 기준 뷰포트
VIEWPORT_WIDTH = 680
SCREENSHOT_TIMEOUT = 30_000  # 30초


async def capture_screenshot(
    url: str,
    output_path: Path,
    *,
    viewport_width: int = VIEWPORT_WIDTH,
    timeout: int = SCREENSHOT_TIMEOUT,
) -> bool:
    """URL의 풀페이지 스크린샷을 캡처한다.

    Args:
        url: 캡처할 URL
        output_path: PNG 저장 경로
        viewport_width: 뷰포트 너비 (기본 680px)
        timeout: 타임아웃 (밀리초)

    Returns:
        성공 여부
    """
    from playwright.async_api import async_playwright

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": 800},
                device_scale_factor=2,
            )
            page = await context.new_page()

            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(2000)  # 이미지 로딩 대기

            await page.screenshot(path=str(output_path), full_page=True)
            await browser.close()

        logger.info("스크린샷 저장: %s", output_path)
        return True

    except Exception as e:
        logger.error("스크린샷 실패 (%s): %s", url, e)
        return False


def capture_screenshot_sync(
    url: str,
    output_path: Path,
    *,
    viewport_width: int = VIEWPORT_WIDTH,
    timeout: int = SCREENSHOT_TIMEOUT,
) -> bool:
    """capture_screenshot의 동기 래퍼."""
    import asyncio

    return asyncio.run(
        capture_screenshot(url, output_path, viewport_width=viewport_width, timeout=timeout)
    )
