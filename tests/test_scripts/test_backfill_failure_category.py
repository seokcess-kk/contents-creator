"""backfill_failure_category.classify_row 정규식 매핑 테스트 (2026-05-14).

7종 enum 매핑 각각 + 매칭 불가 (EXCEPTION fallback) 케이스 검증. DB 호출은 없음.
"""

from __future__ import annotations

import pytest

from scripts.backfill_failure_category import classify_row


class TestClassifyRow:
    @pytest.mark.parametrize(
        ("error_text", "expected"),
        [
            # PREFILTER — _apply_prefilter 가 작성하는 메시지 형식
            ("prefilter: search_volume=50<100", "PREFILTER_VOLUME"),
            ("prefilter: search_volume=80<100, difficulty=HIGH>MEDIUM", "PREFILTER_VOLUME"),
            ("prefilter: difficulty=HIGH>MEDIUM", "PREFILTER_DIFFICULTY"),
            # SERP / SCRAPE — orchestrator 가 RuntimeError 로 wrap 한 후 _handle_item_failure 가
            # 'RuntimeError: ...' prefix 를 붙임.
            ("RuntimeError: serp: 4 pages collected, minimum 5 required", "SERP_INSUFFICIENT"),
            ("RuntimeError: scrape: 3 pages collected, minimum 5 required", "SCRAPE_INSUFFICIENT"),
            # InsufficientCollectionError 가 직접 raise 되는 경로 (배치 외부)
            ("serp: 6 pages collected, minimum 5 required", "SERP_INSUFFICIENT"),
            ("scrape: 2 pages collected, minimum 5 required", "SCRAPE_INSUFFICIENT"),
            # COMPLIANCE / BODY_SIMILARITY — 메시지 패턴
            ("RuntimeError: compliance fixer exhausted 2 attempts", "COMPLIANCE_FAILED"),
            ("의료법 위반 자동 수정 실패", "COMPLIANCE_FAILED"),
            ("RuntimeError: 본문_차별화_부족 jaccard=0.85", "BODY_SIMILARITY_HIGH"),
            # 매칭 불가 → EXCEPTION (catch-all)
            ("RuntimeError: Bright Data API timeout after 30s", "EXCEPTION"),
            ("ValueError: 알 수 없는 operation: unknown", "EXCEPTION"),
            ("", "EXCEPTION"),
        ],
    )
    def test_classify_by_error_text(self, error_text: str, expected: str) -> None:
        assert classify_row(error_text, []) == expected

    def test_violations_take_priority_over_error_text(self) -> None:
        # error 텍스트는 EXCEPTION 매칭이지만 violations 에 본문_차별화_부족 → BODY_SIMILARITY_HIGH.
        assert (
            classify_row(
                error_text="RuntimeError: 알 수 없는 에러",
                violations=["본문_차별화_부족", "허위_과장"],
            )
            == "BODY_SIMILARITY_HIGH"
        )

    def test_none_error_with_empty_violations_returns_exception(self) -> None:
        # error 가 사라진 row 도 일단 분류 — 운영자 사후 검토 대상.
        assert classify_row(None, []) == "EXCEPTION"

    def test_none_violations_treated_as_empty(self) -> None:
        # compliance_violations 컬럼이 NULL 인 구버전 row 도 graceful.
        assert classify_row("prefilter: search_volume=10<100", None) == "PREFILTER_VOLUME"
