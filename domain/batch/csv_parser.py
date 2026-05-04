"""CSV → KeywordBatchItem 리스트 변환 + 검증.

지원 컬럼 (SPEC-BATCH §3 Phase 1 입력):
    keyword (필수), operation, priority, cluster_id, cluster_role,
    intent, region, brand_id, target_url, memo

검증 규칙:
- keyword: 비어 있으면 failed
- operation: invalid 값은 failed (analyze/generate/pipeline 외)
- priority: 1~9 범위 외는 default 5 폴백 (warning)
- mode: CSV 컬럼 X — batch 단위로 받음 (item.mode 는 batch.mode 상속)
- cluster_role: invalid 값은 default 'member' 폴백
- 중복 keyword: 같은 batch 안에서는 첫 row 만 created, 나머지는 skipped
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from domain.batch.model import (
    ClusterRole,
    KeywordBatchItem,
    Operation,
)

logger = logging.getLogger(__name__)

_VALID_OPERATIONS: tuple[Operation, ...] = ("analyze", "generate", "pipeline")
_VALID_CLUSTER_ROLES: tuple[ClusterRole, ...] = ("primary", "member")
_REQUIRED_COLUMNS = ("keyword",)


def parse_csv(
    csv_text: str,
    *,
    batch_id: str = "pending",
    default_mode: str = "now",
) -> tuple[list[KeywordBatchItem], list[dict[str, str]], list[dict[str, str]]]:
    """CSV 문자열을 파싱해 (created_items, skipped, failed) 반환.

    batch_id 가 'pending' 이면 storage 가 batch insert 후 채움.
    """
    created: list[KeywordBatchItem] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    seen_keywords: set[str] = set()

    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ValueError("CSV 에 헤더가 없습니다 — 첫 줄에 컬럼 이름 필요")

    missing = [c for c in _REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {', '.join(missing)}")

    for idx, row in enumerate(reader, start=2):  # 2 = 헤더 다음 줄
        item, reason = _parse_row(row, batch_id=batch_id, default_mode=default_mode)
        if item is None:
            failed.append({"row": str(idx), "reason": reason or "unknown"})
            continue
        key = item.keyword.strip().lower()
        if key in seen_keywords:
            skipped.append({"row": str(idx), "reason": "중복 키워드", "keyword": item.keyword})
            continue
        seen_keywords.add(key)
        created.append(item)

    logger.info(
        "csv_parser.done created=%d skipped=%d failed=%d",
        len(created),
        len(skipped),
        len(failed),
    )
    return created, skipped, failed


def _parse_row(
    row: dict[str, Any], *, batch_id: str, default_mode: str
) -> tuple[KeywordBatchItem | None, str | None]:
    """단일 CSV row → KeywordBatchItem. 실패 시 (None, reason)."""
    keyword = (row.get("keyword") or "").strip()
    if not keyword:
        return None, "keyword 비어있음"

    operation_raw = (row.get("operation") or "analyze").strip().lower()
    if operation_raw not in _VALID_OPERATIONS:
        return None, f"invalid operation: {operation_raw!r}"

    cluster_role_raw = (row.get("cluster_role") or "member").strip().lower()
    if cluster_role_raw not in _VALID_CLUSTER_ROLES:
        cluster_role_raw = "member"

    priority = _safe_int(row.get("priority"), default=5)
    if not 1 <= priority <= 9:
        priority = 5

    return (
        KeywordBatchItem(
            batch_id=batch_id,
            keyword=keyword,
            operation=operation_raw,  # type: ignore[arg-type]
            mode=default_mode,  # type: ignore[arg-type]
            priority=priority,
            cluster_id=_strip_or_none(row.get("cluster_id")),
            cluster_role=cluster_role_raw,  # type: ignore[arg-type]
            intent=_strip_or_none(row.get("intent")),
            region=_strip_or_none(row.get("region")),
            brand_id=_strip_or_none(row.get("brand_id")),
            target_url=_strip_or_none(row.get("target_url")),
            memo=_strip_or_none(row.get("memo")),
        ),
        None,
    )


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _safe_int(value: Any, *, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
