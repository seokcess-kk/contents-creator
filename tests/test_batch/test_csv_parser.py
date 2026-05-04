"""CSV → KeywordBatchItem 변환 + 검증 테스트."""

from __future__ import annotations

import pytest

from domain.batch.csv_parser import parse_csv


def test_parses_minimal_keyword_only_csv() -> None:
    """필수 컬럼 keyword 만 있는 단순 CSV → operation default 'analyze'."""
    csv_text = "keyword\n천안다이어트한의원\n"
    created, skipped, failed = parse_csv(csv_text, batch_id="b-1")
    assert len(created) == 1
    assert created[0].keyword == "천안다이어트한의원"
    assert created[0].operation == "analyze"
    assert created[0].mode == "now"
    assert created[0].priority == 5
    assert created[0].cluster_role == "member"
    assert skipped == [] and failed == []


def test_parses_full_columns() -> None:
    csv_text = (
        "keyword,operation,priority,cluster_id,cluster_role,intent,region,brand_id,target_url,memo\n"
        "천안다이어트,pipeline,1,c-1,primary,info,천안,b-1,https://x/y,첫 분석\n"
    )
    created, _, _ = parse_csv(csv_text, batch_id="b-1")
    item = created[0]
    assert item.operation == "pipeline"
    assert item.priority == 1
    assert item.cluster_id == "c-1"
    assert item.cluster_role == "primary"
    assert item.intent == "info"
    assert item.region == "천안"
    assert item.brand_id == "b-1"
    assert item.target_url == "https://x/y"
    assert item.memo == "첫 분석"


def test_invalid_operation_goes_to_failed() -> None:
    csv_text = "keyword,operation\n키워드1,unknown_op\n키워드2,pipeline\n"
    created, _, failed = parse_csv(csv_text, batch_id="b-1")
    assert len(created) == 1
    assert created[0].keyword == "키워드2"
    assert len(failed) == 1
    assert "operation" in failed[0]["reason"]


def test_empty_keyword_goes_to_failed() -> None:
    csv_text = "keyword,operation\n,analyze\nvalid,analyze\n"
    created, _, failed = parse_csv(csv_text, batch_id="b-1")
    assert len(created) == 1
    assert len(failed) == 1
    assert "keyword" in failed[0]["reason"]


def test_invalid_cluster_role_falls_back_to_member() -> None:
    csv_text = "keyword,cluster_role\nkw,leader\n"
    created, _, _ = parse_csv(csv_text, batch_id="b-1")
    assert created[0].cluster_role == "member"  # invalid → default 폴백


def test_priority_out_of_range_falls_back() -> None:
    csv_text = "keyword,priority\nkw1,15\nkw2,abc\nkw3,3\n"
    created, _, _ = parse_csv(csv_text, batch_id="b-1")
    assert created[0].priority == 5  # 15 → 폴백
    assert created[1].priority == 5  # 'abc' → 폴백
    assert created[2].priority == 3


def test_duplicate_keyword_within_batch_goes_to_skipped() -> None:
    """같은 batch 안의 중복 키워드는 첫 row 만 created, 나머지는 skipped (대소문자 무시)."""
    csv_text = "keyword\n다이어트\nDIET\n다이어트\n비만\n"
    created, skipped, _ = parse_csv(csv_text, batch_id="b-1")
    keywords = [it.keyword for it in created]
    assert keywords == ["다이어트", "DIET", "비만"]  # 3번째 다이어트만 skipped
    assert len(skipped) == 1
    assert skipped[0]["keyword"] == "다이어트"
    assert "중복" in skipped[0]["reason"]


def test_missing_keyword_column_raises_value_error() -> None:
    """필수 헤더 누락 시 ValueError — API 가 400 으로 변환."""
    csv_text = "operation,priority\nanalyze,1\n"
    with pytest.raises(ValueError, match="필수 컬럼 누락"):
        parse_csv(csv_text, batch_id="b-1")


def test_no_header_raises_value_error() -> None:
    """빈 CSV (헤더 없음) — DictReader 가 fieldnames=None."""
    with pytest.raises(ValueError, match="헤더"):
        parse_csv("", batch_id="b-1")


def test_default_mode_propagates_to_items() -> None:
    """batch.mode 가 item.mode 로 상속."""
    csv_text = "keyword\nkw1\nkw2\n"
    created, _, _ = parse_csv(csv_text, batch_id="b-1", default_mode="overnight")
    assert all(it.mode == "overnight" for it in created)
