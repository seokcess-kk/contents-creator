"""rules.py 테스트 — 상수, enum, regex 매칭, 정책 프로필."""

from __future__ import annotations

import re

import pytest

from domain.compliance.rules import (
    FORBIDDEN_LITERALS,
    RULES,
    CompliancePolicy,
    Rule,
    ViolationCategory,
    build_pre_generation_injection,
    get_all_patterns,
    get_rules,
    get_safe_alternatives,
)


class TestViolationCategory:
    """ViolationCategory enum 이 정확히 8개 멤버를 가진다."""

    def test_has_8_categories(self) -> None:
        assert len(ViolationCategory) == 8

    def test_category_values(self) -> None:
        expected = {
            "absolute_guarantee",
            "unique_superlative",
            "direct_comparison",
            "before_after",
            "cure_promise",
            "patient_testimonial",
            "unverified_credential",
            "first_person_promotion",
        }
        actual = {c.value for c in ViolationCategory}
        assert actual == expected


class TestCompliancePolicy:
    """CompliancePolicy 가 두 프로필을 가진다."""

    def test_has_two_profiles(self) -> None:
        assert len(CompliancePolicy) == 2

    def test_seo_strict_exists(self) -> None:
        assert CompliancePolicy.SEO_STRICT.value == "seo_strict"

    def test_brand_lenient_exists(self) -> None:
        assert CompliancePolicy.BRAND_LENIENT.value == "brand_lenient"


class TestRulesMapping:
    """RULES dict 이 두 프로필 모두 매핑한다."""

    def test_seo_strict_has_8_rules(self) -> None:
        rules = RULES[CompliancePolicy.SEO_STRICT]
        assert len(rules) == 8

    def test_brand_lenient_has_7_rules(self) -> None:
        rules = RULES[CompliancePolicy.BRAND_LENIENT]
        assert len(rules) == 7

    def test_brand_lenient_excludes_first_person(self) -> None:
        rules = RULES[CompliancePolicy.BRAND_LENIENT]
        categories = {r.category for r in rules}
        assert ViolationCategory.FIRST_PERSON_PROMOTION not in categories

    def test_all_rules_are_rule_instances(self) -> None:
        for policy in CompliancePolicy:
            for rule in RULES[policy]:
                assert isinstance(rule, Rule)

    def test_all_rules_have_patterns(self) -> None:
        for policy in CompliancePolicy:
            for rule in RULES[policy]:
                assert len(rule.patterns) > 0

    def test_all_rules_have_safe_alternatives(self) -> None:
        for policy in CompliancePolicy:
            for rule in RULES[policy]:
                assert len(rule.safe_alternatives) > 0


class TestRegexPatterns:
    """각 카테고리의 regex 가 예상 텍스트를 매칭한다."""

    @pytest.mark.parametrize(
        "text,expected_category",
        [
            ("100% 효과 보장", ViolationCategory.ABSOLUTE_GUARANTEE),
            ("반드시 좋아집니다", ViolationCategory.ABSOLUTE_GUARANTEE),
            ("확실한 효과를 보입니다", ViolationCategory.ABSOLUTE_GUARANTEE),
            ("최고의 치료", ViolationCategory.UNIQUE_SUPERLATIVE),
            ("유일한 방법", ViolationCategory.UNIQUE_SUPERLATIVE),
            ("독보적인 기술", ViolationCategory.UNIQUE_SUPERLATIVE),
            ("타 병원과 달리", ViolationCategory.DIRECT_COMPARISON),
            ("다른 곳은 못 합니다", ViolationCategory.DIRECT_COMPARISON),
            ("시술 전후 변화", ViolationCategory.BEFORE_AFTER),
            ("Before / After", ViolationCategory.BEFORE_AFTER),
            ("비포 애프터", ViolationCategory.BEFORE_AFTER),
            ("완치 됩니다", ViolationCategory.CURE_PROMISE),
            ("재발 없는", ViolationCategory.CURE_PROMISE),
            ("평생 효과", ViolationCategory.CURE_PROMISE),
            ("10kg 빠졌어요", ViolationCategory.PATIENT_TESTIMONIAL),
            ("효과 봤어요", ViolationCategory.PATIENT_TESTIMONIAL),
            ("세계 1위", ViolationCategory.UNVERIFIED_CREDENTIAL),
            ("Best Doctor 선정", ViolationCategory.UNVERIFIED_CREDENTIAL),
            ("저희 병원에서는", ViolationCategory.FIRST_PERSON_PROMOTION),
            ("예약하세요", ViolationCategory.FIRST_PERSON_PROMOTION),
            ("상담 받으세요", ViolationCategory.FIRST_PERSON_PROMOTION),
        ],
    )
    def test_pattern_matches(self, text: str, expected_category: ViolationCategory) -> None:
        patterns = get_all_patterns(CompliancePolicy.SEO_STRICT)
        matched = False
        for category, compiled in patterns:
            if category == expected_category and compiled.search(text):
                matched = True
                break
        assert matched, f"'{text}' should match {expected_category.value}"

    def test_safe_text_no_match(self) -> None:
        """안전한 텍스트는 어떤 패턴에도 매칭되지 않는다."""
        safe_texts = [
            "개선이 기대됩니다",
            "개인차가 있을 수 있습니다",
            "전문적인 관리를 받을 수 있습니다",
            "장기적 관리가 필요합니다",
        ]
        patterns = get_all_patterns(CompliancePolicy.SEO_STRICT)
        for text in safe_texts:
            for _, compiled in patterns:
                assert not compiled.search(text), f"Safe text '{text}' should not match"


class TestGetFunctions:
    """get_rules, get_all_patterns, get_safe_alternatives 동작."""

    def test_get_rules_default_is_strict(self) -> None:
        rules = get_rules()
        assert len(rules) == 8

    def test_get_all_patterns_returns_compiled(self) -> None:
        patterns = get_all_patterns()
        assert len(patterns) > 0
        for cat, pat in patterns:
            assert isinstance(cat, ViolationCategory)
            assert isinstance(pat, re.Pattern)

    def test_get_safe_alternatives_known_category(self) -> None:
        alts = get_safe_alternatives(ViolationCategory.ABSOLUTE_GUARANTEE)
        assert len(alts) > 0

    def test_get_safe_alternatives_unknown_returns_empty(self) -> None:
        # brand_lenient 에서 first_person 을 조회하면 빈 리스트
        alts = get_safe_alternatives(
            ViolationCategory.FIRST_PERSON_PROMOTION,
            CompliancePolicy.BRAND_LENIENT,
        )
        assert alts == []


class TestBuildPreGenerationInjection:
    """build_pre_generation_injection 이 유효한 문자열을 반환한다."""

    def test_returns_nonempty_string(self) -> None:
        result = build_pre_generation_injection()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_all_categories(self) -> None:
        result = build_pre_generation_injection()
        for rule in get_rules():
            assert rule.description in result


class TestForbiddenLiterals:
    """FORBIDDEN_LITERALS 가 유효하다."""

    def test_nonempty(self) -> None:
        assert len(FORBIDDEN_LITERALS) > 0

    def test_all_strings(self) -> None:
        for lit in FORBIDDEN_LITERALS:
            assert isinstance(lit, str)
            assert len(lit) >= 2
