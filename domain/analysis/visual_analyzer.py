"""비주얼 분석. DOM 파싱(정량) + VLM 인터페이스(정성).

DOM에서 색상, 레이아웃, 이미지 메타를 추출한다.
VLM은 인터페이스만 정의하고 추후 연결한다.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from domain.analysis.model import VisualAnalysis

logger = logging.getLogger(__name__)


def analyze_visual_dom(html: str) -> dict:
    """HTML에서 비주얼 요소를 DOM 파싱으로 추출한다.

    Returns:
        {colors, layout, images} dict
    """
    soup = BeautifulSoup(html, "lxml")

    colors = _extract_colors(soup)
    layout = _extract_layout(soup)
    images = _extract_image_meta(soup)

    return {"colors": colors, "layout": layout, "images": images}


def analyze_visual_vlm(screenshot_path: Path, html: str) -> dict:
    """VLM으로 스크린샷을 분석한다.

    현재는 스텁 구현. 추후 실제 VLM API 연결.
    """
    if not screenshot_path.exists():
        logger.warning("스크린샷 없음, VLM 분석 스킵: %s", screenshot_path)
        return {}

    # TODO: VLM API 연결 시 아래 주석 해제
    # from domain.common import llm_client
    # response = llm_client.analyze_image(
    #     screenshot_path,
    #     prompt="이 블로그 페이지를 분석하세요...",
    #     system="...",
    # )

    logger.info("VLM 분석 스킵 (인터페이스만 구현): %s", screenshot_path)
    return {
        "mood": "",
        "layout_pattern": "",
        "image_styles": [],
        "industry_trend": "",
    }


def aggregate_visual(dom_results: list[dict], vlm_results: list[dict]) -> VisualAnalysis:
    """N개 포스트의 비주얼 분석 결과를 집계한다."""
    all_colors: list[str] = []
    all_bg_colors: list[str] = []
    all_font_colors: list[str] = []
    layout_types: list[str] = []
    total_images = 0

    for dom in dom_results:
        colors = dom.get("colors", {})
        all_colors.extend(colors.get("all_colors", []))
        all_bg_colors.extend(colors.get("background_colors", []))
        all_font_colors.extend(colors.get("font_colors", []))

        layout = dom.get("layout", {})
        layout_types.append(layout.get("type", "mixed"))
        total_images += dom.get("images", {}).get("count", 0)

    n = len(dom_results) or 1

    # 상위 5개 색상
    color_freq = Counter(all_colors)
    dominant = [c for c, _ in color_freq.most_common(5)]

    # 레이아웃 최빈값
    layout_freq = Counter(layout_types)
    top_layout = layout_freq.most_common(1)[0][0] if layout_freq else "mixed"

    # VLM 결과 (현재 스텁)
    mood = ""
    industry = ""
    for vlm in vlm_results:
        if vlm.get("mood"):
            mood = vlm["mood"]
        if vlm.get("industry_trend"):
            industry = vlm["industry_trend"]

    return VisualAnalysis(
        dominant_palette=dominant,
        background_colors=list(set(all_bg_colors))[:5],
        font_colors=list(set(all_font_colors))[:5],
        mood=mood,
        layout_pattern=top_layout,
        avg_image_count=round(total_images / n, 1),
        industry_trend=industry,
    )


def _extract_colors(soup: BeautifulSoup) -> dict:
    """인라인 스타일에서 색상을 추출한다."""
    hex_pattern = re.compile(r"#([0-9a-fA-F]{3,8})")
    rgb_pattern = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")

    all_colors: list[str] = []
    bg_colors: list[str] = []
    font_colors: list[str] = []

    for tag in soup.find_all(style=True):
        style = tag.get("style", "")

        # hex 색상
        for match in hex_pattern.finditer(style):
            color = f"#{match.group(1).lower()}"
            all_colors.append(color)

        # rgb 색상 → hex 변환
        for match in rgb_pattern.finditer(style):
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            color = f"#{r:02x}{g:02x}{b:02x}"
            all_colors.append(color)

        # 배경색/글자색 분리
        if "background" in style:
            for m in hex_pattern.finditer(style):
                bg_colors.append(f"#{m.group(1).lower()}")
        if "color" in style and "background" not in style.split("color")[0][-5:]:
            for m in hex_pattern.finditer(style):
                font_colors.append(f"#{m.group(1).lower()}")

    return {
        "all_colors": all_colors,
        "background_colors": bg_colors,
        "font_colors": font_colors,
    }


def _extract_layout(soup: BeautifulSoup) -> dict:
    """레이아웃 구조를 분석한다."""
    sections = soup.find_all("div", class_=re.compile(r"se-section"))
    images = soup.find_all("img")
    text_blocks = soup.find_all(["p", "h2", "h3"])

    img_count = len(images)
    text_count = len(text_blocks)
    total = img_count + text_count

    if total == 0:
        layout_type = "empty"
    elif img_count > text_count:
        layout_type = "image_heavy"
    elif text_count > img_count * 3:
        layout_type = "text_heavy"
    else:
        layout_type = "mixed"

    return {
        "type": layout_type,
        "section_count": len(sections),
        "image_count": img_count,
        "text_block_count": text_count,
    }


def _extract_image_meta(soup: BeautifulSoup) -> dict:
    """이미지 메타데이터를 추출한다."""
    images = soup.find_all("img")

    return {
        "count": len(images),
        "srcs": [img.get("src", "") for img in images[:20]],
        "alts": [img.get("alt", "") for img in images[:20]],
    }
