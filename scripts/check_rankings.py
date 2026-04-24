"""순위 추적 CLI — 단일 또는 전체 publication 즉시 체크.

스케줄러는 매일 자동 실행하지만, 본 스크립트로 즉시 트리거 가능.

예:
    python scripts/check_rankings.py --publication-id <uuid>
    python scripts/check_rankings.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from application.ranking_orchestrator import (
    check_all_active_rankings,
    check_rankings_for_publication,
)
from domain.ranking.model import RankingMatchError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="순위 추적 즉시 실행 (SPEC-RANKING.md §3 [수집])",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--publication-id", type=str, help="단일 publication 즉시 체크")
    group.add_argument("--all", action="store_true", help="등록된 모든 publication 일괄 체크")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    if args.all:
        summary = check_all_active_rankings()
        logger.info(
            "체크 완료: %s",
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False),
        )
        return 0

    try:
        snapshot = check_rankings_for_publication(args.publication_id)
    except ValueError as exc:
        logger.error("체크 실패: %s", exc)
        return 1
    except RankingMatchError as exc:
        logger.error("SERP 측정 실패: %s", exc)
        return 2

    logger.info(
        "체크 완료: %s",
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
