"""키워드 난이도 스냅샷 Supabase CRUD.

`config/schema.sql` 13번 `keyword_difficulty_snapshots` 테이블 사용.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from config.supabase import get_client
from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SearchVolume,
    SerpComposition,
    SerpSection,
)

logger = logging.getLogger(__name__)

_TABLE = "keyword_difficulty_snapshots"


def insert_snapshot(diff: KeywordDifficulty) -> KeywordDifficulty:
    """KeywordDifficulty → Supabase 1행 저장."""
    client = get_client()
    payload: dict[str, Any] = {
        "keyword": diff.keyword,
        "score": diff.score,
        "grade": diff.grade.value,
        "total_cards": diff.composition.total_cards,
        "blog_slots": diff.composition.blog_slots,
        "spam_cards": diff.composition.spam_cards,
        "sections_json": {s.value: c for s, c in diff.composition.section_counts.items()},
        "checked_at": (diff.checked_at or datetime.now()).isoformat(),
    }
    if diff.search_volume is not None:
        payload["monthly_pc_search"] = diff.search_volume.monthly_pc
        payload["monthly_mobile_search"] = diff.search_volume.monthly_mobile
        payload["monthly_total_search"] = diff.search_volume.monthly_total
        payload["competition_idx"] = diff.search_volume.competition_idx
    result = client.table(_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError(f"{_TABLE} insert: no row returned")
    return _row_to_diff(cast("dict[str, Any]", rows[0]))


def get_latest(keyword: str) -> KeywordDifficulty | None:
    """단일 키워드의 가장 최근 스냅샷."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("keyword", keyword)
        .order("checked_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return _row_to_diff(cast("dict[str, Any]", rows[0]))


def list_recent(*, limit: int = 50) -> list[KeywordDifficulty]:
    """전체 스냅샷 최근순 — 키워드별 최신만 반환하지 않음 (히스토리 포함)."""
    client = get_client()
    result = client.table(_TABLE).select("*").order("checked_at", desc=True).limit(limit).execute()
    return [_row_to_diff(cast("dict[str, Any]", r)) for r in (result.data or [])]


def list_by_grade(grade: DifficultyGrade, *, limit: int = 100) -> list[KeywordDifficulty]:
    """등급으로 필터링한 스냅샷 최근순."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("grade", grade.value)
        .order("checked_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_diff(cast("dict[str, Any]", r)) for r in (result.data or [])]


def list_keyword_history(keyword: str, *, limit: int = 30) -> list[KeywordDifficulty]:
    """단일 키워드의 분석 히스토리 (최근순)."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("keyword", keyword)
        .order("checked_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_diff(cast("dict[str, Any]", r)) for r in (result.data or [])]


def _row_to_diff(row: dict[str, Any]) -> KeywordDifficulty:
    sections_json = row.get("sections_json") or {}
    section_counts: dict[SerpSection, int] = {}
    for k, v in sections_json.items():
        try:
            section_counts[SerpSection(k)] = int(v)
        except ValueError:
            continue  # 알려지지 않은 섹션 키는 무시

    composition = SerpComposition(
        section_counts=section_counts,
        total_cards=int(row.get("total_cards") or 0),
    )
    checked_at_raw = row.get("checked_at")
    checked_at: datetime | None = None
    if isinstance(checked_at_raw, str):
        try:
            checked_at = datetime.fromisoformat(checked_at_raw.replace("Z", "+00:00"))
        except ValueError:
            checked_at = None

    search_volume: SearchVolume | None = None
    pc = row.get("monthly_pc_search")
    mobile = row.get("monthly_mobile_search")
    if pc is not None or mobile is not None:
        search_volume = SearchVolume(
            monthly_pc=int(pc or 0),
            monthly_mobile=int(mobile or 0),
            competition_idx=row.get("competition_idx"),
        )

    return KeywordDifficulty(
        keyword=row["keyword"],
        score=float(row["score"]),
        grade=DifficultyGrade(row["grade"]),
        composition=composition,
        search_volume=search_volume,
        checked_at=checked_at,
    )
