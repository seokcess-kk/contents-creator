"""생성만 실행 CLI ([6]~[9]).

얇은 argparse 래퍼 — 실제 로직은 `application.orchestrator.run_generate_only`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from application.models import StageStatus
from application.orchestrator import run_generate_only
from application.progress import LoggingProgressReporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="생성 파이프라인만 실행: [6] 아웃라인 → [9] HTML (SPEC.md §3)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--keyword",
        help="키워드 (DB 에서 최신 패턴 카드 자동 조회)",
    )
    group.add_argument(
        "--pattern-card",
        type=Path,
        help="기존 패턴 카드 JSON 파일 경로",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    result = run_generate_only(
        keyword=args.keyword,
        pattern_card_path=args.pattern_card,
        reporter=LoggingProgressReporter(),
    )
    return 0 if result.status == StageStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
