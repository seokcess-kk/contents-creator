"""brand_card/compliance — BRAND_LENIENT 검증·수정 wrapper 단위 테스트.

domain/compliance.checker LLM 호출은 mock 으로 격리.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from domain.brand_card.compliance import (
    MAX_FIX_ITERATIONS,
    validate_brand_card_plan,
)
from domain.brand_card.model import BrandCardPlan, CardBlock
from domain.compliance.model import Violation


def _make_block(
    *,
    headline: str = "안전한 헤드라인입니다",
    subcopy: str | None = "신뢰할 수 있는 정보를 전달합니다",
    bullets: list[str] | None = None,
    ai_image_prompt: str | None = None,
    card_type: str = "hero",
) -> CardBlock:
    return CardBlock(
        card_type=card_type,
        headline=headline,
        subcopy=subcopy,
        bullets=bullets if bullets is not None else ["기본 불릿"],
        ai_image_prompt=ai_image_prompt,
        recommended_position="after_intro",
    )


def _make_plan(
    *,
    blocks: list[CardBlock] | None = None,
    angle: str = "신뢰형 카드",
    expression_level: str = "balanced",
    plan_id: str | None = "plan-1",
) -> BrandCardPlan:
    return BrandCardPlan(
        id=plan_id,
        brand_id="brand-1",
        keyword="다이어트 한약",
        strategy="trust_first",
        expression_level=expression_level,
        template_id="clinic_trust",
        angle=angle,
        blocks=blocks if blocks is not None else [_make_block()],
        status="draft",
    )


class TestValidatePlan:
    """전체 검증·수정 흐름."""

    def test_clean_plan_passes_without_changes(self) -> None:
        plan = _make_plan()
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            fixed, report = validate_brand_card_plan(plan)
        assert report.passed is True
        assert report.iterations == 0
        assert report.violations == []
        assert fixed.blocks[0].headline == plan.blocks[0].headline

    def test_violation_replaced_with_safe_alternative(self) -> None:
        """보장 표현이 안전 대체어로 치환된다."""
        block = _make_block(headline="100% 보장하는 효과")
        plan = _make_plan(blocks=[block])

        # 첫 호출은 위반 보고, 두 번째는 통과 (치환 후 재검증).
        check_calls: list[Any] = []

        def fake_check(text: str, **kwargs: Any) -> list[Violation]:
            check_calls.append(text)
            if "100" in text or "보장" in text:
                return [
                    Violation(
                        category="absolute_guarantee",
                        text_snippet=text[:80],
                        severity="high",
                        reason="보장 표현 감지",
                    ),
                ]
            return []

        with patch(
            "domain.brand_card.compliance.check_compliance",
            side_effect=fake_check,
        ):
            fixed, report = validate_brand_card_plan(plan)

        assert report.passed is True
        assert report.iterations >= 1
        assert "100" not in fixed.blocks[0].headline
        assert "보장" not in fixed.blocks[0].headline
        assert len(report.changelog) >= 1
        assert report.changelog[0].rule == "absolute_guarantee"

    def test_fix_failure_returns_failed_report(self) -> None:
        """치환 후에도 위반 잔존 시 max iter 도달, passed=False."""
        block = _make_block(headline="안전 헤드라인")
        plan = _make_plan(blocks=[block])

        violation = Violation(
            category="absolute_guarantee",
            text_snippet="안전 헤드라인",
            severity="high",
            reason="LLM 가짜 위반 (replacement 불가)",
        )

        # 항상 위반 보고하지만 patterns 이 본문과 매칭되지 않아 changelog 비어 있음 → break.
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[violation],
        ):
            fixed, report = validate_brand_card_plan(plan)

        assert report.passed is False
        assert report.violations
        assert report.iterations == 0  # changelog 없으면 즉시 break
        assert fixed.blocks[0].headline == "안전 헤드라인"

    def test_iterations_capped_at_max(self) -> None:
        """check 가 매번 새 위반을 만들어도 max_iterations 까지만 반복."""
        block = _make_block(headline="100% 보장 표현 안내")
        plan = _make_plan(blocks=[block])

        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[
                Violation(
                    category="absolute_guarantee",
                    text_snippet="100% 보장",
                    severity="high",
                    reason="잔존",
                ),
            ],
        ):
            _, report = validate_brand_card_plan(plan)

        # 2회 시도까지 진행 (replacement 가능한 한 매 iteration 시도)
        assert report.iterations <= MAX_FIX_ITERATIONS

    def test_unknown_category_skipped(self) -> None:
        """LLM 이 정의되지 않은 카테고리를 보내도 crash 하지 않는다."""
        plan = _make_plan(blocks=[_make_block(headline="100% 보장 표현")])
        unknown_violation = Violation(
            category="invented_category",
            text_snippet="100%",
            severity="high",
            reason="LLM 환각",
        )

        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[unknown_violation],
        ):
            _, report = validate_brand_card_plan(plan)

        # 알려지지 않은 카테고리는 phrase replacement 제외 → changelog 없음 → 즉시 break
        assert report.passed is False
        assert report.iterations == 0


class TestImagePromptValidation:
    """ai_image_prompt 보조 검증 — 위반 시 None 으로 비운다."""

    def test_invalid_prompt_emptied(self) -> None:
        block = _make_block(
            ai_image_prompt="patient face",  # 'no text' 없고 patient 키워드
        )
        plan = _make_plan(blocks=[block])
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            fixed, report = validate_brand_card_plan(plan)
        assert fixed.blocks[0].ai_image_prompt is None
        assert any(entry.rule == "image_prompt_validation" for entry in report.changelog)

    def test_valid_prompt_kept(self) -> None:
        block = _make_block(
            ai_image_prompt="abstract herbal illustration, no text, soft pastel",
        )
        plan = _make_plan(blocks=[block])
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            fixed, report = validate_brand_card_plan(plan)
        assert fixed.blocks[0].ai_image_prompt is not None
        assert all(entry.rule != "image_prompt_validation" for entry in report.changelog)


class TestExpressionLevel:
    """expression_level=safe 추가 경고 — hooking 표현 발견 시 changelog 기록."""

    def test_safe_flags_hooking_phrase(self) -> None:
        block = _make_block(headline="실패했다면 다시 시작해보세요")
        plan = _make_plan(blocks=[block], expression_level="safe")
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            fixed, report = validate_brand_card_plan(plan)
        # 텍스트는 수정 안 함
        assert "실패했다면" in fixed.blocks[0].headline
        # changelog 에 expression_level_safe 기록
        assert any(entry.rule == "expression_level_safe" for entry in report.changelog)
        # passed 자체는 violations 만으로 판단 — 경고는 영향 없음
        assert report.passed is True

    def test_balanced_does_not_flag_hooking(self) -> None:
        block = _make_block(headline="실패했다면 다시 시작해보세요")
        plan = _make_plan(blocks=[block], expression_level="balanced")
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            _, report = validate_brand_card_plan(plan)
        assert all(entry.rule != "expression_level_safe" for entry in report.changelog)

    def test_hooking_does_not_flag_hooking(self) -> None:
        block = _make_block(headline="혼자 버티기 어렵다면")
        plan = _make_plan(blocks=[block], expression_level="hooking")
        with patch(
            "domain.brand_card.compliance.check_compliance",
            return_value=[],
        ):
            _, report = validate_brand_card_plan(plan)
        assert all(entry.rule != "expression_level_safe" for entry in report.changelog)


class TestMultiBlock:
    """다중 블록 — 각 블록의 텍스트 필드 모두 적용."""

    def test_violation_in_subcopy_replaced(self) -> None:
        block = _make_block(
            headline="안전한 헤드라인",
            subcopy="100% 보장 효과를 약속드립니다",
        )
        plan = _make_plan(blocks=[block])

        def fake_check(text: str, **kwargs: Any) -> list[Violation]:
            if "100" in text or "보장" in text:
                return [
                    Violation(
                        category="absolute_guarantee",
                        text_snippet=text[:80],
                        severity="high",
                        reason="보장 표현",
                    ),
                ]
            return []

        with patch(
            "domain.brand_card.compliance.check_compliance",
            side_effect=fake_check,
        ):
            fixed, report = validate_brand_card_plan(plan)

        assert report.passed is True
        assert "100" not in (fixed.blocks[0].subcopy or "")
        assert "보장" not in (fixed.blocks[0].subcopy or "")

    def test_violation_in_bullets_replaced(self) -> None:
        block = _make_block(
            bullets=["전후 사진으로 확인", "안전한 시술"],
        )
        plan = _make_plan(blocks=[block])

        def fake_check(text: str, **kwargs: Any) -> list[Violation]:
            if "전후" in text:
                return [
                    Violation(
                        category="before_after",
                        text_snippet=text[:80],
                        severity="high",
                        reason="전후 비교",
                    ),
                ]
            return []

        with patch(
            "domain.brand_card.compliance.check_compliance",
            side_effect=fake_check,
        ):
            fixed, report = validate_brand_card_plan(plan)

        assert report.passed is True
        joined = " ".join(fixed.blocks[0].bullets)
        assert "전후" not in joined


class TestFinalText:
    """ComplianceReport.final_text 는 수정 후 직렬화 결과."""

    def test_final_text_reflects_fixes(self) -> None:
        block = _make_block(headline="100% 보장 효과")
        plan = _make_plan(blocks=[block])

        def fake_check(text: str, **kwargs: Any) -> list[Violation]:
            if "100" in text or "보장" in text:
                return [
                    Violation(
                        category="absolute_guarantee",
                        text_snippet=text[:80],
                        severity="high",
                        reason="보장 표현",
                    ),
                ]
            return []

        with patch(
            "domain.brand_card.compliance.check_compliance",
            side_effect=fake_check,
        ):
            _, report = validate_brand_card_plan(plan)

        assert "100" not in report.final_text
        assert "보장" not in report.final_text


@pytest.mark.parametrize(
    "current,target,allowed",
    [
        ("draft", "approved", True),
        ("draft", "reviewed", True),
        ("draft", "rejected", True),
        ("draft", "published", False),  # approved 거치지 않음
        ("draft", "archived", False),
        ("reviewed", "approved", True),
        ("reviewed", "rejected", True),
        ("reviewed", "draft", False),
        ("approved", "published", True),
        ("approved", "rejected", True),
        ("approved", "draft", False),
        ("published", "archived", True),
        ("published", "draft", False),
        ("rejected", "draft", False),  # 종결
        ("rejected", "approved", False),
        ("archived", "draft", False),  # 종결
        ("draft", "draft", True),  # idempotent
    ],
)
class TestStatusTransition:
    def test_transition_matrix(
        self,
        current: str,
        target: str,
        allowed: bool,
    ) -> None:
        from domain.brand_card.model import (
            StatusTransitionError,
            assert_status_transition,
        )

        if allowed:
            assert_status_transition(current, target)
        else:
            with pytest.raises(StatusTransitionError):
                assert_status_transition(current, target)


def test_unknown_current_status_raises() -> None:
    from domain.brand_card.model import (
        StatusTransitionError,
        assert_status_transition,
    )

    with pytest.raises(StatusTransitionError, match="알 수 없는"):
        assert_status_transition("invalid_status", "approved")
