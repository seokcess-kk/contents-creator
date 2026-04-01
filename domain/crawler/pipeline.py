"""크롤러 파이프라인. 키워드 → 상위글 수집 → HTML + 스크린샷 저장."""

from __future__ import annotations

import json
import logging

from domain.common.config import settings
from domain.crawler.blog_scraper import extract_blog_content
from domain.crawler.model import CrawlResult, PostData
from domain.crawler.naver_search import search_blog
from domain.crawler.screenshot import capture_screenshot_sync

logger = logging.getLogger(__name__)


def run_crawl(keyword: str, top_n: int = 10) -> CrawlResult:
    """키워드로 네이버 상위 블로그를 크롤링한다.

    1. 네이버 검색 API로 상위 N개 URL 수집
    2. 각 URL의 블로그 본문 HTML 추출
    3. 각 URL의 풀페이지 스크린샷 캡처
    4. _workspace/01_crawl/ 에 결과 저장

    Args:
        keyword: 검색 키워드
        top_n: 수집할 상위 결과 수

    Returns:
        CrawlResult
    """
    workspace = settings.workspace_dir / "01_crawl"
    posts_dir = workspace / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)

    # 1. 네이버 검색
    logger.info("=== 크롤링 시작: '%s' (상위 %d개) ===", keyword, top_n)
    search_results = search_blog(keyword, top_n)

    posts: list[PostData] = []
    success_count = 0
    fail_count = 0

    for i, result in enumerate(search_results, start=1):
        rank_str = f"{i:02d}"
        logger.info("[%s/%d] %s", rank_str, len(search_results), result.link)

        post = PostData(
            rank=i,
            url=result.link,
            title=result.title,
            post_date=result.post_date,
        )

        # 2. 블로그 본문 추출
        try:
            raw_html, text_content = extract_blog_content(result.link)
            post.raw_html = raw_html
            post.text_content = text_content

            # HTML 저장
            html_path = posts_dir / f"{rank_str}_raw.html"
            html_path.write_text(raw_html, encoding="utf-8")
        except Exception as e:
            logger.error("[%s] 본문 추출 실패: %s", rank_str, e)
            post.success = False
            post.error = str(e)
            fail_count += 1
            posts.append(post)
            continue

        # 3. 스크린샷
        screenshot_path = posts_dir / f"{rank_str}_screenshot.png"
        captured = capture_screenshot_sync(result.link, screenshot_path)
        if captured:
            post.screenshot_path = str(screenshot_path)
        else:
            logger.warning("[%s] 스크린샷 실패, HTML만 저장", rank_str)

        success_count += 1
        posts.append(post)

    # 4. 메타데이터 저장
    crawl_result = CrawlResult(
        keyword=keyword,
        top_n=top_n,
        posts=posts,
        total_success=success_count,
        total_failed=fail_count,
        workspace_path=str(workspace),
    )

    metadata_path = workspace / "metadata.json"
    metadata_path.write_text(
        json.dumps(crawl_result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "=== 크롤링 완료: 성공 %d / 실패 %d ===",
        success_count,
        fail_count,
    )
    return crawl_result
