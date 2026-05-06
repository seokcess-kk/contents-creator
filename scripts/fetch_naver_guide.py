"""[일회용] 네이버 서치어드바이저 가이드 페이지 일괄 수집.

본 SEO 파이프라인과 무관한 자료 수집 스크립트.
1) sitemap.xml fetch → /guide/* 로 시작하는 URL 목록 추출
2) 각 가이드 페이지 fetch → docs/raw/naver-guide/{slug}.html 저장
3) docs/raw/naver-guide/_index.json 에 (url, slug, title, fetched_at) 기록

Bright Data Web Unlocker 단일 zone 으로 fetch (domain/crawler/CLAUDE.md #1 준수).
가이드 사이트는 Nuxt SPA라 SSR HTML 의 <a> 추출로는 불충분 → sitemap.xml 기반.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from config.settings import settings
from domain.crawler.brightdata_client import BrightDataClient, BrightDataError

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://searchadvisor.naver.com/sitemap.xml"
GUIDE_PREFIX = "https://searchadvisor.naver.com/guide"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "raw" / "naver-guide"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _slugify(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", path).strip("-")
    return slug or "index"


def _extract_guide_urls_from_sitemap(xml_text: str) -> list[str]:
    root = ElementTree.fromstring(xml_text)
    urls: list[str] = []
    for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
        if loc.text and loc.text.strip().startswith(GUIDE_PREFIX):
            urls.append(loc.text.strip())
    seen: set[str] = set()
    deduped: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    api_key = settings.bright_data_api_key
    zone = settings.bright_data_web_unlocker_zone
    if not api_key or not zone:
        logger.error("BRIGHT_DATA_API_KEY / BRIGHT_DATA_WEB_UNLOCKER_ZONE 가 설정되지 않았습니다.")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with BrightDataClient(api_key=api_key, zone=zone) as client:
        logger.info("[1/3] sitemap fetch: %s", SITEMAP_URL)
        try:
            sitemap_xml = client.fetch(SITEMAP_URL)
        except BrightDataError as exc:
            logger.error("sitemap fetch 실패: %s", exc)
            return 3
        (OUTPUT_DIR / "_sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

        logger.info("[2/3] sitemap 에서 /guide URL 추출")
        urls = _extract_guide_urls_from_sitemap(sitemap_xml)
        logger.info("발견한 가이드 페이지 수: %d", len(urls))
        if not urls:
            logger.error("sitemap 에 /guide URL 이 없습니다. 샘플:\n%s", sitemap_xml[:500])
            return 4

        index: list[dict[str, str]] = []
        ok, fail = 0, 0
        for i, url in enumerate(urls, 1):
            slug = _slugify(url)
            out_path = OUTPUT_DIR / f"{slug}.html"
            logger.info("[3/3] (%d/%d) %s → %s", i, len(urls), url, out_path.name)
            try:
                html = client.fetch(url)
            except BrightDataError as exc:
                logger.warning("fetch 실패: %s (%s)", url, exc)
                fail += 1
                continue
            out_path.write_text(html, encoding="utf-8")
            index.append(
                {
                    "url": url,
                    "slug": slug,
                    "file": out_path.name,
                    "title": _extract_title(html),
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
            )
            ok += 1

    index_path = OUTPUT_DIR / "_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("완료: 성공 %d / 실패 %d / 인덱스 %s", ok, fail, index_path)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
