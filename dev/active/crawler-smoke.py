"""Phase 1 크롤러 E2E 스모크.

실제 Bright Data 호출로 [1] SERP 수집 + [2] 본문 수집을 실행해
output/{slug}/{ts}/analysis/{serp-results.json, pages/*.html, pages/index.json}
이 생성되는지 확인한다.

사용:
    .venv/Scripts/python.exe dev/active/crawler-smoke.py --keyword "강남 다이어트 한의원"
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from application.progress import LoggingProgressReporter
from application.stage_runner import (
    run_stage_page_scraping,
    run_stage_serp_collection,
)


def slugify(keyword: str) -> str:
    s = re.sub(r"\s+", "-", keyword.strip().lower())
    return re.sub(r"[^a-z0-9가-힣\-]", "", s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 crawler smoke test")
    parser.add_argument("--keyword", required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    slug = slugify(args.keyword)
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    output_dir = Path("output") / slug / ts
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[smoke] keyword={args.keyword}")
    print(f"[smoke] output_dir={output_dir}")

    reporter = LoggingProgressReporter()

    serp = run_stage_serp_collection(
        keyword=args.keyword,
        output_dir=output_dir,
        reporter=reporter,
    )
    print(f"[smoke] serp count={len(serp.results)}")
    for r in serp.results[:3]:
        print(f"  rank={r.rank} url={r.url}")

    scrape = run_stage_page_scraping(
        serp=serp,
        output_dir=output_dir,
        reporter=reporter,
    )
    print(
        f"[smoke] scrape successful={len(scrape.successful)} "
        f"failed={len(scrape.failed)}"
    )
    for page in scrape.successful[:3]:
        html_bytes = len(page.html.encode("utf-8"))
        print(f"  idx={page.idx} mobile={page.mobile_url} bytes={html_bytes}")

    print(f"[smoke] done - inspect {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
