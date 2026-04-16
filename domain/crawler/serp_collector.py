"""[1] 네이버 블로그 SERP 수집 — 통합검색 우선 + 블로그 탭 보충.

SPEC-SEO-TEXT.md §3 [1] 구현. Bright Data Web Unlocker 로 네이버 블로그
검색 결과 페이지를 fetch 한 뒤 BeautifulSoup 으로 블로그 URL 을 파싱한다.

제품 의도: **통합검색 상위 노출 블로그** 를 분석하는 것이 본 파이프라인의
목적. 따라서 항상 `where=blog` 통합검색부터 시도한다. 그러나 네이버 신버전
UI 가 통합검색 블로그 섹션에 6~7개만 초기 렌더링하므로 (2026-04-16 실측),
7개 미만 또는 MAX_RESULTS(10) 미달 시 `ssc=tab.blog.all` 블로그 전용 탭에서
**최대 5개까지** 중복을 제거하며 보충한다. 각 결과에는 `source` 필드로 출처
트랙을 기록해 패턴 카드에서 구분 가능하게 한다.

- 통합검색 쿼리: `search.naver.com/search.naver?query={kw}&where=blog`
- 블로그 탭 쿼리: `search.naver.com/search.naver?ssc=tab.blog.all&query={kw}&start=1`
- 파서: `a[href]` + `*[data-url]` 둘 다 순회 (네이버 신버전 UI 대응)
- 필터: `blog.naver.com` / `m.blog.naver.com` 외 배제, `/clip/` 배제, 광고 배제
- 합쳐서 7개 미만이면 InsufficientCollectionError 발생
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
    SerpSource,
)

logger = logging.getLogger(__name__)

MAX_RESULTS = 10
# 통합검색이 표본을 다 채우지 못할 때, 블로그 탭에서 보충으로 끌어오는 최대 개수.
# 의도는 "통합검색 상위 노출" 분석이므로 블로그 탭 비중을 5개 이하로 제한해
# 분석 품질의 중심이 통합검색 결과에 남도록 한다.
BLOG_TAB_BOOST_LIMIT = 5

# 네이버 블로그 일반 포스트 URL 패턴. /clip/ (동영상 클립) 및 유저 홈(숫자 없음) 배제.
# 예: https://blog.naver.com/ssmaa/224246591163
BLOG_POST_URL_RE = re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}$")


def build_integrated_serp_url(keyword: str) -> str:
    """통합검색 블로그 섹션 URL (`where=blog`).

    네이버 통합검색 상위 노출 블로그를 대상으로 한다. 제품 의도가 "통합검색
    상위 노출 분석" 이므로 본 파이프라인의 기본 수집 경로.
    """
    return f"https://search.naver.com/search.naver?query={quote(keyword)}&where=blog"


def build_blog_tab_serp_url(keyword: str, start: int = 1) -> str:
    """블로그 전용 탭 URL (`ssc=tab.blog.all`).

    한 페이지에 40개 이상 포스트를 서버 렌더링한다. 통합검색 수집이 표본
    부족일 때 `BLOG_TAB_BOOST_LIMIT` 만큼만 보충용으로 호출한다.
    """
    return (
        "https://search.naver.com/search.naver"
        f"?ssc=tab.blog.all&query={quote(keyword)}&start={start}"
    )


def collect_serp(keyword: str, client: BrightDataClient) -> SerpResults:
    """통합검색 우선 + 블로그 탭 보충 전략으로 네이버 블로그 SERP 수집.

    Step 1 — 통합검색(`where=blog`) 에서 있는 만큼 수집.
    Step 2 — MAX_RESULTS 미달이면 블로그 탭에서 중복 제거하며 최대
             BLOG_TAB_BOOST_LIMIT 개까지 이어 붙임.
    Step 3 — 합계 < MIN_COLLECTED_PAGES 이면 InsufficientCollectionError.

    통합검색 결과의 원 순위(1~N)가 rank 앞쪽에 그대로 보존되고, 블로그 탭
    보충분은 그 뒤에 이어진다. 각 결과의 `source` 필드로 출처를 구분한다.
    """
    logger.info("serp.collect keyword=%s", keyword)

    results: list[SerpResult] = []
    seen: set[str] = set()

    # Step 1: 통합검색
    integrated_url = build_integrated_serp_url(keyword)
    integrated_html = client.fetch(integrated_url)
    _append_unique(
        parsed=_parse_serp_html(integrated_html),
        source="integrated",
        seen=seen,
        results=results,
        cap=MAX_RESULTS,
    )
    integrated_count = len(results)
    logger.info("serp.integrated count=%s", integrated_count)

    # Step 2: 필요 시 블로그 탭 보충
    if len(results) < MAX_RESULTS:
        remaining = MAX_RESULTS - len(results)
        boost_cap_total = len(results) + min(remaining, BLOG_TAB_BOOST_LIMIT)
        blog_tab_url = build_blog_tab_serp_url(keyword)
        blog_tab_html = client.fetch(blog_tab_url)
        _append_unique(
            parsed=_parse_serp_html(blog_tab_html),
            source="blog_tab",
            seen=seen,
            results=results,
            cap=boost_cap_total,
        )
    boost_count = len(results) - integrated_count
    logger.info(
        "serp.collected total=%s integrated=%s blog_tab_boost=%s",
        len(results),
        integrated_count,
        boost_count,
    )

    if len(results) < MIN_COLLECTED_PAGES:
        raise InsufficientCollectionError(
            minimum=MIN_COLLECTED_PAGES, actual=len(results), stage="serp"
        )

    return SerpResults(
        keyword=keyword,
        collected_at=datetime.now().astimezone(),
        results=results,
    )


def _append_unique(
    parsed: list[SerpResult],
    source: SerpSource,
    seen: set[str],
    results: list[SerpResult],
    cap: int,
) -> None:
    """`parsed` 를 순회하며 중복 제거 후 `results` 에 append.

    - `cap` 에 도달하면 조기 종료
    - 추가되는 항목은 `source` 로 출처를 덮어쓰고, rank 는 전체 순서로 재부여
    """
    for item in parsed:
        if len(results) >= cap:
            break
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
                source=source,
            )
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
