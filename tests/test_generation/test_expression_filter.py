"""표현 필터 테스트."""

from __future__ import annotations

from domain.generation.expression_filter import count_cliches, filter_expressions


class TestFilterExpressions:
    def test_detects_importance_cliche(self) -> None:
        text = "피부 관리를 하는 것이 중요합니다."
        filtered, detected = filter_expressions(text)
        assert len(detected) > 0

    def test_detects_explore_cliche(self) -> None:
        text = "오늘은 여드름에 대해 알아보겠습니다."
        filtered, detected = filter_expressions(text)
        assert len(detected) > 0

    def test_clean_text_unchanged(self) -> None:
        text = "피부 관리의 핵심은 보습입니다."
        filtered, detected = filter_expressions(text)
        assert len(detected) == 0
        assert filtered == text

    def test_replaces_recommendation(self) -> None:
        text = "전문의 상담을 받는 것을 추천드립니다."
        filtered, detected = filter_expressions(text)
        assert "추천드립니다" not in filtered or len(detected) > 0


class TestCountCliches:
    def test_counts_multiple(self) -> None:
        text = "하는 것이 중요합니다. 에 대해 알아보겠습니다. 추천드립니다."
        assert count_cliches(text) >= 2

    def test_zero_for_clean(self) -> None:
        assert count_cliches("깨끗한 텍스트입니다.") == 0
