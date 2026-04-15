"""분석만 실행 CLI ([1]~[5]).

얇은 argparse 래퍼 — 실제 로직은 `application.orchestrator.run_analyze_only`.
"""

from __future__ import annotations

import argparse
import logging
import sys

from application.models import StageStatus
from application.orchestrator import run_analyze_only
from application.progress import LoggingProgressReporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="분석 파이프라인만 실행: [1] SERP → [5] 패턴 카드 (SPEC.md §3)",
    )
    parser.add_argument("--keyword", required=True, help="타겟 네이버 검색 키워드")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    result = run_analyze_only(
        keyword=args.keyword,
        reporter=LoggingProgressReporter(),
    )
    return 0 if result.status == StageStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
