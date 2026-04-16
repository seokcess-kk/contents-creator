"""[1] 네이버 블로그 SERP 수집.

SPEC-SEO-TEXT.md §3 [1] 구현. Bright Data Web Unlocker 로 네이버 블로그
검색 결과 페이지를 fetch 한 뒤 BeautifulSoup 으로 블로그 URL 을 파싱한다.

- 쿼리: `https://search.naver.com/search.naver?ssc=tab.blog.all&query={keyword}`
  (2026-04-16 실측: where=blog 통합 섹션은 6~7개만 노출, ssc=tab.blog.all 블로그
  탭 직접 URL 은 한 페이지에 40개 이상 서버 렌더링)
- 필터: `blog.naver.com` / `m.blog.naver.com` 외 배제, `/clip/` 배제, 광고 배제
- 선착순 10개 선택. 최소 7개 미만이면 InsufficientCollectionError 발생
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup, Tag

from domain.crawler.brightdata_client import BrightDataClient
from domain.crawler.model import (
    MIN_COLLECTED_PAGES,
    InsufficientCollectionError,
    SerpResult,
    SerpResults,
)

logger = logging.getLogger(__name__)

MAX_RESULTS = 10
# 네이버 검색의 "블로그 전용 탭" 은 ssc=tab.blog.all 로 접근한다 (2026-04-16 실측).
# where=blog 통합검색 섹션은 React 버튼으로 6~7개만 노출하지만, ssc=tab.blog.all 은
# 한 페이지에 40개 이상 포스트를 서버 렌더링으로 반환한다.
# SPEC §3 [1] "상위 20개 결과" 요구를 단일 페이지로 충족 가능.
SERP_PAGES_TO_FETCH = 1
SERP_PAGE_SIZE = 30

# 네이버 블로그 일반 포스트 URL 패턴. /clip/ (동영상 클립) 및 유저 홈(숫자 없음) 배제.
# 예: https://blog.naver.com/ssmaa/224246591163
BLOG_POST_URL_RE = re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}$")


def build_serp_url(keyword: str, start: int = 1) -> str:
    """키워드 + 페이지 시작 index → 네이버 블로그 전용 탭 검색 URL.

    `ssc=tab.blog.all` 은 통합검색의 블로그 섹션이 아니라 "블로그 탭" 을 직접
    요청하는 파라미터다. 한 페이지에 40개 이상 서버 렌더링됨.
    `start` 는 1, 11, 21 … 1-index 시작점 (현재는 1페이지면 충분).
    """
    return f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={quote(keyword)}&start={start}"


def collect_serp(keyword: str, client: BrightDataClient) -> SerpResults:
    """네이버 블로그 SERP 를 수집해 SerpResults 로 반환.

    SERP_PAGES_TO_FETCH 페이지를 순차 fetch 하고 중복 URL 을 병합한다.
    수집 수가 MIN_COLLECTED_PAGES 미만이면 InsufficientCollectionError 발생.
    """
    logger.info("serp.collect keyword=%s pages=%s", keyword, SERP_PAGES_TO_FETCH)
    results: list[SerpResult] = []
    seen: set[str] = set()
    for page_idx in range(SERP_PAGES_TO_FETCH):
        start = 1 + page_idx * SERP_PAGE_SIZE
        serp_url = build_serp_url(keyword, start=start)
        html = client.fetch(serp_url)
        for item in _parse_serp_html(html):
            url_str = str(item.url)
            if url_str in seen:
                continue
            seen.add(url_str)
            results.append(
                SerpResult(
                    rank=len(results) + 1,
                    url=item.url,
                    title=item.title,
                    snippet=item.snippet,
                )
            )
            if len(results) >= MAX_RESULTS:
                break
        if len(results) >= MAX_RESULTS:
            break

    logger.info("serp.collected count=%s", len(results))

    if len(results) < MIN_COLLECTED_PAGES:
        raise InsufficientCollectionError(
            minimum=MIN_COLLECTED_PAGES, actual=len(results), stage="serp"
        )

    return SerpResults(
        keyword=keyword,
        collected_at=datetime.now().astimezone(),
        results=results,
    )


def _parse_serp_html(html: str) -> list[SerpResult]:
    """SERP HTML 에서 네이버 블로그 URL 을 추출한다.

    네이버 검색 결과 마크업이 버전에 따라 크게 달라진다:
    - 구버전: `<a href="https://blog.naver.com/...">`
    - 신버전: `<button data-url="https://blog.naver.com/...">` (a 태그 미사용)

    DOM 위치에 의존하지 않고 `href` 또는 `data-url` 속성을 가진 모든 태그를
    순회해 BLOG_POST_URL_RE 로 필터링한다. 선착순 MAX_RESULTS.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: list[SerpResult] = []

    candidates = soup.find_all(
        lambda tag: isinstance(tag, Tag) and (tag.has_attr("href") or tag.has_attr("data-url"))
    )

    for node in candidates:
        if not isinstance(node, Tag):
            continue
        href = str(node.get("href") or node.get("data-url") or "").strip()
        normalized = _normalize_href(href)
        if normalized is None:
            continue
        if normalized in seen:
            continue
        if _is_ad_context(node):
            continue
        seen.add(normalized)

        title = node.get_text(strip=True)
        if not title:
            # title 이 비어 있으면 (data-url 버튼은 비어 있는 경우 많음) placeholder.
            title = "(untitled)"

        results.append(
            SerpResult(
                rank=len(results) + 1,
                url=normalized,  # type: ignore[arg-type]
                title=title,
                snippet="",
            )
        )

        if len(results) >= MAX_RESULTS:
            break

    logger.info("serp.parsed count=%s", len(results))
    return results


def _normalize_href(href: str) -> str | None:
    """네이버 블로그 포스트 URL 이면 그대로 반환, 아니면 None."""
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    elif href.startswith("/"):
        return None  # 상대 경로는 블로그 원문 링크 아님
    try:
        parsed = urlparse(href)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.netloc not in ("blog.naver.com", "m.blog.naver.com"):
        return None
    canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if not BLOG_POST_URL_RE.match(canonical):
        return None
    return canonical


def _is_ad_context(anchor: Tag) -> bool:
    """네이버 검색 광고 섹션 여부 휴리스틱 — 부모 체인에 'ads' 힌트가 있으면 True."""
    for parent in anchor.parents:
        if not isinstance(parent, Tag):
            continue
        cls_attr = parent.get("class")
        classes = cls_attr if isinstance(cls_attr, list) else []
        joined = " ".join(str(c).lower() for c in classes)
        if "ads" in joined or "ad_area" in joined or "sp_power_ad" in joined:
            return True
        section_id = str(parent.get("id", "")).lower()
        if section_id.startswith("power_ad") or section_id == "nx_query_related":
            return True
    return False
