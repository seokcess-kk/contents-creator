"""일반 웹페이지 크롤링. 클라이언트 프로필 추출에도 사용한다."""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from domain.crawler.model import PageData

logger = logging.getLogger(__name__)

# 프로필 추출용 페이지 탐색 패턴
ABOUT_PATTERNS = re.compile(
    r"(about|introduce|intro|소개|인사|원장|대표|의료진|doctor|staff)",
    re.IGNORECASE,
)
SERVICE_PATTERNS = re.compile(
    r"(service|treatment|시술|진료|서비스|프로그램|menu|클리닉|clinic)",
    re.IGNORECASE,
)


def scrape_homepage(url: str, max_pages: int = 10) -> list[PageData]:
    """홈페이지의 주요 페이지를 크롤링한다.

    메인 → 소개 → 서비스 페이지 순으로 탐색하여 최대 max_pages개 수집.

    Args:
        url: 홈페이지 메인 URL
        max_pages: 최대 수집 페이지 수

    Returns:
        PageData 리스트
    """
    results: list[PageData] = []
    visited: set[str] = set()
    base_domain = urlparse(url).netloc

    # 1. 메인 페이지
    main_page = _fetch_page(url)
    results.append(main_page)
    visited.add(url)

    if not main_page.success:
        return results

    # 2. 메인에서 링크 추출 → 소개/서비스 페이지 탐색
    links = _extract_links(main_page.raw_html, url, base_domain)
    prioritized = _prioritize_links(links)

    for link in prioritized:
        if len(results) >= max_pages:
            break
        if link in visited:
            continue
        visited.add(link)

        page = _fetch_page(link)
        results.append(page)

    logger.info("홈페이지 크롤링 완료: %d페이지 수집 (%s)", len(results), url)
    return results


def _fetch_page(url: str, max_retries: int = 2) -> PageData:
    """단일 페이지를 가져온다."""
    from scrapling import StealthyFetcher

    fetcher = StealthyFetcher()

    for attempt in range(max_retries + 1):
        try:
            response = fetcher.fetch(url)
            if response.status == 200:
                html = response.html_content
                soup = BeautifulSoup(html, "lxml")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                text = soup.get_text(separator="\n", strip=True)
                return PageData(
                    url=url,
                    title=title,
                    raw_html=html,
                    text_content=text,
                )
            logger.warning("HTTP %d: %s", response.status, url)
        except Exception as e:
            logger.warning("페이지 크롤링 에러: %s (%s)", e, url)

        if attempt < max_retries:
            time.sleep(2)

    return PageData(url=url, success=False, error=f"크롤링 실패 ({max_retries + 1}회 시도)")


def _extract_links(html: str, base_url: str, base_domain: str) -> list[str]:
    """HTML에서 같은 도메인의 링크를 추출한다."""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # 같은 도메인만, fragment/파일 제외
        if parsed.netloc == base_domain and not parsed.path.endswith(
            (".pdf", ".jpg", ".png", ".zip")
        ):
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url not in links:
                links.append(clean_url)

    return links


def _prioritize_links(links: list[str]) -> list[str]:
    """소개/서비스 페이지를 우선 정렬한다."""
    about: list[str] = []
    service: list[str] = []
    others: list[str] = []

    for link in links:
        path = urlparse(link).path
        if ABOUT_PATTERNS.search(path):
            about.append(link)
        elif SERVICE_PATTERNS.search(path):
            service.append(link)
        else:
            others.append(link)

    return about + service + others
