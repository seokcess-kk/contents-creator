"""URL 등록 CLI.

얇은 argparse 래퍼 — 실제 로직은 `application.ranking_orchestrator.register_publication`.
SPEC-RANKING.md §7 참조.

예 (본 프로젝트로 발행한 글):
    python scripts/register_publication.py \\
        --keyword "신사 다이어트 한의원" \\
        --slug "신사다이어트한의원" \\
        --url "https://blog.naver.com/myblog/123456789" \\
        --published-at "2026-04-24"

예 (외부 URL 추적):
    python scripts/register_publication.py \\
        --keyword "신사 다이어트 한의원" \\
        --url "https://blog.naver.com/competitor/987654321"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime

from application.ranking_orchestrator import register_publication


def _non_empty(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("값은 공백일 수 없습니다")
    return stripped


def _iso_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"ISO 형식 날짜가 아닙니다 (예: 2026-04-24): {value!r}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="네이버 블로그 발행 URL 등록 (SPEC-RANKING.md §3 [등록])",
    )
    parser.add_argument("--keyword", type=_non_empty, required=True, help="추적 검색어")
    parser.add_argument("--url", type=_non_empty, required=True, help="네이버 블로그 포스트 URL")
    parser.add_argument(
        "--slug",
        type=_non_empty,
        default=None,
        help="output 디렉터리 매칭용 slug (선택, 외부 URL 추적이면 생략)",
    )
    parser.add_argument("--job-id", type=str, default=None, help="원본 job_id (선택)")
    parser.add_argument(
        "--published-at",
        type=_iso_date,
        default=None,
        help="발행 시점 ISO date (선택, 기본 등록 시각)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    try:
        publication = register_publication(
            keyword=args.keyword,
            slug=args.slug,
            url=args.url,
            job_id=args.job_id,
            published_at=args.published_at,
        )
    except ValueError as exc:
        logger.error("등록 실패: %s", exc)
        return 1

    logger.info(
        "등록 완료: %s", json.dumps(publication.model_dump(mode="json"), ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
