"""reuse_guard — 차단/경고 룰 + override 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from domain.brand_card.model import BrandCardPlan, CardBlock, ReuseGuardError
from domain.brand_card.reuse_guard import ReuseCheckResult, check_reuse


def _plan(
    *,
    keyword: str = "다이어트한의원",
    headline: str = "체질부터 보는 관리",
    template_id: str = "clinic_trust",
    strategy: str = "trust_first",
    image_asset_id: str | None = None,
    days_ago: int = 1,
) -> BrandCardPlan:
    """테스트용 plan factory — 단일 block."""
    return BrandCardPlan(
        brand_id="b-1",
        keyword=keyword,
        strategy=strategy,
        expression_level="balanced",
        template_id=template_id,
        angle="...",
        blocks=[
            CardBlock(
                card_type="hero",
                headline=headline,
                image_asset_id=image_asset_id,
                recommended_position="after_intro",
            )
        ],
        created_at=datetime.now(tz=UTC) - timedelta(days=days_ago),
    )


class TestHeadlineBlocking:
    def test_unique_headline_passes(self) -> None:
        result = check_reuse(
            candidate_headlines=["새로운 접근법"],
            recent_plans=[_plan(headline="기존 헤드라인")],
        )
        assert result.blocked_headlines == set()

    def test_duplicate_headline_partial_blocked(self) -> None:
        """후보 일부만 차단 — blocked_headlines 에 표시되되 raise 는 안 함."""
        result = check_reuse(
            candidate_headlines=["체질부터 보는 관리", "신규 헤드"],
            recent_plans=[_plan(headline="체질부터 보는 관리")],
        )
        assert "체질부터 보는 관리" in result.blocked_headlines
        assert "신규 헤드" not in result.blocked_headlines

    def test_all_candidates_blocked_raises_without_override(self) -> None:
        with pytest.raises(ReuseGuardError, match="30일"):
            check_reuse(
                candidate_headlines=["A 헤드라인", "B 헤드라인"],
                recent_plans=[
                    _plan(headline="A 헤드라인"),
                    _plan(headline="B 헤드라인"),
                ],
            )

    def test_override_allows_blocked_headlines(self) -> None:
        """allow_override=True 면 raise 안 하고 blocked_headlines 비어서 반환."""
        result = check_reuse(
            candidate_headlines=["A 헤드라인", "B 헤드라인"],
            recent_plans=[
                _plan(headline="A 헤드라인"),
                _plan(headline="B 헤드라인"),
            ],
            allow_override=True,
        )
        assert result.blocked_headlines == set()  # override 시 차단 약화

    def test_partial_block_does_not_raise(self) -> None:
        """후보 일부만 차단 — 나머지로 진행 가능."""
        result = check_reuse(
            candidate_headlines=["기존", "신규 A", "신규 B"],
            recent_plans=[_plan(headline="기존")],
        )
        assert result.blocked_headlines == {"기존"}


class TestTemplateOveruse:
    def test_below_threshold_no_warning(self) -> None:
        plans = [_plan(template_id="clinic_trust") for _ in range(4)]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert result.warning_template_id is None

    def test_five_consecutive_template_triggers_warning(self) -> None:
        plans = [_plan(template_id="clinic_trust") for _ in range(5)]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert result.warning_template_id == "clinic_trust"

    def test_mixed_templates_no_warning(self) -> None:
        plans = [
            _plan(template_id="clinic_trust"),
            _plan(template_id="diet_empathy"),
            _plan(template_id="clinic_trust"),
            _plan(template_id="process_guide"),
            _plan(template_id="clinic_trust"),
        ]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert result.warning_template_id is None


class TestStrategyOveruse:
    def test_five_same_strategy_warns(self) -> None:
        plans = [_plan(strategy="trust_first") for _ in range(5)]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert result.warning_strategy == "trust_first"


class TestPhotoOveruse:
    def test_same_photo_three_keywords_warns(self) -> None:
        """연속 3 키워드 모두 같은 의료진 사진 사용 → 경고."""
        plans = [
            _plan(keyword="대구다이어트한의원", image_asset_id="m-doctor-A"),
            _plan(keyword="다이어트한의원추천", image_asset_id="m-doctor-A"),
            _plan(keyword="동성로다이어트", image_asset_id="m-doctor-A"),
        ]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert "m-doctor-A" in result.warning_overused_photo_ids

    def test_different_photos_per_keyword_no_warning(self) -> None:
        plans = [
            _plan(keyword="키워드A", image_asset_id="m-doctor-A"),
            _plan(keyword="키워드B", image_asset_id="m-doctor-B"),
            _plan(keyword="키워드C", image_asset_id="m-doctor-C"),
        ]
        result = check_reuse(
            candidate_headlines=["unique"],
            recent_plans=plans,
        )
        assert result.warning_overused_photo_ids == set()


class TestHasWarningsProperty:
    def test_no_warnings_false(self) -> None:
        result = ReuseCheckResult()
        assert result.has_warnings is False

    def test_with_template_warning_true(self) -> None:
        result = ReuseCheckResult(warning_template_id="clinic_trust")
        assert result.has_warnings is True
