from __future__ import annotations

from typing import Any

from web.api.routers.usage import (
    _aggregate,
    _aggregate_by_day,
    _aggregate_by_provider,
    _fetch_all_usage,
    _kst_date,
)


def test_usage_aggregate_splits_billable_and_free_requests() -> None:
    rows = [
        {"provider": "brightdata", "requests": 1, "estimated_cost_usd": 0.01},
        {"provider": "naver_searchad", "requests": 1, "estimated_cost_usd": 0},
        {"provider": "anthropic", "requests": 2, "estimated_cost_usd": 0.02},
    ]

    totals = _aggregate(rows)

    assert totals["requests"] == 4
    assert totals["billable_requests"] == 3
    assert totals["free_requests"] == 1
    assert totals["estimated_cost_usd"] == 0.03


def test_usage_provider_aggregate_marks_naver_searchad_free() -> None:
    rows = [
        {"provider": "brightdata", "requests": 1, "estimated_cost_usd": 0.01},
        {"provider": "naver_searchad", "requests": 2, "estimated_cost_usd": 0},
    ]

    by_provider = {row["provider"]: row for row in _aggregate_by_provider(rows)}

    assert by_provider["brightdata"]["billing_type"] == "billable"
    assert by_provider["brightdata"]["billable_requests"] == 1
    assert by_provider["brightdata"]["free_requests"] == 0
    assert by_provider["naver_searchad"]["billing_type"] == "free"
    assert by_provider["naver_searchad"]["billable_requests"] == 0
    assert by_provider["naver_searchad"]["free_requests"] == 2


def test_usage_day_aggregate_splits_billable_and_free_requests() -> None:
    # 09:00 / 10:00 UTC = 18:00 / 19:00 KST → 둘 다 KST 2026-05-03
    rows = [
        {"provider": "brightdata", "requests": 1, "created_at": "2026-05-03T09:00:00Z"},
        {"provider": "naver_searchad", "requests": 1, "created_at": "2026-05-03T10:00:00Z"},
    ]

    by_day = _aggregate_by_day(rows)

    assert by_day == [
        {
            "date": "2026-05-03",
            "requests": 2,
            "billable_requests": 1,
            "free_requests": 1,
            "tokens": 0,
            "cost": 0.0,
        }
    ]


def test_kst_date_handles_midnight_to_9am_kst_window() -> None:
    """KST 자정~오전 9시 호출은 UTC 전날 15~24시 → KST 일자로 정확히 변환."""
    # 2026-05-03 00:30 KST = 2026-05-02 15:30 UTC
    assert _kst_date("2026-05-02T15:30:00+00:00") == "2026-05-03"
    # 2026-05-03 08:59 KST = 2026-05-02 23:59 UTC
    assert _kst_date("2026-05-02T23:59:00Z") == "2026-05-03"
    # 2026-05-03 09:00 KST = 2026-05-03 00:00 UTC (경계)
    assert _kst_date("2026-05-03T00:00:00Z") == "2026-05-03"
    # 2026-05-03 23:30 KST = 2026-05-03 14:30 UTC
    assert _kst_date("2026-05-03T14:30:00Z") == "2026-05-03"


def test_kst_date_falls_back_for_invalid_input() -> None:
    """파싱 불가 시 UTC prefix 폴백 — None/빈/형식오류 처리."""
    assert _kst_date(None) == ""
    assert _kst_date("") == ""
    assert _kst_date("not-a-date") == "not-a-date"  # 10자 prefix 폴백


def test_aggregate_by_day_shifts_late_night_kst_calls_to_correct_day() -> None:
    """KST 새벽 호출이 'UTC 전날'로 잘못 집계되던 사고 회귀 방지."""
    # KST 2026-05-03 02:00 = UTC 2026-05-02 17:00
    rows = [
        {"provider": "anthropic", "requests": 1, "created_at": "2026-05-02T17:00:00Z"},
    ]
    by_day = _aggregate_by_day(rows)
    assert len(by_day) == 1
    assert by_day[0]["date"] == "2026-05-03"


class _FakePage:
    """Supabase chain mock — execute() 가 .data 속성을 가진 객체 반환."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeQuery:
    """체이닝 호출(table/select/gte/eq/order/range/execute) 을 모두 받는 mock."""

    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self._pages = pages
        self._call_count = 0

    def table(self, _name: str) -> _FakeQuery:
        return self

    def select(self, _cols: str) -> _FakeQuery:
        return self

    def gte(self, _col: str, _val: str) -> _FakeQuery:
        return self

    def eq(self, _col: str, _val: str) -> _FakeQuery:
        return self

    def order(self, _col: str, desc: bool = False) -> _FakeQuery:
        return self

    def range(self, _start: int, _end: int) -> _FakeQuery:
        return self

    def execute(self) -> _FakePage:
        if self._call_count >= len(self._pages):
            return _FakePage([])
        page = self._pages[self._call_count]
        self._call_count += 1
        return _FakePage(page)


def test_fetch_all_usage_paginates_until_short_page() -> None:
    """1000 건 만점 페이지가 이어지면 다음 페이지를 더 받아 모두 수확."""
    full_page = [{"provider": "anthropic", "requests": 1}] * 1000
    short_page = [{"provider": "anthropic", "requests": 1}] * 250
    fake = _FakeQuery(pages=[full_page, full_page, short_page])

    rows = _fetch_all_usage(fake, since="2026-04-01T00:00:00+00:00", provider=None)

    assert len(rows) == 2250  # 500 잘림 사고 회귀 방지


def test_fetch_all_usage_stops_on_first_short_page() -> None:
    """첫 페이지가 미만이면 한 번에 종료 — 30일 합계가 1000 미만인 일반 케이스."""
    short_page = [{"provider": "anthropic", "requests": 1}] * 42
    fake = _FakeQuery(pages=[short_page])

    rows = _fetch_all_usage(fake, since="2026-04-01T00:00:00+00:00", provider=None)

    assert len(rows) == 42
