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
from pathlib import Path

from application import batch_orchestrator
from domain.batch import storage
from domain.batch.model import NotSupportedYetError

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
    parser.add_argument(
        "--mode",
        choices=["now", "overnight", "auto"],
        default="now",
        help="처리 모드 (Phase 1 은 'now' 만 지원)",
    )
    parser.add_argument("--name", type=str, default=None, help="배치 이름 (선택)")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.csv is not None:
        return _enqueue(args.csv, mode=args.mode, name=args.name)
    if args.status is not None:
        return _status(args.status)
    if args.retry_item is not None:
        return _retry(args.retry_item)
    if args.cancel is not None:
        return _cancel(args.cancel)
    return 1  # pragma: no cover — mutually_exclusive_group required=True 가 차단


def _enqueue(csv_path: Path, *, mode: str, name: str | None) -> int:
    if not csv_path.exists():
        logger.error("CSV 파일 없음: %s", csv_path)
        return 1
    csv_text = csv_path.read_text(encoding="utf-8-sig")  # BOM 제거
    try:
        result = batch_orchestrator.enqueue_from_csv(csv_text, mode=mode, name=name)
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


if __name__ == "__main__":
    sys.exit(main())
