"""CSV → KeywordBatchItem 리스트 변환 + 검증.

지원 컬럼 (SPEC-BATCH §3 Phase 1 입력):
    keyword (필수), operation, priority, cluster_id, cluster_role,
    intent, region, brand_id, target_url, memo, blog (별칭 또는 네이버 blog_id)

검증 규칙:
- keyword: 비어 있으면 failed
- operation: invalid 값은 failed (analyze/generate/pipeline 외)
- priority: 1~9 범위 외는 default 5 폴백 (warning)
- mode: CSV 컬럼 X — batch 단위로 받음 (item.mode 는 batch.mode 상속)
- cluster_role: invalid 값은 default 'member' 폴백
- 중복 keyword: 같은 batch 안에서는 첫 row 만 created, 나머지는 skipped
- blog: blog_resolver 가 주어지면 호출 (lookup). 미일치 시 blog_channel_id=None + warning

도메인 격리 원칙상 csv_parser 는 다른 도메인 (blog_channel) 을 import 하지
않는다. blog 별칭/ID → blog_channel_id 변환은 application 레이어가 주입하는
`blog_resolver: Callable[[str], str | None]` 로 처리한다.
"""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Callable
from typing import Any

from domain.batch.model import (
    ClusterRole,
    KeywordBatchItem,
    Operation,
)

BlogResolver = Callable[[str], str | None]
"""blog 별칭/ID → blog_channel_id 또는 None. 미일치 시 None 반환."""

logger = logging.getLogger(__name__)

_VALID_OPERATIONS: tuple[Operation, ...] = ("analyze", "generate", "pipeline")
_VALID_CLUSTER_ROLES: tuple[ClusterRole, ...] = ("primary", "member")
_REQUIRED_COLUMNS = ("keyword",)

# 운영자 다운로드용 CSV 템플릿 헤더 — 미니멀 (필수 1 + 자주 쓰는 1).
# parse_csv 는 다른 컬럼 (priority/cluster_*/intent/region/brand_id/target_url/
# memo/blog) 도 모두 지원하지만, 첫 사용자가 11컬럼을 보고 머뭇거리는 사례가
# 있어 템플릿은 keyword + operation 만 노출. 추가 컬럼이 필요한 운영자는
# BatchUploadForm 의 안내문구 또는 본 모듈 docstring 의 "지원 컬럼" 참조해
# Excel 에서 직접 헤더 추가.
_TEMPLATE_HEADERS = ("keyword", "operation")

_TEMPLATE_SAMPLE_ROWS: tuple[tuple[str, ...], ...] = (
    ("예시 키워드 1", "pipeline"),
    ("예시 키워드 2", "pipeline"),
)


def build_csv_template(*, with_bom: bool = True) -> str:
    """운영자 다운로드용 CSV 템플릿 문자열 (미니멀: keyword + operation).

    with_bom: Windows Excel 에서 한글 깨짐 방지 (UTF-8 BOM 부착).
    헤더 + 안내 예시 2행. 사용자는 예시 행을 지우거나 자기 키워드로 교체.
    추가 컬럼 (priority/cluster_*/intent/region/brand_id/target_url/memo/blog)
    이 필요하면 Excel 에서 헤더 행에 직접 추가 — parse_csv 가 그대로 인식.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_TEMPLATE_HEADERS)
    for row in _TEMPLATE_SAMPLE_ROWS:
        writer.writerow(row)
    text = buf.getvalue()
    return ("﻿" + text) if with_bom else text


def parse_csv(
    csv_text: str,
    *,
    batch_id: str = "pending",
    default_mode: str = "now",
    blog_resolver: BlogResolver | None = None,
) -> tuple[list[KeywordBatchItem], list[dict[str, str]], list[dict[str, str]]]:
    """CSV 문자열을 파싱해 (created_items, skipped, failed) 반환.

    batch_id 가 'pending' 이면 storage 가 batch insert 후 채움.

    blog_resolver: CSV `blog` 컬럼 raw 텍스트(별칭 또는 네이버 blog_id) → blog_channel_id
    변환 함수. 미주입 시 모든 row 의 blog_channel_id=None.
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
        item, reason = _parse_row(
            row,
            batch_id=batch_id,
            default_mode=default_mode,
            blog_resolver=blog_resolver,
        )
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
    row: dict[str, Any],
    *,
    batch_id: str,
    default_mode: str,
    blog_resolver: BlogResolver | None = None,
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

    blog_raw = _strip_or_none(row.get("blog"))
    blog_channel_id: str | None = None
    if blog_raw and blog_resolver is not None:
        blog_channel_id = blog_resolver(blog_raw)
        if blog_channel_id is None:
            logger.warning(
                "csv_parser.blog_alias_unmatched keyword=%s blog=%r — blog_channel_id=null",
                keyword,
                blog_raw,
            )

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
            blog_channel_id=blog_channel_id,
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
