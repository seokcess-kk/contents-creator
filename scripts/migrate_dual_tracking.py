"""재발행 듀얼 트래킹 정책 백필 CLI.

기본은 dry-run. --apply 시 실제 DB 갱신.
특정 키워드만 정리하려면 --keyword 반복.

예 (dry-run, 모든 대상):
    python scripts/migrate_dual_tracking.py

예 (4개 키워드만 실제 적용):
    python scripts/migrate_dual_tracking.py --apply \\
        --keyword 압구정한의원 \\
        --keyword 대전다이어트약 \\
        --keyword 웨스턴다이어트 \\
        --keyword 부평다이어트한의원
"""

from __future__ import annotations

import argparse
import logging
import sys

from application.dual_tracking_migration import (
    apply_dual_tracking_migration,
    collect_dual_tracking_targets,
)
from domain.ranking.model import Publication


def _log_targets(label: str, pubs: list[Publication], logger: logging.Logger) -> None:
    logger.info("[%s] %d개", label, len(pubs))
    for p in pubs:
        logger.info("  - %s keyword=%r url=%s", p.id, p.keyword, p.url)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="재발행 듀얼 트래킹 정책 백필 (republishing/draft → active)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 DB 갱신 (기본: dry-run)",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=None,
        help="특정 키워드만 정리 (반복 가능, 미지정 시 모두)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    targets = collect_dual_tracking_targets(args.keyword)
    _log_targets("republishing → active", targets["parents_to_activate"], logger)
    _log_targets("draft+url → active", targets["drafts_to_activate"], logger)

    if not args.apply:
        logger.info("--apply 미지정. dry-run 종료.")
        return 0

    counts = apply_dual_tracking_migration(args.keyword)
    logger.info(
        "적용 완료: parents=%d drafts=%d failed=%d",
        counts["parents_activated"],
        counts["drafts_activated"],
        counts["failed"],
    )
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
