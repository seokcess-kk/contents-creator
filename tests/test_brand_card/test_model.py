"""brand_card 도메인 모델 단위 테스트.

Phase 1 Day 1 — model.py 1:1 schema 매핑 검증.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.brand_card.model import (
    BrandCardError,
    BrandCardPlan,
    BrandCardStatus,
    BrandMessageSource,
    CardBlock,
    CardCampaignInput,
    CardStrategy,
    CardType,
    ExpressionLevel,
    MessageSourceType,
    RenderedBrandCard,
    RenderedCardSet,
    ReuseGuardError,
    TextOverflowError,
)


class TestEnums:
    def test_strategy_values(self) -> None:
        assert CardStrategy.TRUST_FIRST == "trust_first"
        assert CardStrategy.EMPATHY_FIRST == "empathy_first"
        assert CardStrategy.PROCESS_FIRST == "process_first"
        assert CardStrategy.LOCAL_FIRST == "local_first"
        # SPEC §5 P1 4종 정확히 4개
        assert len(list(CardStrategy)) == 4

    def test_expression_level_values(self) -> None:
        assert ExpressionLevel.SAFE == "safe"
        assert ExpressionLevel.BALANCED == "balanced"
        assert ExpressionLevel.HOOKING == "hooking"
        assert len(list(ExpressionLevel)) == 3

    def test_status_values(self) -> None:
        # SPEC §9 status 6종
        assert {s.value for s in BrandCardStatus} == {
            "draft",
            "reviewed",
            "approved",
            "rejected",
            "published",
            "archived",
        }

    def test_card_type_values(self) -> None:
        # SPEC §4 P1 6종
        assert {t.value for t in CardType} == {
            "hero",
            "problem",
            "solution",
            "differentiator",
            "process",
            "trust_closing",
        }

    def test_message_source_type_excludes_forbidden_phrases(self) -> None:
        """M5: card_campaign_inputs.forbidden_phrases 가 단일 출처 — source_type 에서 제거됨."""
        values = {t.value for t in MessageSourceType}
        assert "forbidden_phrases" not in values
        assert values == {"brand_common", "campaign", "keyword_specific", "reference"}


class TestBrandMessageSource:
    def test_minimum_construction(self) -> None:
        src = BrandMessageSource(brand_id="b-1", source_type="brand_common")
        assert src.brand_id == "b-1"
        assert src.source_type == "brand_common"
        assert src.content_summary == {}
        assert src.created_at is None  # DB 가 채움

    def test_with_file(self) -> None:
        src = BrandMessageSource(
            brand_id="b-1",
            source_type="campaign",
            file_name="brochure.pdf",
            file_path="/uploads/brand/b-1/brochure.pdf",
            content_text="브로슈어 본문",
        )
        assert src.file_name == "brochure.pdf"
        assert src.content_text == "브로슈어 본문"


class TestCardCampaignInput:
    def test_default_expression_level_is_balanced(self) -> None:
        ci = CardCampaignInput(brand_id="b-1", keyword="다이어트한의원")
        assert ci.expression_level == "balanced"
        assert ci.required_phrases == []
        assert ci.forbidden_phrases == []

    def test_with_required_and_forbidden(self) -> None:
        ci = CardCampaignInput(
            brand_id="b-1",
            keyword="대구다이어트병원",
            required_phrases=["대구 동성로", "한약 처방"],
            forbidden_phrases=["100% 보장"],
        )
        assert "대구 동성로" in ci.required_phrases
        assert "100% 보장" in ci.forbidden_phrases


class TestCardBlock:
    def test_either_image_asset_or_ai_prompt(self) -> None:
        # 실사 사진 사용
        b1 = CardBlock(
            card_type="trust_closing",
            headline="대구 다이어트 한의원",
            image_asset_id="m-1",
            recommended_position="before_closing",
        )
        assert b1.image_asset_id == "m-1"
        assert b1.ai_image_prompt is None

        # AI 이미지 사용
        b2 = CardBlock(
            card_type="problem",
            headline="식욕 조절이 어렵다면",
            ai_image_prompt="minimalist illustration of a balance scale",
            recommended_position="after_problem",
        )
        assert b2.ai_image_prompt is not None
        assert b2.image_asset_id is None

    def test_bullets_default_empty(self) -> None:
        b = CardBlock(
            card_type="differentiator",
            headline="차별점",
            recommended_position="mid",
        )
        assert b.bullets == []


class TestBrandCardPlan:
    def test_construction_with_blocks(self) -> None:
        plan = BrandCardPlan(
            brand_id="b-1",
            keyword="다이어트한의원",
            strategy="trust_first",
            expression_level="balanced",
            template_id="clinic_trust",
            angle="체질·생활 패턴 함께 보는 관리",
            blocks=[
                CardBlock(
                    card_type="hero",
                    headline="체질부터 보는 관리",
                    recommended_position="after_intro",
                ),
            ],
        )
        assert plan.status == "draft"
        assert len(plan.blocks) == 1

    def test_status_draft_is_default(self) -> None:
        plan = BrandCardPlan(
            brand_id="b-1",
            keyword="kw",
            strategy="empathy_first",
            expression_level="hooking",
            template_id="diet_empathy",
            angle="...",
            blocks=[],
        )
        assert plan.status == "draft"


class TestRenderedBrandCard:
    def test_construction_minimum(self) -> None:
        card = RenderedBrandCard(
            brand_id="b-1",
            keyword="다이어트",
            strategy="trust_first",
            expression_level="balanced",
            template_id="clinic_trust",
            variant_idx=1,
            png_path=Path("output/diet/2026-04-28/cards/card-clinic_trust-trust_first-01.png"),
            width_px=1080,
            height_px=1350,
        )
        assert card.status == "published"
        assert card.variant_idx == 1
        assert card.width_px == 1080

    def test_variant_idx_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            RenderedBrandCard(
                brand_id="b-1",
                keyword="kw",
                strategy="trust_first",
                expression_level="balanced",
                template_id="clinic_trust",
                variant_idx=0,  # invalid
                png_path=Path("x.png"),
                width_px=1080,
                height_px=1350,
            )

    def test_dimensions_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            RenderedBrandCard(
                brand_id="b-1",
                keyword="kw",
                strategy="trust_first",
                expression_level="balanced",
                template_id="clinic_trust",
                variant_idx=1,
                png_path=Path("x.png"),
                width_px=0,
                height_px=1350,
            )


class TestRenderedCardSet:
    def test_construction(self) -> None:
        card = RenderedBrandCard(
            brand_id="b-1",
            keyword="kw",
            strategy="trust_first",
            expression_level="balanced",
            template_id="clinic_trust",
            variant_idx=1,
            png_path=Path("a.png"),
            width_px=1080,
            height_px=1350,
        )
        s = RenderedCardSet(
            reuse_group_id="g-1",
            brand_id="b-1",
            keyword="kw",
            cards=[card],
            manifest_path=Path("cards-manifest.json"),
        )
        assert s.reuse_group_id == "g-1"
        assert len(s.cards) == 1


class TestExceptions:
    def test_text_overflow_inherits_brand_card_error(self) -> None:
        assert issubclass(TextOverflowError, BrandCardError)

    def test_reuse_guard_error_inherits_brand_card_error(self) -> None:
        assert issubclass(ReuseGuardError, BrandCardError)
