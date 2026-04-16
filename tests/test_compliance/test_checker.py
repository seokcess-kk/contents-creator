"""checker.py 테스트 — regex 1차 + LLM mock 2차."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from domain.compliance.checker import (
    _check_regex,
    _extract_snippet,
    _merge_violations,
    check_compliance,
)
from domain.compliance.model import Violation
from domain.compliance.rules import CompliancePolicy, ViolationCategory


class TestCheckRegex:
    """regex 기반 1차 스크리닝."""

    def test_detects_absolute_guarantee(self) -> None:
        text = "이 치료는 100% 효과가 있습니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.ABSOLUTE_GUARANTEE.value in cats

    def test_detects_superlative(self) -> None:
        text = "최고의 치료를 제공합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.UNIQUE_SUPERLATIVE.value in cats

    def test_detects_first_person_strict(self) -> None:
        text = "저희 병원에서 진료합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.FIRST_PERSON_PROMOTION.value in cats

    def test_first_person_allowed_in_lenient(self) -> None:
        text = "저희 병원에서 진료합니다."
        violations = _check_regex(text, CompliancePolicy.BRAND_LENIENT)
        cats = [v.category for v in violations]
        assert ViolationCategory.FIRST_PERSON_PROMOTION.value not in cats

    def test_clean_text_no_violations(self) -> None:
        text = "한의원에서는 체질 분석을 통해 맞춤 관리를 진행합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        assert len(violations) == 0

    def test_multiple_violations_in_one_text(self) -> None:
        text = "저희 병원은 최고의 시설로 100% 완치를 보장합니다."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = {v.category for v in violations}
        assert len(cats) >= 3  # first_person, superlative, guarantee, cure

    def test_before_after_detection(self) -> None:
        text = "시술 전후 사진을 확인하세요."
        violations = _check_regex(text, CompliancePolicy.SEO_STRICT)
        cats = [v.category for v in violations]
        assert ViolationCategory.BEFORE_AFTER.value in cats


class TestExtractSnippet:
    """snippet 추출 컨텍스트."""

    def test_short_text(self) -> None:
        text = "abc"
        snippet = _extract_snippet(text, 0, 3)
        assert snippet == "abc"

    def test_context_window(self) -> None:
        text = "A" * 100 + "위반" + "B" * 100
        snippet = _extract_snippet(text, 100, 102)
        assert "위반" in snippet
        assert len(snippet) <= 104  # 50+2+50


class TestMergeViolations:
    """regex + LLM 결과 병합."""

    def test_deduplicates(self) -> None:
        v1 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과를 보장합니다 이 치료",
            severity="high",
            reason="regex",
        )
        v2 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과를 보장합니다 이 치료",
            severity="medium",
            reason="llm",
        )
        merged = _merge_violations([v1], [v2])
        assert len(merged) == 1

    def test_keeps_different_snippets(self) -> None:
        v1 = Violation(
            category="absolute_guarantee",
            text_snippet="100% 효과",
            severity="high",
            reason="regex",
        )
        v2 = Violation(
            category="cure_promise",
            text_snippet="완치가 가능합니다",
            severity="medium",
            reason="llm",
        )
        merged = _merge_violations([v1], [v2])
        assert len(merged) == 2


class TestCheckComplianceIntegration:
    """check_compliance 통합 (LLM mock)."""

    @patch("domain.compliance.checker._check_llm")
    def test_combines_regex_and_llm(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = [
            Violation(
                category="cure_promise",
                text_snippet="암시적 완치 뉘앙스가 있습니다",
                severity="medium",
                reason="LLM 감지",
            ),
        ]
        text = "이 치료는 100% 효과가 있고 완전히 나을 수 있습니다."
        violations = check_compliance(text, CompliancePolicy.SEO_STRICT)
        # regex 가 잡는 것 + LLM 이 잡는 것
        assert len(violations) >= 2
        cats = {v.category for v in violations}
        assert "absolute_guarantee" in cats
        assert "cure_promise" in cats

    @patch("domain.compliance.checker._check_llm")
    def test_clean_text_passes(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = []
        text = "체질에 맞는 관리 방법을 선택하는 것이 중요합니다."
        violations = check_compliance(text, CompliancePolicy.SEO_STRICT)
        assert len(violations) == 0
