"""L1 구조 분석. HTML 파싱 기반, LLM 불필요.

글자수, 문단수, 소제목, 이미지 위치, CTA, 네이버 특화 요소를 추출한다.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from domain.analysis.model import L1Analysis, SectionInfo

logger = logging.getLogger(__name__)


def analyze_structure(html: str) -> SectionInfo:
    """단일 포스트 HTML의 구조를 분석한다.

    Args:
        html: 블로그 본문 HTML

    Returns:
        SectionInfo
    """
    soup = BeautifulSoup(html, "lxml")

    # 텍스트 추출
    text = soup.get_text(separator="\n", strip=True)
    paragraphs = [p for p in text.split("\n") if p.strip()]

    # 소제목 추출 (h2, h3, strong 기반)
    subtitles = _extract_subtitles(soup)

    # 이미지 위치
    image_positions = _extract_image_positions(soup, len(paragraphs))

    # CTA
    cta_positions, cta_texts = _extract_cta(soup, paragraphs)

    # 네이버 특화 요소
    naver_elements = _count_naver_elements(soup)

    # 섹션 비율 계산
    section_ratio = _calc_section_ratio(paragraphs, subtitles, cta_positions)

    return SectionInfo(
        total_chars=len(text),
        total_paragraphs=len(paragraphs),
        subtitle_count=len(subtitles),
        subtitles=subtitles,
        section_ratio=section_ratio,
        image_count=len(image_positions),
        image_positions=image_positions,
        cta_positions=cta_positions,
        cta_texts=cta_texts,
        naver_elements=naver_elements,
    )


def aggregate_l1(sections: list[SectionInfo]) -> L1Analysis:
    """N개 포스트의 L1 분석 결과를 집계한다."""
    n = len(sections)
    if n == 0:
        return L1Analysis()

    avg_chars = sum(s.total_chars for s in sections) / n
    avg_paras = sum(s.total_paragraphs for s in sections) / n
    avg_subs = sum(s.subtitle_count for s in sections) / n
    avg_imgs = sum(s.image_count for s in sections) / n

    # CTA 텍스트 빈도
    cta_counter: dict[str, int] = {}
    for s in sections:
        for t in s.cta_texts:
            cta_counter[t] = cta_counter.get(t, 0) + 1
    top_cta = sorted(cta_counter, key=cta_counter.get, reverse=True)[:5]  # type: ignore[arg-type]

    # 네이버 요소 평균
    naver_avg: dict[str, float] = {}
    for key in ("map", "divider", "blockquote"):
        naver_avg[key] = sum(s.naver_elements.get(key, 0) for s in sections) / n

    return L1Analysis(
        post_count=n,
        avg_char_count=round(avg_chars),
        avg_paragraph_count=round(avg_paras, 1),
        avg_subtitle_count=round(avg_subs, 1),
        avg_image_count=round(avg_imgs, 1),
        cta_patterns=top_cta,
        naver_elements=naver_avg,
        per_post=sections,
    )


def _extract_subtitles(soup: BeautifulSoup) -> list[str]:
    """소제목을 추출한다."""
    subtitles: list[str] = []

    # h2, h3
    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) < 100:
            subtitles.append(text)

    # strong 기반 소제목 (네이버 블로그에서 흔함)
    if not subtitles:
        for strong in soup.find_all("strong"):
            text = strong.get_text(strip=True)
            parent = strong.parent
            if (
                text
                and 5 < len(text) < 50
                and isinstance(parent, Tag)
                and parent.name in ("p", "div", "span")
            ):
                # 단독 strong (문단의 유일한 내용)
                parent_text = parent.get_text(strip=True)
                if parent_text == text:
                    subtitles.append(text)

    return subtitles


def _extract_image_positions(soup: BeautifulSoup, total_paragraphs: int) -> list[int]:
    """이미지 삽입 위치를 문단 번호로 반환한다."""
    positions: list[int] = []
    all_elements = soup.find_all(["p", "div", "img"])

    para_index = 0
    for elem in all_elements:
        if elem.name == "img":
            positions.append(para_index)
        elif elem.name in ("p", "div") and elem.get_text(strip=True):
            para_index += 1

    return positions


def _extract_cta(soup: BeautifulSoup, paragraphs: list[str]) -> tuple[list[int], list[str]]:
    """CTA 위치와 텍스트를 추출한다."""
    cta_keywords = re.compile(r"(전화|상담|예약|카카오톡|문의|방문|클릭|신청)", re.IGNORECASE)

    positions: list[int] = []
    texts: list[str] = []

    for i, para in enumerate(paragraphs):
        if cta_keywords.search(para):
            positions.append(i)
            texts.append(para[:50])

    return positions, texts


def _count_naver_elements(soup: BeautifulSoup) -> dict[str, int]:
    """네이버 블로그 특화 요소를 카운트한다."""
    return {
        "map": len(soup.find_all("div", class_=re.compile(r"se-map|naver-map"))),
        "divider": len(soup.find_all("hr"))
        + len(soup.find_all("div", class_=re.compile(r"se-hr"))),
        "blockquote": len(soup.find_all("blockquote"))
        + len(soup.find_all("div", class_=re.compile(r"se-quote"))),
    }


def _calc_section_ratio(
    paragraphs: list[str],
    subtitles: list[str],
    cta_positions: list[int],
) -> str:
    """도입-본론-결론 비율을 계산한다."""
    total = len(paragraphs)
    if total == 0:
        return "0-0-0"

    # 도입부: 첫 번째 소제목 이전
    first_subtitle_pos = total // 5  # 기본값: 상위 20%
    if subtitles:
        # 소제목이 있으면 첫 소제목까지가 도입부
        for i, para in enumerate(paragraphs):
            if subtitles[0] in para:
                first_subtitle_pos = i
                break

    # 결론: 마지막 CTA부터
    conclusion_start = total - (total // 5)  # 기본값: 하위 20%
    if cta_positions:
        conclusion_start = min(cta_positions[-1], total - 1)

    intro_ratio = round(first_subtitle_pos / total * 100)
    conclusion_ratio = round((total - conclusion_start) / total * 100)
    body_ratio = 100 - intro_ratio - conclusion_ratio

    return f"도입{intro_ratio}-본론{body_ratio}-결론{conclusion_ratio}"
