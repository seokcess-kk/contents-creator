"""SPEC-BATCH Phase 2 PR2 — 사전 필터 단위 테스트.

`_apply_prefilter` 가 KeywordDifficulty 결과로 임계값 검사 후 통과/미달 분기.
analyze_keyword 호출은 모두 mock 처리해 실제 SERP/검색량 fetch 0건.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from application import batch_orchestrator
from domain.batch.model import KeywordBatch, KeywordBatchItem
from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SearchVolume,
    SerpComposition,
    SovValueGrade,
)


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "operation": "analyze",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def _batch(**overrides: object) -> KeywordBatch:
    base: dict[str, object] = {"id": "b-1", "total_count": 5}
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


def _difficulty(*, grade: str, monthly_total: int | None) -> KeywordDifficulty:
    composition = SerpComposition(section_counts={}, total_cards=10)
    # SearchVolume.monthly_total 은 (monthly_pc + monthly_mobile) property 라
    # 모바일 컬럼에 monthly_total 을 모두 담아 합계 일치시킴.
    sv = SearchVolume(monthly_mobile=monthly_total) if monthly_total is not None else None
    # DifficultyGrade 값은 소문자 (low/medium/high/missing)
    return KeywordDifficulty(
        keyword="kw",
        composition=composition,
        score=0.0,
        grade=DifficultyGrade(grade.lower()),
        search_volume=sv,
        sov_grade=SovValueGrade.UNKNOWN,
    )


@pytest.fixture
def storage_mock() -> Any:
    with patch("application.batch_orchestrator.storage") as m:
        yield m


def test_no_thresholds_skips_call() -> None:
    """임계값 모두 None → _has_prefilter False → analyze_keyword 호출 안 됨."""
    batch = _batch()  # min_search_volume / max_difficulty 모두 None
    assert batch_orchestrator._has_prefilter(batch) is False


def test_search_volume_below_threshold_skips(storage_mock: Any) -> None:
    """검색량 미달 → skipped."""
    batch = _batch(min_search_volume=200)
    item = _item()
    diff = _difficulty(grade="LOW", monthly_total=50)
    with patch(
        "application.keyword_difficulty_orchestrator.analyze_keyword",
        return_value=diff,
    ):
        passed = batch_orchestrator._apply_prefilter(item, batch)
    assert passed is False
    # skipped status 마킹 + error="prefilter: ..."
    last_status = storage_mock.update_item_status.call_args.args[1]
    assert last_status == "skipped"
    err = storage_mock.update_item_status.call_args.kwargs["error"]
    assert err.startswith("prefilter:")
    assert "search_volume=50" in err


def test_search_volume_none_passes(storage_mock: Any) -> None:
    """검색량 fetch 실패(None) 는 미달로 보지 않음 — graceful pass."""
    batch = _batch(min_search_volume=200)
    item = _item()
    diff = _difficulty(grade="LOW", monthly_total=None)
    with patch(
        "application.keyword_difficulty_orchestrator.analyze_keyword",
        return_value=diff,
    ):
        passed = batch_orchestrator._apply_prefilter(item, batch)
    assert passed is True


def test_difficulty_above_max_skips(storage_mock: Any) -> None:
    """난이도 초과 → skipped (max_difficulty=MEDIUM 인데 결과 HIGH)."""
    batch = _batch(max_difficulty="MEDIUM")
    item = _item()
    diff = _difficulty(grade="HIGH", monthly_total=1000)
    with patch(
        "application.keyword_difficulty_orchestrator.analyze_keyword",
        return_value=diff,
    ):
        passed = batch_orchestrator._apply_prefilter(item, batch)
    assert passed is False
    err = storage_mock.update_item_status.call_args.kwargs["error"]
    assert "difficulty=high>MEDIUM" in err


def test_both_thresholds_pass_records_meta(storage_mock: Any) -> None:
    """둘 다 통과 → True + update_item_result 에 사전 필터 메타 저장."""
    batch = _batch(min_search_volume=100, max_difficulty="HIGH")
    item = _item()
    diff = _difficulty(grade="MEDIUM", monthly_total=500)
    with patch(
        "application.keyword_difficulty_orchestrator.analyze_keyword",
        return_value=diff,
    ):
        passed = batch_orchestrator._apply_prefilter(item, batch)
    assert passed is True
    storage_mock.update_item_result.assert_called_once()
    kwargs = storage_mock.update_item_result.call_args.kwargs
    assert kwargs["search_volume"] == 500
    assert kwargs["difficulty_grade"] == "medium"


def test_analyze_keyword_raises_passes_gracefully(storage_mock: Any) -> None:
    """analyze_keyword 가 raise 해도 batch 진행 차단 안 함 — graceful True."""
    batch = _batch(min_search_volume=100)
    item = _item()
    with patch(
        "application.keyword_difficulty_orchestrator.analyze_keyword",
        side_effect=RuntimeError("brightdata 503"),
    ):
        passed = batch_orchestrator._apply_prefilter(item, batch)
    assert passed is True
    # update_item_status 호출 안 됨 (skipped 마킹 안 함)
    storage_mock.update_item_status.assert_not_called()


def test_unknown_difficulty_value_passes(storage_mock: Any) -> None:
    """rank dict 에 없는 grade → graceful pass (False positive 회피)."""
    assert batch_orchestrator._exceeds_difficulty("unknown_grade", "MEDIUM") is False
    assert batch_orchestrator._exceeds_difficulty("LOW", "weird") is False
