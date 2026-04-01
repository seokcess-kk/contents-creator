"""네이버 블로그 본문 HTML을 스크래핑한다.

네이버 블로그는 iframe 구조를 사용한다.
스마트에디터 3.0: div.se-main-container
구버전: div#postViewArea
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_blog_content(url: str) -> tuple[str, str]:
    """블로그 URL에서 본문 HTML과 텍스트를 추출한다.

    Scrapling의 StealthyFetcher로 접근하여 iframe 내부 본문을 파싱한다.

    Args:
        url: 네이버 블로그 포스트 URL

    Returns:
        (raw_html, text_content) 튜플

    Raises:
        RuntimeError: 본문 추출 실패 시
    """
    real_url = _resolve_blog_url(url)
    html = _fetch_with_retry(real_url)
    return _parse_blog_html(html)


def _resolve_blog_url(url: str) -> str:
    """네이버 블로그 URL을 실제 본문 URL로 변환한다.

    모바일 URL이나 리다이렉트 URL을 처리한다.
    blog.naver.com/PostView.naver 형태로 변환.
    """
    # m.blog.naver.com → blog.naver.com
    url = url.replace("m.blog.naver.com", "blog.naver.com")

    # blog.naver.com/{id}/{logNo} → PostView URL로 변환
    match = re.match(
        r"https?://blog\.naver\.com/([^/]+)/(\d+)",
        url,
    )
    if match:
        blogger_id, log_no = match.groups()
        return (
            f"https://blog.naver.com/PostView.naver"
            f"?blogId={blogger_id}&logNo={log_no}&redirect=Dlog"
        )

    return url


def _fetch_with_retry(url: str, max_retries: int = 3) -> str:
    """Scrapling으로 페이지를 가져온다. 실패 시 재시도."""
    from scrapling import StealthyFetcher

    fetcher = StealthyFetcher()

    for attempt in range(max_retries):
        try:
            response = fetcher.fetch(url)
            if response.status == 200:
                return response.html_content
            logger.warning(
                "HTTP %d: %s (시도 %d/%d)",
                response.status,
                url,
                attempt + 1,
                max_retries,
            )
        except Exception as e:
            logger.warning("크롤링 에러: %s (시도 %d/%d)", e, attempt + 1, max_retries)

        if attempt < max_retries - 1:
            time.sleep(2 ** (attempt + 1))

    raise RuntimeError(f"블로그 크롤링 실패 (3회 시도): {url}")


def _parse_blog_html(html: str) -> tuple[str, str]:
    """블로그 HTML에서 본문 영역을 추출한다.

    Returns:
        (본문 HTML, 순수 텍스트) 튜플
    """
    soup = BeautifulSoup(html, "lxml")

    # 스마트에디터 3.0
    container = soup.select_one("div.se-main-container")
    if container:
        return str(container), container.get_text(separator="\n", strip=True)

    # 구버전 에디터
    container = soup.select_one("div#postViewArea")
    if container:
        return str(container), container.get_text(separator="\n", strip=True)

    # 전체 body fallback
    body = soup.select_one("body")
    if body:
        return str(body), body.get_text(separator="\n", strip=True)

    raise RuntimeError("블로그 본문 영역을 찾을 수 없습니다.")
