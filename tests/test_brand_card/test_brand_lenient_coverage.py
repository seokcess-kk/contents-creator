"""Phase 1 검증 게이트 (R3): BRAND_LENIENT 룰이 SPEC §7 항상 차단 9종을 모두 catch 하는지 회귀.

SPEC-BRAND-CARD §7 항상 차단:
1. 효과 보장
2. 수치 감량
3. 최고/유일/1위
4. 전후 비교
5. 환자 후기
6. 타 병원 비교
7. 부작용 없음                      ← 미매핑 (현재 갭)
8. 가격 할인 과장                   ← 미매핑 (현재 갭)
9. 검증되지 않은 의료진 경력/인증

7종은 기존 RULES[BRAND_LENIENT] 로 catch. 2종은 신규 카테고리 또는 패턴 추가
필요. CLAUDE.md "카테고리 임의 추가 금지" 룰에 따라 SPEC-BRAND-CARD §7 와
domain/compliance/rules.py 동시 수정 필요 (사용자 결정 게이트).
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
            ("효과 보장", "100% 보장합니다", "absolute_guarantee"),
            ("수치 감량", "한 달에 5kg 빠졌습니다", "patient_testimonial"),
            ("최고/유일/1위", "대구 최고의 한의원입니다", "unique_superlative"),
            ("전후 비교", "시술 전후 사진 보세요", "before_after"),
            ("환자 후기", "효과 봤어요 너무 좋아요", "patient_testimonial"),
            ("타 병원 비교", "다른 병원보다 효과적", "direct_comparison"),
            ("미검증 자격", "Best Doctor 수상 경력", "unverified_credential"),
        ],
    )
    def test_covered_categories_caught(
        self,
        spec_label: str,
        trigger_text: str,
        expected_category: str,
    ) -> None:
        """SPEC §7 9종 중 7종이 BRAND_LENIENT 로 차단됨."""
        matched = _check_violations(trigger_text, CompliancePolicy.BRAND_LENIENT)
        assert expected_category in matched, (
            f"§7 {spec_label!r} 항목이 BRAND_LENIENT 로 차단되지 않음. matched={matched}"
        )

    def test_first_person_promotion_allowed_in_brand_lenient(self) -> None:
        """BRAND_LENIENT 는 SEO_STRICT 와 달리 1인칭 허용 (§8 정책 차이)."""
        text = "우리 한의원에서는 체질을 함께 봅니다. 상담 받으세요."
        seo = _check_violations(text, CompliancePolicy.SEO_STRICT)
        brand = _check_violations(text, CompliancePolicy.BRAND_LENIENT)
        assert "first_person_promotion" in seo, "SEO_STRICT 는 1인칭 차단"
        assert "first_person_promotion" not in brand, "BRAND_LENIENT 는 1인칭 허용"


class TestBrandLenientGaps:
    """SPEC §7 9종 중 현재 미커버 2종 — SPEC-BRAND-CARD 와 rules.py 동기화 필요.

    이 테스트는 현재 갭을 명시적으로 마킹한다. 룰 추가 후 expected_failure 제거.
    """

    @pytest.mark.xfail(
        reason="SPEC §7 #7 '부작용 없음' 매핑 미완. 카테고리 추가 또는 "
        "ABSOLUTE_GUARANTEE 패턴 확장 필요 (사용자 결정 게이트)",
        strict=True,
    )
    def test_gap_no_side_effects_claim(self) -> None:
        text = "부작용 없음을 자신합니다"
        matched = _check_violations(text, CompliancePolicy.BRAND_LENIENT)
        assert len(matched) > 0, "SPEC §7 '부작용 없음' 미차단"

    @pytest.mark.xfail(
        reason="SPEC §7 #8 '가격 할인 과장' 매핑 미완. 카테고리 추가 필요 (사용자 결정 게이트)",
        strict=True,
    )
    def test_gap_price_discount_hype(self) -> None:
        text = "단 하루 90% 할인 이벤트"
        matched = _check_violations(text, CompliancePolicy.BRAND_LENIENT)
        assert len(matched) > 0, "SPEC §7 '가격 할인 과장' 미차단"

    def test_brand_lenient_has_seven_rules(self) -> None:
        """현재 BRAND_LENIENT 룰 7종 — §7 9종 vs 갭 2종 일치 검증."""
        rules = get_rules(CompliancePolicy.BRAND_LENIENT)
        # SPEC §7 항상 차단 9종 - 갭 2종 = 7종 catch 가능
        assert len(rules) == 7, (
            f"BRAND_LENIENT 룰 수 변경 감지: {len(rules)} (예상 7). "
            "SPEC §7 또는 rules.py 갱신이 동기화되지 않은 가능성 — 본 테스트 갱신 필요."
        )
