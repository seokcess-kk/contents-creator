"""네이버 검색 API를 통해 키워드 상위 블로그 URL을 수집한다."""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request

from domain.common.config import settings
from domain.crawler.model import NaverSearchResult

logger = logging.getLogger(__name__)

NAVER_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def search_blog(keyword: str, top_n: int = 10) -> list[NaverSearchResult]:
    """네이버 블로그 검색 API로 상위 N개 결과를 반환한다.

    Args:
        keyword: 검색 키워드
        top_n: 수집할 결과 수 (최대 100)

    Returns:
        NaverSearchResult 리스트
    """
    if not settings.naver_client_id or not settings.naver_client_secret:
        raise ValueError("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")

    results: list[NaverSearchResult] = []
    display = min(top_n, 100)

    params = urllib.parse.urlencode(
        {
            "query": keyword,
            "display": display,
            "start": 1,
            "sort": "sim",
        }
    )
    url = f"{NAVER_BLOG_SEARCH_URL}?{params}"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", settings.naver_client_id)
    request.add_header("X-Naver-Client-Secret", settings.naver_client_secret)

    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except Exception as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                logger.warning("네이버 API 에러: %s, %d초 후 재시도", e, wait)
                time.sleep(wait)
            else:
                logger.error("네이버 API 3회 실패: %s", e)
                raise

    for item in data.get("items", []):
        results.append(
            NaverSearchResult(
                title=_strip_html(item.get("title", "")),
                link=item.get("link", ""),
                description=_strip_html(item.get("description", "")),
                blogger_name=item.get("bloggername", ""),
                blogger_link=item.get("bloggerlink", ""),
                post_date=item.get("postdate", ""),
            )
        )

    logger.info("네이버 검색 '%s': %d개 결과 수집", keyword, len(results))
    return results[:top_n]


def _strip_html(text: str) -> str:
    """HTML 태그를 제거한다."""
    import re

    return re.sub(r"<[^>]+>", "", text)
