"""SPEC-BRAND-CARD R3 게이트 — BRAND_LENIENT 가 §7 항상 차단 9종을 모두 차단하는지 회귀.

§7 항상 차단 9종 (SPEC-BRAND-CARD.md):
1. 효과 보장 → ABSOLUTE_GUARANTEE
2. 수치 감량 → PATIENT_TESTIMONIAL
3. 최고/유일/1위 → UNIQUE_SUPERLATIVE
4. 전후 비교 → BEFORE_AFTER
5. 환자 후기 → PATIENT_TESTIMONIAL
6. 타 병원 비교 → DIRECT_COMPARISON
7. 부작용 없음 → NO_SIDE_EFFECTS_CLAIM
8. 가격 할인 과장 → PRICE_DISCOUNT_HYPE
9. 검증되지 않은 의료진 경력/인증 → UNVERIFIED_CREDENTIAL

BRAND_LENIENT 는 SEO_STRICT 의 부분집합 (FIRST_PERSON_PROMOTION 만 제외).
LLM 호출 없이 regex 패턴 매칭으로 차단 여부만 검증한다.
"""

from __future__ import annotations

import pytest

from domain.compliance.rules import (
    CompliancePolicy,
    ViolationCategory,
    get_all_patterns,
)


def _matches(text: str, expected_category: ViolationCategory) -> bool:
    """BRAND_LENIENT 패턴이 text 에서 expected_category 위반을 잡으면 True."""
    for category, pattern in get_all_patterns(CompliancePolicy.BRAND_LENIENT):
        if category != expected_category:
            continue
        if pattern.search(text) is not None:
            return True
    return False


class TestSection7AlwaysBlocked:
    """SPEC-BRAND-CARD §7 항상 차단 9종 회귀 게이트."""

    @pytest.mark.parametrize(
        "text",
        [
            "이 시술은 100% 효과를 보장합니다",
            "반드시 효과를 봅니다",
            "확실한 효과가 있어요",
        ],
    )
    def test_1_absolute_guarantee_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.ABSOLUTE_GUARANTEE)

    @pytest.mark.parametrize(
        "text",
        [
            "한 달 만에 7kg 빠졌어요",
            "허리가 5cm 줄었습니다",
        ],
    )
    def test_2_numeric_reduction_blocked(self, text: str) -> None:
        # 수치 감량은 PATIENT_TESTIMONIAL 카테고리에서 차단
        assert _matches(text, ViolationCategory.PATIENT_TESTIMONIAL)

    @pytest.mark.parametrize(
        "text",
        [
            "지역 최고의 한의원입니다",
            "유일한 비법",
            "전국 1등 클리닉",
        ],
    )
    def test_3_unique_superlative_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.UNIQUE_SUPERLATIVE)

    @pytest.mark.parametrize(
        "text",
        [
            "시술 전후 사진 공개",
            "Before/After 비교",
            "비포 애프터로 확인하세요",
        ],
    )
    def test_4_before_after_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.BEFORE_AFTER)

    @pytest.mark.parametrize(
        "text",
        [
            "완전 나았어요",
            "효과 봤어요 정말 좋아요",
        ],
    )
    def test_5_patient_testimonial_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.PATIENT_TESTIMONIAL)

    @pytest.mark.parametrize(
        "text",
        [
            "타 병원과 달리 차별화된 시술",
            "다른 곳은 흉내 낼 수 없는 노하우",
            "여타 의료기관과는 다른 접근",
            "근처 병원보다 빠른 회복",
        ],
    )
    def test_6_direct_comparison_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.DIRECT_COMPARISON)

    @pytest.mark.parametrize(
        "text",
        [
            "부작용 없는 안전한 치료",
            "부작용 걱정 없이 받으세요",
            "안전성 100% 보장",
            "안전 보장",
        ],
    )
    def test_7_no_side_effects_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.NO_SIDE_EFFECTS_CLAIM)

    @pytest.mark.parametrize(
        "text",
        [
            "70% 할인 진행 중",
            "단 하루 특별 할인",
            "최저가 보장",
            "반값 이벤트",
        ],
    )
    def test_8_price_discount_hype_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.PRICE_DISCOUNT_HYPE)

    @pytest.mark.parametrize(
        "text",
        [
            "세계 1위 의료진",
            "Best Doctor 인증",
            "세계 최초 시술",
        ],
    )
    def test_9_unverified_credential_blocked(self, text: str) -> None:
        assert _matches(text, ViolationCategory.UNVERIFIED_CREDENTIAL)


class TestBrandLenientExcludesFirstPerson:
    """BRAND_LENIENT 는 1인칭 promotion 만 SEO_STRICT 에서 제외한다."""

    def test_first_person_not_in_brand_lenient(self) -> None:
        """`FIRST_PERSON_PROMOTION` 카테고리는 BRAND_LENIENT 에 포함되지 않는다."""
        categories = {cat for cat, _ in get_all_patterns(CompliancePolicy.BRAND_LENIENT)}
        assert ViolationCategory.FIRST_PERSON_PROMOTION not in categories

    def test_first_person_text_passes_brand_lenient(self) -> None:
        """'저희 한의원'·'예약하세요' 같은 1인칭 표현은 BRAND_LENIENT 에서 통과해야 한다."""
        for text in ["저희 한의원에 오세요", "지금 예약하세요", "전화주세요"]:
            assert not _matches(text, ViolationCategory.FIRST_PERSON_PROMOTION)


class TestBrandLenientIsSubsetOfStrict:
    """BRAND_LENIENT 카테고리는 SEO_STRICT 의 부분집합이어야 한다."""

    def test_lenient_subset_of_strict(self) -> None:
        strict_cats = {cat for cat, _ in get_all_patterns(CompliancePolicy.SEO_STRICT)}
        lenient_cats = {cat for cat, _ in get_all_patterns(CompliancePolicy.BRAND_LENIENT)}
        assert lenient_cats.issubset(strict_cats)

    def test_only_first_person_excluded(self) -> None:
        strict_cats = {cat for cat, _ in get_all_patterns(CompliancePolicy.SEO_STRICT)}
        lenient_cats = {cat for cat, _ in get_all_patterns(CompliancePolicy.BRAND_LENIENT)}
        diff = strict_cats - lenient_cats
        assert diff == {ViolationCategory.FIRST_PERSON_PROMOTION}
