"""keyword_difficulty/storage.py — list_latest_per_keyword 단위 테스트.

list_recent 는 snapshot row 기준이라 같은 키워드의 옛 스냅샷이 섞여
화면에서 unique 키워드가 잘리는 문제가 있다. 본 테스트는 신규 함수가
키워드별 최신만 반환하는지 + limit 가 키워드(=row) 기준인지 검증한다.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from domain.keyword_difficulty import storage as st
from domain.keyword_difficulty.model import DifficultyGrade


def _row(keyword: str, checked_at: str, grade: str = "medium") -> dict[str, Any]:
    return {
        "id": f"id-{keyword}-{checked_at}",
        "keyword": keyword,
        "score": 0.0,
        "grade": grade,
        "total_cards": 10,
        "blog_slots": 3,
        "spam_cards": 2,
        "sections_json": {},
        "smartblock_present": False,
        "smartblock_count": 0,
        "checked_at": checked_at,
    }


def _client_with_rows(rows: list[dict[str, Any]]) -> MagicMock:
    chain = MagicMock()
    chain.execute.return_value = SimpleNamespace(data=rows)
    client = MagicMock()
    client.table.return_value = chain
    # PostgREST 체이닝 — .select().order().limit() / .eq().order().limit() 모두 chain 자체 반환
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.eq.return_value = chain
    return client


class TestListLatestPerKeyword:
    def test_dedupe_keeps_latest_per_keyword(self) -> None:
        # checked_at desc 로 정렬된 raw rows — keyword A 는 2개, B/C 는 1개씩
        rows = [
            _row("A", "2026-05-13T10:00:00+00:00"),
            _row("B", "2026-05-13T09:00:00+00:00"),
            _row("A", "2026-05-12T08:00:00+00:00"),  # A 의 옛 스냅샷
            _row("C", "2026-05-12T07:00:00+00:00"),
        ]
        client = _client_with_rows(rows)
        with patch.object(st, "get_client", return_value=client):
            result = st.list_latest_per_keyword(limit=10)
        keywords = [r.keyword for r in result]
        # unique 3개, A 는 최신 스냅샷 1개만
        assert keywords == ["A", "B", "C"]

    def test_limit_counts_unique_keywords_not_rows(self) -> None:
        # raw rows 5개 (unique 키워드 3개) — limit=2 면 키워드 2개 반환
        rows = [
            _row("A", "2026-05-13T10:00:00+00:00"),
            _row("A", "2026-05-13T09:00:00+00:00"),
            _row("B", "2026-05-13T08:00:00+00:00"),
            _row("B", "2026-05-13T07:00:00+00:00"),
            _row("C", "2026-05-13T06:00:00+00:00"),
        ]
        client = _client_with_rows(rows)
        with patch.object(st, "get_client", return_value=client):
            result = st.list_latest_per_keyword(limit=2)
        assert [r.keyword for r in result] == ["A", "B"]

    def test_empty_rows_returns_empty_list(self) -> None:
        client = _client_with_rows([])
        with patch.object(st, "get_client", return_value=client):
            result = st.list_latest_per_keyword(limit=10)
        assert result == []


class TestListLatestPerKeywordByGrade:
    def test_grade_filter_then_dedupe(self) -> None:
        rows = [
            _row("A", "2026-05-13T10:00:00+00:00", grade="low"),
            _row("A", "2026-05-12T08:00:00+00:00", grade="low"),
            _row("B", "2026-05-13T09:00:00+00:00", grade="low"),
        ]
        client = _client_with_rows(rows)
        with patch.object(st, "get_client", return_value=client):
            result = st.list_latest_per_keyword_by_grade(DifficultyGrade.LOW, limit=10)
        assert [r.keyword for r in result] == ["A", "B"]
        # .eq("grade", "low") 호출 확인
        client.table.return_value.eq.assert_called_with("grade", "low")
