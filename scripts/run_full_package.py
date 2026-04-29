"""SEO + 브랜드 카드 합류 패키지 CLI.

얇은 argparse 래퍼 — 실제 로직은 `application.orchestrator.run_full_package`.
ThreadPoolExecutor(2) 로 SEO 파이프라인 + 브랜드 카드 트랙 병렬 실행.
"""

from __future__ import annotations

import argparse
import logging
import sys

from application.models import StageStatus
from application.orchestrator import run_full_package
from application.progress import LoggingProgressReporter
from domain.brand_card.model import ExpressionLevel


def _non_empty(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("must be non-empty")
    return stripped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SEO + 브랜드 카드 합류 패키지 (SPEC-BRAND-CARD §5)",
    )
    parser.add_argument("--keyword", required=True, type=_non_empty, help="타겟 키워드")
    parser.add_argument("--brand-id", required=True, type=_non_empty, help="등록된 브랜드 ID")
    parser.add_argument(
        "--expression-level",
        choices=[e.value for e in ExpressionLevel],
        default=ExpressionLevel.BALANCED.value,
    )
    parser.add_argument("--strategy-count", type=int, default=3, choices=range(1, 5))
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="브랜드 카드 승인 게이트 건너뛰고 [B12] 까지 일괄 실행 (자동화·E2E 용)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    result = run_full_package(
        keyword=args.keyword,
        brand_id=args.brand_id,
        expression_level=args.expression_level,
        strategy_count=args.strategy_count,
        auto_approve=args.auto_approve,
        reporter=LoggingProgressReporter(),
    )

    if result.seo_result is not None:
        print(f"SEO: status={result.seo_result.status.value}")
    if result.brand_card_result is not None:
        print(
            f"BrandCard: status={result.brand_card_result.status.value} "
            f"plans={result.brand_card_result.plan_count} "
            f"rendered={result.brand_card_result.rendered_count}"
        )
    if result.error:
        print(f"오류: {result.error}", file=sys.stderr)

    return 0 if result.status == StageStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
