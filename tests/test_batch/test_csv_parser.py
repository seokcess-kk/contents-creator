"""CSV → KeywordBatchItem 변환 + 검증 테스트."""

from __future__ import annotations

import pytest

from domain.batch.csv_parser import build_csv_template, parse_csv


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


def test_blog_resolver_resolves_alias_and_id() -> None:
    """blog 컬럼이 별칭 또는 네이버 blog_id 와 매칭되면 blog_channel_id 채움."""
    fake_table = {"메인블로그": "ch-1", "myblog123": "ch-2"}

    def resolver(raw: str) -> str | None:
        return fake_table.get(raw.strip().lower())

    csv_text = "keyword,blog\nkw1,메인블로그\nkw2,myblog123\nkw3,unknown_alias\nkw4,\n"
    created, _, _ = parse_csv(csv_text, batch_id="b-1", blog_resolver=resolver)
    assert created[0].blog_channel_id == "ch-1"
    assert created[1].blog_channel_id == "ch-2"
    # 미일치는 None + warning (테스트는 None 검증만)
    assert created[2].blog_channel_id is None
    # 빈 문자열은 lookup 자체 skip
    assert created[3].blog_channel_id is None


def test_blog_resolver_none_means_no_lookup() -> None:
    """blog_resolver=None 이면 blog 컬럼이 있어도 blog_channel_id=None."""
    csv_text = "keyword,blog\nkw1,메인블로그\n"
    created, _, _ = parse_csv(csv_text, batch_id="b-1", blog_resolver=None)
    assert created[0].blog_channel_id is None


def test_template_roundtrips_through_parser() -> None:
    """build_csv_template 출력이 parse_csv 로 그대로 round-trip 되어야 한다.

    헤더·예시 행이 컬럼 추가/이름 변경으로 어긋나면 운영자가 받은 템플릿이
    바로 failed 로 떨어지는 사고를 회귀 방지.
    """
    template = build_csv_template(with_bom=True)
    # BOM 은 운영자 도구(Excel)용. parse_csv 는 BOM 없는 입력을 가정하므로 strip.
    template_no_bom = template.lstrip("﻿")
    created, skipped, failed = parse_csv(template_no_bom, batch_id="b-tpl")

    assert failed == [], f"템플릿이 parser 검증을 통과해야 함: {failed}"
    assert skipped == []
    # 안내 예시 2행이 모두 created 로 들어와야 함
    assert len(created) == 2
    assert all(it.operation == "pipeline" for it in created)
    # 두 예시 행은 priority 5, 3 이어야 함 (template 의 안내 예시 정의)
    priorities = sorted(it.priority for it in created)
    assert priorities == [3, 5]


def test_template_has_bom_for_excel_compatibility() -> None:
    """Windows Excel 한글 깨짐 방지를 위해 BOM 부착이 default."""
    assert build_csv_template().startswith("﻿")
    assert not build_csv_template(with_bom=False).startswith("﻿")
