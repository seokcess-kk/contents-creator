from __future__ import annotations

from web.api.routers.usage import _aggregate, _aggregate_by_day, _aggregate_by_provider


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
    rows = [
        {"provider": "brightdata", "requests": 1, "created_at": "2026-05-03T00:00:00Z"},
        {"provider": "naver_searchad", "requests": 1, "created_at": "2026-05-03T01:00:00Z"},
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
