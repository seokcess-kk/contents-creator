"""단계별 실행 헬퍼. orchestrator 가 호출.

각 함수는 도메인 함수를 wrap 하고 ProgressReporter 를 호출한다.
파일 저장도 여기서 수행 (도메인은 순수 계산만 반환).

MVP 스켈레톤 — SPEC-SEO-TEXT.md §8 개발 순서에 따라 순차 구현.
현재: [1] SERP 수집, [2] 본문 수집 완료.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from application.progress import ProgressReporter
from config.settings import require
from domain.crawler.brightdata_client import BrightDataClient
from domain.crawler.model import ScrapeResult, SerpResults
from domain.crawler.page_scraper import scrape_pages
from domain.crawler.serp_collector import collect_serp

logger = logging.getLogger(__name__)


def _build_brightdata_client() -> BrightDataClient:
    """config/.env 로부터 BrightDataClient 를 생성한다."""
    return BrightDataClient(
        api_key=require("bright_data_api_key"),
        zone=require("bright_data_web_unlocker_zone"),
    )


def run_stage_serp_collection(
    keyword: str,
    output_dir: Path,
    reporter: ProgressReporter,
    client: BrightDataClient | None = None,
) -> SerpResults:
    """[1] 네이버 블로그 SERP 수집.

    `output_dir/analysis/serp-results.json` 에 결과를 저장한다.
    `client` 가 None 이면 config 에서 기본 클라이언트를 생성 (테스트 주입 가능).
    """
    reporter.stage_start("serp_collection")

    owned_client = client is None
    if client is None:
        client = _build_brightdata_client()

    try:
        results = collect_serp(keyword, client)
    finally:
        if owned_client:
            client.close()

    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    serp_path = analysis_dir / "serp-results.json"
    serp_path.write_text(
        results.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("serp.saved path=%s count=%s", serp_path, len(results.results))

    reporter.stage_end(
        "serp_collection",
        {"count": len(results.results), "path": str(serp_path)},
    )
    return results


def run_stage_page_scraping(
    serp: SerpResults,
    output_dir: Path,
    reporter: ProgressReporter,
    client: BrightDataClient | None = None,
) -> ScrapeResult:
    """[2] 네이버 블로그 본문 수집.

    HTML 원본은 `output_dir/analysis/pages/{idx}.html`,
    메타는 `output_dir/analysis/pages/index.json` 에 저장한다.
    """
    reporter.stage_start("page_scraping", total=len(serp.results))

    owned_client = client is None
    if client is None:
        client = _build_brightdata_client()

    try:
        result = scrape_pages(serp, client)
    finally:
        if owned_client:
            client.close()

    pages_dir = output_dir / "analysis" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    index_successful: list[dict[str, object]] = []
    for page in result.successful:
        path = pages_dir / f"{page.idx}.html"
        path.write_text(page.html, encoding="utf-8")
        index_successful.append(
            {
                "idx": page.idx,
                "rank": page.rank,
                "url": str(page.url),
                "mobile_url": str(page.mobile_url),
                "path": f"pages/{page.idx}.html",
                "fetched_at": page.fetched_at.isoformat(),
            }
        )

    index_failed = [
        {
            "idx": f.idx,
            "rank": f.rank,
            "url": str(f.url),
            "reason": f.reason,
        }
        for f in result.failed
    ]

    index_path = pages_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {"successful": index_successful, "failed": index_failed},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    reporter.stage_end(
        "page_scraping",
        {
            "successful": len(result.successful),
            "failed": len(result.failed),
            "path": str(pages_dir),
        },
    )
    return result
