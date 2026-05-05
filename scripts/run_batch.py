"""키워드 배치 운영 CLI. SPEC-BATCH.md §7 참조.

얇은 argparse 래퍼 — 실제 로직은 `application.batch_orchestrator`.

예 (CSV 업로드 + 즉시 처리):
    python scripts/run_batch.py --csv keywords.csv --mode now --name "캠페인1"

예 (배치 진행 상태 조회):
    python scripts/run_batch.py --status <batch_id>

예 (실패 단건 수동 재시도):
    python scripts/run_batch.py --retry-item <item_id>

CSV 컬럼: keyword (필수), operation, priority, cluster_id, cluster_role,
intent, region, brand_id, target_url, memo
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from application import batch_orchestrator
from config.settings import settings
from domain.batch import storage
from domain.batch.model import NotSupportedYetError

_KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="키워드 배치 운영 (SPEC-BATCH.md Phase 1)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", type=Path, help="CSV 파일 경로 — 새 배치 enqueue")
    group.add_argument("--status", type=str, help="배치 ID — 진행 상태 조회")
    group.add_argument("--retry-item", type=str, help="item ID — 수동 재시도")
    group.add_argument("--cancel", type=str, help="배치 ID — queued items cancelled 마킹")
    group.add_argument(
        "--backfill-fk",
        type=str,
        dest="backfill_fk",
        help="배치 ID — fire-and-forget 회수 실패한 pattern_card_id/generated_content_id 사후 백필",
    )
    group.add_argument(
        "--dispatch-overnight",
        action="store_true",
        dest="dispatch_overnight",
        help="Phase 3 PR1 — overnight 모드 batch 일괄 dispatch (야간 cron 또는 운영자 트리거)",
    )
    parser.add_argument(
        "--overnight-batch-id",
        type=str,
        default=None,
        help="--dispatch-overnight 와 함께 — 특정 batch 만 처리 (없으면 전체 overnight queued)",
    )
    parser.add_argument(
        "--mode",
        choices=["now", "overnight", "auto"],
        default="now",
        help="처리 모드 (Phase 1 은 'now' 만 지원)",
    )
    parser.add_argument("--name", type=str, default=None, help="배치 이름 (선택)")
    # Phase 2 PR2 — 사전 필터 + cluster 재사용 옵션 (--csv 모드에서만 의미)
    parser.add_argument(
        "--min-search-volume",
        type=int,
        default=None,
        help="사전 필터 — 월 검색량 미달 키워드 자동 skipped (None=필터 안 함)",
    )
    parser.add_argument(
        "--max-difficulty",
        type=str,
        choices=["LOW", "MEDIUM", "HIGH", "MISSING"],
        default=None,
        help="사전 필터 — 난이도 초과 키워드 자동 skipped (None=필터 안 함)",
    )
    parser.add_argument(
        "--cluster-dedupe",
        action="store_true",
        help="cluster_id 의 primary→member PatternCard 재사용 (default OFF, 본문 유사도 리스크)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.csv is not None:
        return _enqueue(
            args.csv,
            mode=args.mode,
            name=args.name,
            min_search_volume=args.min_search_volume,
            max_difficulty=args.max_difficulty,
            cluster_dedupe=args.cluster_dedupe,
        )
    if args.status is not None:
        return _status(args.status)
    if args.retry_item is not None:
        return _retry(args.retry_item)
    if args.cancel is not None:
        return _cancel(args.cancel)
    if args.backfill_fk is not None:
        return _backfill(args.backfill_fk)
    if args.dispatch_overnight:
        return _dispatch_overnight(args.overnight_batch_id)
    return 1  # pragma: no cover — mutually_exclusive_group required=True 가 차단


def _enqueue(
    csv_path: Path,
    *,
    mode: str,
    name: str | None,
    min_search_volume: int | None = None,
    max_difficulty: str | None = None,
    cluster_dedupe: bool = False,
) -> int:
    if not csv_path.exists():
        logger.error("CSV 파일 없음: %s", csv_path)
        return 1
    csv_text = csv_path.read_text(encoding="utf-8-sig")  # BOM 제거
    try:
        result = batch_orchestrator.enqueue_from_csv(
            csv_text,
            mode=mode,
            name=name,
            min_search_volume=min_search_volume,
            max_difficulty=max_difficulty,
            cluster_dedupe=cluster_dedupe,
        )
    except NotSupportedYetError as exc:
        logger.error("미지원 모드: %s", exc)
        return 2
    except ValueError as exc:
        logger.error("CSV 파싱 실패: %s", exc)
        return 3

    print(  # noqa: T201 — CLI 출력
        f"\n배치 enqueue 완료\n"
        f"  batch_id   : {result.batch_id}\n"
        f"  total      : {result.total}\n"
        f"  created    : {result.created}\n"
        f"  skipped    : {len(result.skipped)}\n"
        f"  failed     : {len(result.failed)}\n"
    )
    if result.skipped:
        print("  skipped 상세 (최대 5건):")  # noqa: T201
        for s in result.skipped[:5]:
            print(f"    - row {s.get('row')}: {s.get('reason')} ({s.get('keyword', '-')})")  # noqa: T201
    if result.failed:
        print("  failed 상세 (최대 5건):")  # noqa: T201
        for f in result.failed[:5]:
            print(f"    - row {f.get('row')}: {f.get('reason')}")  # noqa: T201
    return 0


def _status(batch_id: str) -> int:
    batch = storage.get_batch(batch_id)
    if batch is None:
        logger.error("배치 미존재: %s", batch_id)
        return 1
    counters = storage.count_items_by_status(batch_id)
    body = batch.model_dump(mode="json")
    body.update(counters)
    print(json.dumps(body, ensure_ascii=False, indent=2))  # noqa: T201

    # 최근 실패 5건 보너스
    failed_items = storage.list_items(batch_id, status="failed", limit=5)
    if failed_items:
        print("\n최근 failed (최대 5건):")  # noqa: T201
        for it in failed_items:
            print(f"  - {it.id} keyword={it.keyword} retries={it.retry_count} err={it.error}")  # noqa: T201
    return 0


def _retry(item_id: str) -> int:
    try:
        batch_orchestrator.retry_item(item_id)
    except ValueError as exc:
        logger.error("재시도 불가: %s", exc)
        return 1
    print(f"item {item_id} → queued (재시도 큐)")  # noqa: T201
    return 0


def _cancel(batch_id: str) -> int:
    try:
        cancelled = batch_orchestrator.cancel_batch(batch_id)
    except ValueError as exc:
        logger.error("배치 미존재: %s", exc)
        return 1
    print(f"batch {batch_id} cancelled={cancelled}")  # noqa: T201
    return 0


def _dispatch_overnight(batch_id: str | None) -> int:
    """Phase 3 PR1 — overnight batch 일괄 dispatch.

    Phase 3 PR2 추가 — cron 친화 시간대 게이트:
      - `batch_id` 명시 시: 운영자 의도 트리거 → 게이트 우회
      - `BATCH_OVERNIGHT_FORCE=true` env: 시간대 게이트 우회 (수동 즉시 dispatch)
      - 그 외: 현재 KST 시각이 `BATCH_OVERNIGHT_HOUR_KST` (default 22) 일 때만 실행,
        아니면 noop (exit 0). 외부 cron 이 매시간 호출해도 1회만 실행되도록.
    """
    if not _is_overnight_window(batch_id=batch_id):
        current = datetime.now(_KST).hour
        logger.info(
            "overnight 시간대 아님 (현재: %d시 KST, 활성: %d시). force=False — noop",
            current,
            settings.batch_overnight_hour_kst,
        )
        return 0
    try:
        result = batch_orchestrator.dispatch_overnight_batches(batch_id=batch_id)
    except Exception as exc:
        logger.error("overnight dispatch 실패: %s", exc)
        return 1
    print(  # noqa: T201
        f"\novernight dispatch 완료\n"
        f"  dispatched_batches : {result['dispatched_batches']}\n"
        f"  dispatched_items   : {result['dispatched_items']}\n"
        f"  skipped_batches    : {result['skipped_batches']}\n"
    )
    return 0


def _is_overnight_window(*, batch_id: str | None) -> bool:
    """현재 KST 시각이 overnight dispatch 활성 시간대인지 판정.

    우선순위:
      1. batch_id 명시: 운영자 명시 트리거 → True
      2. settings.batch_overnight_force: env 즉시 트리거 → True
      3. 현재 KST 시각 == settings.batch_overnight_hour_kst → True
      4. 그 외 → False (noop)
    """
    if batch_id is not None:
        return True
    if settings.batch_overnight_force:
        return True
    return datetime.now(_KST).hour == settings.batch_overnight_hour_kst


def _backfill(batch_id: str) -> int:
    """SPEC-BATCH §3 Phase 2 PR4 — fire-and-forget 회수 실패 사후 백필 운영 도구."""
    try:
        result = batch_orchestrator.backfill_unlinked_items(batch_id)
    except Exception as exc:
        logger.error("백필 실패: %s", exc)
        return 1
    print(  # noqa: T201
        f"\n배치 {batch_id} 백필 완료\n"
        f"  matched_pattern_cards   : {result['matched_pattern_cards']}\n"
        f"  matched_generated       : {result['matched_generated_contents']}\n"
        f"  still_unlinked          : {result['still_unlinked']}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
