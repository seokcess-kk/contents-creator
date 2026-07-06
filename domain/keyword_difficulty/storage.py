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
    SmartblockInfo,
    SovValueGrade,
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
    payload["sov_grade"] = diff.sov_grade.value
    payload["smartblock_present"] = diff.composition.smartblock.present
    payload["smartblock_count"] = diff.composition.smartblock.count
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


# 키워드별 dedupe 시 PostgREST 단일 호출로 가져올 raw row 상한.
# Supabase max-rows default 1000. 키워드당 평균 history 깊이 × unique 키워드 수
# 보다 충분히 크게 잡아 dedupe 결과가 잘리지 않도록 한다.
_DEDUPE_FETCH_LIMIT = 1000


def list_latest_per_keyword(
    *,
    limit: int = 200,
    fetch_limit: int = _DEDUPE_FETCH_LIMIT,
) -> list[KeywordDifficulty]:
    """키워드별 최신 스냅샷 1개만 — 최근 분석된 unique 키워드 limit 개.

    `list_recent` 는 snapshot row 기준이라 같은 키워드의 옛 스냅샷이 섞여
    화면 상에서 unique 키워드가 잘리는 문제가 있다. 본 함수는 raw row 를
    fetch_limit 만큼 최근순으로 가져온 뒤 키워드별 최신만 in-memory dedupe
    해 keyword 기준의 최신 limit 개를 반환한다.
    """
    client = get_client()
    result = (
        client.table(_TABLE).select("*").order("checked_at", desc=True).limit(fetch_limit).execute()
    )
    rows = result.data or []
    seen: set[str] = set()
    out: list[KeywordDifficulty] = []
    for r in rows:
        row = cast("dict[str, Any]", r)
        kw = row.get("keyword")
        if not kw or kw in seen:
            continue
        seen.add(kw)
        out.append(_row_to_diff(row))
        if len(out) >= limit:
            break
    return out


def list_latest_per_keyword_by_grade(
    grade: DifficultyGrade,
    *,
    limit: int = 100,
    fetch_limit: int = _DEDUPE_FETCH_LIMIT,
) -> list[KeywordDifficulty]:
    """등급 필터 + 키워드별 최신 1개만."""
    client = get_client()
    result = (
        client.table(_TABLE)
        .select("*")
        .eq("grade", grade.value)
        .order("checked_at", desc=True)
        .limit(fetch_limit)
        .execute()
    )
    rows = result.data or []
    seen: set[str] = set()
    out: list[KeywordDifficulty] = []
    for r in rows:
        row = cast("dict[str, Any]", r)
        kw = row.get("keyword")
        if not kw or kw in seen:
            continue
        seen.add(kw)
        out.append(_row_to_diff(row))
        if len(out) >= limit:
            break
    return out


def delete_by_keyword(keyword: str) -> int:
    """단일 키워드의 모든 스냅샷 삭제 — 히스토리 전체 제거.

    `publications.keyword_difficulty_snapshot_id` FK 는 `on delete set null`
    이므로 발행 이력은 보존되고 연결만 끊어진다.

    Returns: 삭제된 row 수.
    """
    client = get_client()
    result = client.table(_TABLE).delete().eq("keyword", keyword).execute()
    rows = result.data or []
    return len(rows)


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

    # 스마트블록 — 컬럼이 아직 없는 옛 row (마이그레이션 이전) 는 default 적용
    smartblock = SmartblockInfo(
        present=bool(row.get("smartblock_present") or False),
        count=int(row.get("smartblock_count") or 0),
    )
    composition = SerpComposition(
        section_counts=section_counts,
        total_cards=int(row.get("total_cards") or 0),
        smartblock=smartblock,
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

    sov_raw = row.get("sov_grade")
    try:
        sov_grade = SovValueGrade(sov_raw) if sov_raw else SovValueGrade.UNKNOWN
    except ValueError:
        sov_grade = SovValueGrade.UNKNOWN

    return KeywordDifficulty(
        id=row.get("id"),
        keyword=row["keyword"],
        score=float(row["score"]),
        grade=DifficultyGrade(row["grade"]),
        composition=composition,
        search_volume=search_volume,
        sov_grade=sov_grade,
        checked_at=checked_at,
    )
