"""keyword_batch_items.failure_category 1회성 백필 (2026-05-14).

기존 row 중 status IN ('failed','skipped','needs_review') AND failure_category IS NULL
인 row 의 error 텍스트를 정규식으로 분석해 7종 enum 으로 매핑한다.

운영 안전 가드 (2중):
  1) --apply 옵션 없으면 dry-run (DB write 0). 매칭 카운트 + 샘플만 로깅
  2) --apply 사용 시에도 환경변수 BACKFILL_CONFIRM=YES 가 없으면 거부

예 (dry-run):
    python scripts/backfill_failure_category.py

예 (실제 적용):
    BACKFILL_CONFIRM=YES python scripts/backfill_failure_category.py --apply

매칭 불가 row 는 EXCEPTION 으로 마킹 (catch-all). 추후 패턴 추가 후 재실행 가능.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from collections import Counter
from typing import Any, cast

from config.supabase import get_client
from domain.batch.model import FailureCategory

logger = logging.getLogger(__name__)

# 정규식 → FailureCategory 매핑 순서 (먼저 매칭되는 것 우선).
# error 텍스트 예시는 application/batch_orchestrator.py 와 domain/crawler/model.py 참조.
_PATTERNS: list[tuple[re.Pattern[str], FailureCategory]] = [
    (re.compile(r"^prefilter:.*search_volume", re.IGNORECASE), "PREFILTER_VOLUME"),
    (re.compile(r"^prefilter:.*difficulty", re.IGNORECASE), "PREFILTER_DIFFICULTY"),
    # orchestrator 가 RuntimeError 로 wrap 하므로 "RuntimeError: serp: ..." 형태로 들어옴.
    # InsufficientCollectionError 가 직접 raise 되는 경로도 대비해 양쪽 모두 매칭.
    (re.compile(r"(^|: )serp: \d+ pages collected", re.IGNORECASE), "SERP_INSUFFICIENT"),
    (re.compile(r"(^|: )scrape: \d+ pages collected", re.IGNORECASE), "SCRAPE_INSUFFICIENT"),
    # 본문 차별화 부족은 _dispatch_item 본문에서 compliance_violations 에 push 되며
    # error 컬럼에는 안 들어가는 경우가 있음 — 별도 검사 (classify_row 에서 보강).
    (re.compile(r"본문.차별화.부족|body.similarity.high", re.IGNORECASE), "BODY_SIMILARITY_HIGH"),
    (re.compile(r"compliance|의료법", re.IGNORECASE), "COMPLIANCE_FAILED"),
]

_ITEM_TABLE = "keyword_batch_items"
_TARGET_STATUSES = ("failed", "skipped", "needs_review")


def classify_row(error_text: str | None, violations: list[str] | None) -> FailureCategory:
    """error 텍스트 + compliance_violations 결합해 enum 결정.

    우선순위: violations 의 '본문_차별화_부족' > error 정규식 매칭 > EXCEPTION (catch-all).
    error_text=None 이고 violations 비어 있어도 EXCEPTION 반환 (status 가 failure 인데
    원문이 사라진 row 도 일단 분류 — 운영자가 사후 검토).
    """
    if violations and "본문_차별화_부족" in violations:
        return "BODY_SIMILARITY_HIGH"
    if error_text:
        for pattern, category in _PATTERNS:
            if pattern.search(error_text):
                return category
    return "EXCEPTION"


def _fetch_target_rows() -> list[dict[str, Any]]:
    """failure_category IS NULL 이고 status 가 failure 계열인 row 만 fetch."""
    client = get_client()
    result = (
        client.table(_ITEM_TABLE)
        .select("id, status, error, failure_category, compliance_violations, keyword")
        .in_("status", list(_TARGET_STATUSES))
        .is_("failure_category", "null")
        .execute()
    )
    return cast("list[dict[str, Any]]", result.data or [])


def _apply_update(item_id: str, category: FailureCategory) -> None:
    """단건 update — failure_category 만 채움 (다른 컬럼 무변경)."""
    get_client().table(_ITEM_TABLE).update({"failure_category": category}).eq(
        "id", item_id
    ).execute()


def run(*, apply: bool, sample_size: int = 5) -> int:
    """반환: 0=성공, 1=guard 위반 또는 매칭 0건."""
    rows = _fetch_target_rows()
    logger.info("backfill.fetched count=%d", len(rows))
    if not rows:
        logger.info("backfill.no_targets — failure_category 가 NULL 인 failure row 없음")
        return 0

    counter: Counter[FailureCategory] = Counter()
    samples: dict[FailureCategory, list[str]] = {}
    for row in rows:
        cat = classify_row(row.get("error"), row.get("compliance_violations") or [])
        counter[cat] += 1
        samples.setdefault(cat, [])
        if len(samples[cat]) < sample_size:
            samples[cat].append(
                f"id={row.get('id')} keyword={row.get('keyword')!r} error={row.get('error')!r}"
            )

    for cat, n in counter.most_common():
        logger.info("backfill.classified %s = %d", cat, n)
        for s in samples[cat]:
            logger.info("  sample: %s", s)

    if not apply:
        logger.info("backfill.dry_run — --apply 미사용. DB write 0건.")
        return 0

    if os.environ.get("BACKFILL_CONFIRM") != "YES":
        logger.error(
            "backfill.guard_failed — --apply 사용 시 BACKFILL_CONFIRM=YES 필수. 거부."
        )
        return 1

    updated = 0
    for row in rows:
        cat = classify_row(row.get("error"), row.get("compliance_violations") or [])
        item_id = str(row.get("id"))
        try:
            _apply_update(item_id, cat)
            updated += 1
        except Exception:
            logger.exception("backfill.update_failed item_id=%s", item_id)
    logger.info("backfill.done updated=%d / total=%d", updated, len(rows))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="keyword_batch_items.failure_category 백필 (1회성, 2026-05-14)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제 DB 갱신 (기본: dry-run). BACKFILL_CONFIRM=YES 환경변수 필수.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="카테고리별 출력 샘플 수 (default 5)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(apply=args.apply, sample_size=args.sample_size)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
