"""의료법 검증만 실행 CLI ([8]).

얇은 argparse 래퍼 — 실제 로직은 `application.orchestrator.run_validate_only`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from application.models import StageStatus
from application.orchestrator import run_validate_only
from application.progress import LoggingProgressReporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="의료법 검증만 실행: [8] 3중 방어 (SPEC-SEO-TEXT.md §3)",
    )
    parser.add_argument(
        "--content",
        type=Path,
        required=True,
        help="검증 대상 원고 파일 경로 (.md)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    result = run_validate_only(
        content_path=args.content,
        reporter=LoggingProgressReporter(),
    )
    return 0 if result.status == StageStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
