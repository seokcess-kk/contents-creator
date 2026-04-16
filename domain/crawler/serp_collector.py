"""[1] 네이버 블로그 SERP 수집.

SPEC-SEO-TEXT.md §3 [1] 구현. Bright Data Web Unlocker 로 네이버 블로그
검색 결과 페이지를 fetch 한 뒤 BeautifulSoup 으로 블로그 URL 을 파싱한다.

- 쿼리: `https://search.naver.com/search.naver?query={keyword}&where=blog`
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

# 네이버 블로그 일반 포스트 URL 패턴. /clip/ (동영상 클립) 및 유저 홈(숫자 없음) 배제.
# 예: https://blog.naver.com/ssmaa/224246591163
BLOG_POST_URL_RE = re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}$")


def build_serp_url(keyword: str) -> str:
    """키워드 → 네이버 블로그 탭 검색 URL."""
    return f"https://search.naver.com/search.naver?query={quote(keyword)}&where=blog"


def collect_serp(keyword: str, client: BrightDataClient) -> SerpResults:
    """네이버 블로그 SERP 를 수집해 SerpResults 로 반환.

    수집 수가 MIN_COLLECTED_PAGES 미만이면 InsufficientCollectionError 발생.
    """
    serp_url = build_serp_url(keyword)
    logger.info("serp.collect keyword=%s", keyword)
    html = client.fetch(serp_url)
    results = _parse_serp_html(html)

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

    네이버 검색 결과 마크업이 변동 가능하므로 DOM 위치에 과도하게 의존하지 않고,
    `a[href]` 전체를 순회하며 BLOG_POST_URL_RE 로 필터링한다. 선착순 MAX_RESULTS.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: list[SerpResult] = []

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor.get("href", "")).strip()
        normalized = _normalize_href(href)
        if normalized is None:
            continue
        if normalized in seen:
            continue
        if _is_ad_context(anchor):
            continue
        seen.add(normalized)

        title = anchor.get_text(strip=True)
        if not title:
            # title 이 비어 있으면 추후 본문 수집 시 메타만으로도 충분하므로 placeholder.
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
