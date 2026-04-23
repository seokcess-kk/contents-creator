"""전체 파이프라인 CLI.

얇은 argparse 래퍼 — 실제 로직은 `application.orchestrator.run_pipeline`.
Phase 2 FastAPI 라우터도 동일한 함수를 호출한다.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from application.models import StageStatus
from application.orchestrator import run_pipeline
from application.progress import LoggingProgressReporter


def _non_empty_keyword(value: str) -> str:
    """공백만 있거나 빈 문자열을 거부하는 argparse type validator."""
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("keyword must be non-empty")
    return stripped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="전체 SEO 원고 생성 파이프라인 실행 (SPEC-SEO-TEXT.md §3 [1]~[9])",
    )
    parser.add_argument(
        "--keyword",
        required=True,
        type=_non_empty_keyword,
        help="타겟 네이버 검색 키워드",
    )
    parser.add_argument(
        "--pattern-card",
        type=Path,
        default=None,
        help="기존 패턴 카드 JSON 경로 (지정 시 [1]~[5] 분석 스킵하고 재사용)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="[9] AI 이미지 생성 단계를 스킵",
    )
    parser.add_argument(
        "--regenerate-images",
        action="store_true",
        help="이미지 prompt 해시 캐시를 무시하고 강제 재생성",
    )
    parser.add_argument(
        "--force-analyze",
        action="store_true",
        help="캐시된 패턴 카드가 있어도 분석을 처음부터 다시 실행",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    result = run_pipeline(
        keyword=args.keyword,
        reporter=LoggingProgressReporter(),
        pattern_card_path=args.pattern_card,
        generate_images=not args.no_images,
        regenerate_images=args.regenerate_images,
        force_analyze=args.force_analyze,
    )
    return 0 if result.status == StageStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
