"""fixer.py 테스트 — 구절 치환, M2 도입부 보호."""

from __future__ import annotations

from domain.compliance.fixer import (
    _find_violation_paragraph,
    _is_intro_violation,
    _try_phrase_replacement,
    fix_violations,
)
from domain.compliance.model import Violation
from domain.compliance.rules import CompliancePolicy, ViolationCategory


class TestPhraseReplacement:
    """구절 치환 — 기본 수정 경로."""

    def test_replaces_guarantee_expression(self) -> None:
        text = "이 시술은 100% 효과를 보여줍니다."
        violation = Violation(
            category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
            text_snippet="100% 효과",
            severity="high",
            reason="효과 보장",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "100%" not in fixed
        assert entry.rule == ViolationCategory.ABSOLUTE_GUARANTEE.value

    def test_replaces_superlative(self) -> None:
        text = "최고의 의료 서비스를 제공합니다."
        violation = Violation(
            category=ViolationCategory.UNIQUE_SUPERLATIVE.value,
            text_snippet="최고의 의료",
            severity="high",
            reason="비교 우위",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "최고" not in fixed

    def test_replaces_first_person(self) -> None:
        text = "저희 병원은 최선을 다합니다."
        violation = Violation(
            category=ViolationCategory.FIRST_PERSON_PROMOTION.value,
            text_snippet="저희 병원",
            severity="high",
            reason="1인칭",
        )
        fixed, entry = _try_phrase_replacement(text, violation, CompliancePolicy.SEO_STRICT)
        assert entry is not None
        assert "저희 병원" not in fixed


class TestFindViolationParagraph:
    """위반 문단 탐색."""

    def test_finds_paragraph_with_double_newline(self) -> None:
        text = "첫 문단입니다.\n\n위반 표현이 있는 문단입니다.\n\n마지막 문단."
        violation = Violation(
            category="test",
            text_snippet="위반 표현이 있는 문단",
            severity="high",
            reason="test",
        )
        para = _find_violation_paragraph(text, violation)
        assert para is not None
        assert "위반 표현" in para

    def test_returns_none_for_missing_snippet(self) -> None:
        text = "안전한 텍스트입니다."
        violation = Violation(
            category="test",
            text_snippet="존재하지 않는 표현",
            severity="high",
            reason="test",
        )
        para = _find_violation_paragraph(text, violation)
        assert para is None


class TestIsIntroViolation:
    """도입부 위반 판단."""

    def test_section_index_1_is_intro(self) -> None:
        text = "도입부 텍스트.\n\n본문 텍스트."
        violation = Violation(
            category="test",
            text_snippet="도입부 텍스트",
            section_index=1,
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is True

    def test_section_index_3_not_intro(self) -> None:
        text = "도입부 텍스트.\n\n본문 텍스트.\n\n세 번째 문단."
        violation = Violation(
            category="test",
            text_snippet="세 번째 문단",
            section_index=3,
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is False

    def test_first_paragraph_detection(self) -> None:
        text = "도입부에 100% 표현.\n\n본문에 내용."
        violation = Violation(
            category="test",
            text_snippet="도입부에 100% 표현",
            severity="high",
            reason="test",
        )
        assert _is_intro_violation(text, violation) is True


class TestFixViolations:
    """fix_violations 통합 테스트."""

    def test_fixes_single_violation(self) -> None:
        text = "이 시술은 100% 효과적입니다."
        violations = [
            Violation(
                category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
                text_snippet="100% 효과",
                severity="high",
                reason="효과 보장",
            ),
        ]
        fixed, changelog = fix_violations(text, violations, CompliancePolicy.SEO_STRICT)
        assert "100%" not in fixed
        assert len(changelog) >= 1

    def test_fixes_multiple_violations(self) -> None:
        text = "최고의 시술로 100% 효과를 냅니다."
        violations = [
            Violation(
                category=ViolationCategory.UNIQUE_SUPERLATIVE.value,
                text_snippet="최고의 시술",
                severity="high",
                reason="비교 우위",
            ),
            Violation(
                category=ViolationCategory.ABSOLUTE_GUARANTEE.value,
                text_snippet="100% 효과",
                severity="high",
                reason="효과 보장",
            ),
        ]
        fixed, changelog = fix_violations(text, violations, CompliancePolicy.SEO_STRICT)
        assert "최고" not in fixed
        assert "100%" not in fixed

    def test_protect_intro_skips_regeneration(self) -> None:
        """도입부(첫 문단) 위반 시 치환만 시도하고 재생성 안 함."""
        text = "도입부에 완치 가능합니다.\n\n본문 내용."
        violations = [
            Violation(
                category=ViolationCategory.CURE_PROMISE.value,
                text_snippet="도입부에 완치 가능합니다",
                section_index=1,
                severity="high",
                reason="치료 확정",
            ),
        ]
        # 구절 치환이 성공하므로 재생성 폴백은 호출되지 않음
        fixed, changelog = fix_violations(
            text, violations, CompliancePolicy.SEO_STRICT, protect_intro=True
        )
        assert "완치" not in fixed
        assert len(changelog) >= 1

    def test_empty_violations_returns_original(self) -> None:
        text = "안전한 텍스트입니다."
        fixed, changelog = fix_violations(text, [])
        assert fixed == text
        assert len(changelog) == 0
