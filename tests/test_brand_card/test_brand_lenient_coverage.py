"""Phase 1 검증 게이트 (R3): BRAND_LENIENT 룰이 SPEC §7 항상 차단 9종을 모두 catch 하는지 회귀.

SPEC-BRAND-CARD §7 항상 차단 (2026-04-28 결정 G1 옵션 A 적용 후 9/9 매핑):
1. 효과 보장 → ABSOLUTE_GUARANTEE
2. 수치 감량 → PATIENT_TESTIMONIAL
3. 최고/유일/1위 → UNIQUE_SUPERLATIVE
4. 전후 비교 → BEFORE_AFTER
5. 환자 후기 → PATIENT_TESTIMONIAL
6. 타 병원 비교 → DIRECT_COMPARISON
7. 부작용 없음 → NO_SIDE_EFFECTS_CLAIM (2026-04-28 신규)
8. 가격 할인 과장 → PRICE_DISCOUNT_HYPE (2026-04-28 신규)
9. 검증되지 않은 의료진 경력/인증 → UNVERIFIED_CREDENTIAL
"""

from __future__ import annotations

import pytest

from domain.compliance.rules import CompliancePolicy, get_rules


def _check_violations(text: str, policy: CompliancePolicy) -> list[str]:
    """text 가 정책 패턴에 매칭되는 카테고리 목록 반환."""
    import re

    matched: list[str] = []
    for rule in get_rules(policy):
        for pattern in rule.patterns:
            if re.search(pattern, text):
                matched.append(rule.category.value)
                break
    return matched


class TestBrandLenientCoverage:
    """SPEC §7 항상 차단 9종 vs RULES[BRAND_LENIENT] 매핑."""

    @pytest.mark.parametrize(
        "spec_label,trigger_text,expected_category",
        [
            ("§7 #1 효과 보장", "100% 보장합니다", "absolute_guarantee"),
            ("§7 #2 수치 감량", "한 달에 5kg 빠졌습니다", "patient_testimonial"),
            ("§7 #3 최고/유일/1위", "대구 최고의 한의원입니다", "unique_superlative"),
            ("§7 #4 전후 비교", "시술 전후 사진 보세요", "before_after"),
            ("§7 #5 환자 후기", "효과 봤어요 너무 좋아요", "patient_testimonial"),
            ("§7 #6 타 병원 비교", "다른 병원보다 효과적", "direct_comparison"),
            ("§7 #7 부작용 없음", "부작용 없는 안전한 시술", "no_side_effects_claim"),
            ("§7 #8 가격 할인", "단 하루 90% 할인 이벤트", "price_discount_hype"),
            ("§7 #9 미검증 자격", "Best Doctor 수상 경력", "unverified_credential"),
        ],
    )
    def test_covered_categories_caught(
        self,
        spec_label: str,
        trigger_text: str,
        expected_category: str,
    ) -> None:
        """SPEC §7 9종 모두 BRAND_LENIENT 로 차단됨 (G1 옵션 A 적용 후)."""
        matched = _check_violations(trigger_text, CompliancePolicy.BRAND_LENIENT)
        assert expected_category in matched, (
            f"{spec_label!r} 항목이 BRAND_LENIENT 로 차단되지 않음. matched={matched}"
        )

    def test_first_person_promotion_allowed_in_brand_lenient(self) -> None:
        """BRAND_LENIENT 는 SEO_STRICT 와 달리 1인칭 허용 (§8 정책 차이)."""
        text = "우리 한의원에서는 체질을 함께 봅니다. 상담 받으세요."
        seo = _check_violations(text, CompliancePolicy.SEO_STRICT)
        brand = _check_violations(text, CompliancePolicy.BRAND_LENIENT)
        assert "first_person_promotion" in seo, "SEO_STRICT 는 1인칭 차단"
        assert "first_person_promotion" not in brand, "BRAND_LENIENT 는 1인칭 허용"


class TestBrandLenientCounts:
    """카테고리 수 정합성 — SPEC §7 와 RULES 동기화 검증."""

    def test_brand_lenient_has_nine_rules(self) -> None:
        """BRAND_LENIENT 룰 9종 — SPEC §7 9종 모두 catch (1인칭 promotion 제외)."""
        rules = get_rules(CompliancePolicy.BRAND_LENIENT)
        assert len(rules) == 9, (
            f"BRAND_LENIENT 룰 수 변경 감지: {len(rules)} (예상 9). "
            "SPEC §7 또는 rules.py 갱신이 동기화되지 않은 가능성 — 본 테스트 갱신 필요."
        )

    def test_seo_strict_has_ten_rules(self) -> None:
        """SEO_STRICT 룰 10종 — BRAND_LENIENT 9종 + FIRST_PERSON_PROMOTION."""
        rules = get_rules(CompliancePolicy.SEO_STRICT)
        assert len(rules) == 10, f"SEO_STRICT 룰 수 변경 감지: {len(rules)} (예상 10)."
