"""[2] 네이버 블로그 본문 수집.

SPEC-SEO-TEXT.md §3 [2] + tasks/lessons.md C1 섹션 구현.

핵심 결정: 모든 블로그 URL 을 `m.blog.naver.com` 으로 정규화한 뒤
Web Unlocker 를 **단일 호출**로 fetch 한다. 모바일 URL 은 iframe 없이
se-main-container 본문이 직접 렌더되므로 2단계 호출이 불필요하다.

재시도는 BrightDataClient 내부 tenacity 로 처리 (2s → 5s, 총 3회 시도).
URL 당 수집 실패 시 예외를 전파하지 않고 ScrapeFailure 로 누적한다.
최종 성공 수 < MIN_COLLECTED_PAGES 면 InsufficientCollectionError 발생.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from pydantic import HttpUrl

from domain.crawler.brightdata_client import BrightDataClient, BrightDataError
from domain.crawler.model import (
    MIN_COLLECTED_PAGES,
    BlogPage,
    InsufficientCollectionError,
    ScrapeFailure,
    ScrapeResult,
    SerpResults,
)

logger = logging.getLogger(__name__)

_DESKTOP_PREFIX_RE = re.compile(r"^https?://blog\.naver\.com/", flags=re.IGNORECASE)


def normalize_to_mobile(url: str) -> str:
    """`blog.naver.com/...` → `https://m.blog.naver.com/...`.

    이미 `m.blog.naver.com` 이면 scheme 만 https 로 통일해 그대로 반환.
    """
    if _DESKTOP_PREFIX_RE.match(url):
        return _DESKTOP_PREFIX_RE.sub("https://m.blog.naver.com/", url)
    if url.startswith("http://m.blog.naver.com/"):
        return "https://" + url[len("http://") :]
    return url


def scrape_pages(serp: SerpResults, client: BrightDataClient) -> ScrapeResult:
    """SERP 결과의 각 URL 을 순차 fetch 해 ScrapeResult 로 반환.

    성공 수 < MIN_COLLECTED_PAGES 면 InsufficientCollectionError 발생.
    """
    successful: list[BlogPage] = []
    failed: list[ScrapeFailure] = []

    for idx, item in enumerate(serp.results):
        original_url = str(item.url)
        mobile_url = normalize_to_mobile(original_url)
        logger.info("scrape.fetch idx=%s rank=%s url=%s", idx, item.rank, mobile_url)

        try:
            html = client.fetch(mobile_url)
        except BrightDataError as exc:
            logger.warning(
                "scrape.failed idx=%s rank=%s url=%s reason=%s",
                idx,
                item.rank,
                mobile_url,
                exc,
            )
            failed.append(
                ScrapeFailure(
                    idx=idx,
                    rank=item.rank,
                    url=item.url,
                    reason=str(exc),
                )
            )
            continue

        successful.append(
            BlogPage(
                idx=idx,
                rank=item.rank,
                url=item.url,
                mobile_url=HttpUrl(mobile_url),
                html=html,
                fetched_at=datetime.now().astimezone(),
                retries=0,
            )
        )

    logger.info("scrape.done successful=%s failed=%s", len(successful), len(failed))

    if len(successful) < MIN_COLLECTED_PAGES:
        raise InsufficientCollectionError(
            minimum=MIN_COLLECTED_PAGES, actual=len(successful), stage="scrape"
        )

    return ScrapeResult(successful=successful, failed=failed)
