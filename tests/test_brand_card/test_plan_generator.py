"""plan_generator — 프롬프트 빌더 + tool_use 응답 파싱 단위 테스트.

LLM 호출 자체는 mock 으로 격리. 실제 Anthropic 호출은 통합 테스트에서.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from domain.brand_card.asset_merge import MergedAssets
from domain.brand_card.model import BrandCardPlan
from domain.brand_card.plan_generator import (
    PlanGenerationError,
    _build_system_prompt,
    _build_tool_schema,
    _build_user_prompt,
    _extract_tool_input,
    _format_assets,
    _format_compliance_rules,
    _format_expression_guide,
    _format_reuse_constraints,
    _parse_plan,
    generate_brand_card_plan,
)
from domain.brand_card.reuse_guard import ReuseCheckResult


class TestSystemPrompt:
    def test_includes_brand_lenient_rules(self) -> None:
        prompt = _build_system_prompt("balanced")
        assert "BRAND_LENIENT" in prompt
        # 9 룰 중 최소 한 개 description 포함
        assert "효과 보장" in prompt or "전후" in prompt or "최고" in prompt

    def test_includes_expression_level(self) -> None:
        prompt = _build_system_prompt("hooking")
        assert "hooking" in prompt
        assert "후킹" in prompt or "공감" in prompt

    def test_safe_level_guide_safer(self) -> None:
        safe = _build_system_prompt("safe")
        hooking = _build_system_prompt("hooking")
        assert "안정적" in safe
        assert "자극" in hooking or "공감" in hooking

    def test_tool_use_enforcement(self) -> None:
        prompt = _build_system_prompt("balanced")
        assert "submit_brand_card_plan" in prompt
        assert "tool" in prompt.lower()


class TestComplianceRulesFormat:
    def test_lists_brand_lenient_rules(self) -> None:
        text = _format_compliance_rules()
        # 9 종 모두 bullet 으로 시작
        assert text.count("- ") >= 9

    def test_omits_first_person_promotion(self) -> None:
        """BRAND_LENIENT 는 1인칭 허용 — first_person_promotion 룰 제외."""
        text = _format_compliance_rules()
        assert "1인칭" not in text or "홍보" not in text  # 룰 description 미포함


class TestExpressionGuide:
    @pytest.mark.parametrize("level", ["safe", "balanced", "hooking"])
    def test_all_levels_have_guide(self, level: str) -> None:
        guide = _format_expression_guide(level)
        assert len(guide) > 10  # 비어 있지 않음


class TestUserPrompt:
    def test_includes_keyword_strategy_template(self) -> None:
        prompt = _build_user_prompt(
            keyword="다이어트한의원",
            strategy="trust_first",
            template_id="clinic_trust",
            expression_level="balanced",
            merged_assets=MergedAssets(),
            reuse_check=ReuseCheckResult(),
        )
        assert "다이어트한의원" in prompt
        assert "trust_first" in prompt
        assert "clinic_trust" in prompt

    def test_empty_assets_marked_explicitly(self) -> None:
        prompt = _build_user_prompt(
            keyword="kw",
            strategy="trust_first",
            template_id="clinic_trust",
            expression_level="balanced",
            merged_assets=MergedAssets(),
            reuse_check=ReuseCheckResult(),
        )
        assert "[자산 없음" in prompt

    def test_user_brief_priority_one_label(self) -> None:
        prompt = _build_user_prompt(
            keyword="kw",
            strategy="trust_first",
            template_id="clinic_trust",
            expression_level="balanced",
            merged_assets=MergedAssets(user_brief="강조: 체질 분석"),
            reuse_check=ReuseCheckResult(),
        )
        assert "1순위" in prompt
        assert "체질 분석" in prompt


class TestAssetsFormatting:
    def test_required_and_forbidden_phrases_listed(self) -> None:
        m = MergedAssets(
            required_phrases=["대구 동성로", "한약 처방"],
            forbidden_phrases=["100% 보장"],
        )
        text = _format_assets(m)
        assert "대구 동성로" in text
        assert "100% 보장" in text


class TestReuseConstraints:
    def test_blocked_headlines_listed(self) -> None:
        rc = ReuseCheckResult(blocked_headlines={"기존 A", "기존 B"})
        text = _format_reuse_constraints(rc, MergedAssets())
        assert "차단된 헤드라인" in text
        assert "기존 A" in text
        assert "기존 B" in text

    def test_template_warning_listed(self) -> None:
        rc = ReuseCheckResult(warning_template_id="clinic_trust")
        text = _format_reuse_constraints(rc, MergedAssets())
        assert "clinic_trust" in text
        assert "5회" in text or "경고" in text

    def test_no_constraints_marked(self) -> None:
        text = _format_reuse_constraints(ReuseCheckResult(), MergedAssets())
        assert "없음" in text


class TestToolSchema:
    def test_tool_name_correct(self) -> None:
        schema = _build_tool_schema()
        assert schema["name"] == "submit_brand_card_plan"

    def test_blocks_required_4_to_6(self) -> None:
        schema = _build_tool_schema()
        blocks_schema = schema["input_schema"]["properties"]["blocks"]
        assert blocks_schema["minItems"] == 4
        assert blocks_schema["maxItems"] == 6

    def test_card_type_enum_six_values(self) -> None:
        schema = _build_tool_schema()
        block_props = schema["input_schema"]["properties"]["blocks"]["items"]["properties"]
        enum_values = block_props["card_type"]["enum"]
        assert set(enum_values) == {
            "hero",
            "problem",
            "solution",
            "differentiator",
            "process",
            "trust_closing",
        }


class TestExtractToolInput:
    def _response(self, content: list[Any], stop_reason: str = "tool_use") -> Any:
        return SimpleNamespace(content=content, stop_reason=stop_reason)

    def test_extracts_matching_tool_use(self) -> None:
        from anthropic.types import ToolUseBlock

        block = ToolUseBlock(
            id="t-1",
            name="submit_brand_card_plan",
            input={"angle": "test", "blocks": []},
            type="tool_use",
        )
        response = self._response([block])
        result = _extract_tool_input(response)
        assert result == {"angle": "test", "blocks": []}

    def test_raises_when_no_tool_use(self) -> None:
        response = self._response([], stop_reason="end_turn")
        with pytest.raises(PlanGenerationError, match="tool_use"):
            _extract_tool_input(response)

    def test_ignores_other_tool_names(self) -> None:
        from anthropic.types import ToolUseBlock

        block = ToolUseBlock(id="t-1", name="other_tool", input={}, type="tool_use")
        response = self._response([block])
        with pytest.raises(PlanGenerationError):
            _extract_tool_input(response)


class TestParsePlan:
    def _valid_input(self) -> dict[str, Any]:
        return {
            "angle": "체질부터 보는 관리",
            "blocks": [
                {
                    "card_type": "hero",
                    "headline": "체질 분석부터 시작",
                    "subcopy": "맞춤 처방",
                    "bullets": [],
                    "recommended_position": "after_intro",
                },
                {
                    "card_type": "differentiator",
                    "headline": "차별점 3가지",
                    "bullets": ["A", "B", "C"],
                    "recommended_position": "mid",
                },
            ],
            "required_phrases_used": ["대구 동성로"],
            "forbidden_phrases_avoided": ["100% 보장"],
        }

    def test_parses_full_plan(self) -> None:
        plan = _parse_plan(
            self._valid_input(),
            brand_id="b-1",
            keyword="kw",
            strategy="trust_first",
            expression_level="balanced",
            template_id="clinic_trust",
            reuse_group_id="g-1",
        )
        assert isinstance(plan, BrandCardPlan)
        assert plan.brand_id == "b-1"
        assert plan.angle == "체질부터 보는 관리"
        assert len(plan.blocks) == 2
        assert plan.status == "draft"
        assert plan.reuse_group_id == "g-1"
        assert plan.required_phrases_used == ["대구 동성로"]

    def test_missing_angle_raises(self) -> None:
        bad = self._valid_input()
        del bad["angle"]
        with pytest.raises(PlanGenerationError):
            _parse_plan(
                bad,
                brand_id="b-1",
                keyword="kw",
                strategy="trust_first",
                expression_level="balanced",
                template_id="clinic_trust",
                reuse_group_id=None,
            )

    def test_missing_blocks_raises(self) -> None:
        bad = self._valid_input()
        del bad["blocks"]
        with pytest.raises(PlanGenerationError):
            _parse_plan(
                bad,
                brand_id="b-1",
                keyword="kw",
                strategy="trust_first",
                expression_level="balanced",
                template_id="clinic_trust",
                reuse_group_id=None,
            )


class TestGenerateBrandCardPlanIntegration:
    """generate_brand_card_plan — LLM 호출은 mock, end-to-end 흐름만 검증."""

    def test_happy_path_returns_plan(self) -> None:
        from anthropic.types import ToolUseBlock

        fake_block = ToolUseBlock(
            id="t-1",
            name="submit_brand_card_plan",
            input={
                "angle": "체질부터 보는 관리",
                "blocks": [
                    {
                        "card_type": "hero",
                        "headline": "맞춤 관리",
                        "recommended_position": "after_intro",
                    }
                    for _ in range(4)
                ],
                "required_phrases_used": [],
                "forbidden_phrases_avoided": [],
            },
            type="tool_use",
        )
        fake_response = SimpleNamespace(
            content=[fake_block],
            stop_reason="tool_use",
            usage=SimpleNamespace(input_tokens=100, output_tokens=200),
        )

        with (
            patch(
                "domain.brand_card.plan_generator.messages_create_with_retry",
                return_value=fake_response,
            ),
            patch("domain.brand_card.plan_generator.build_client"),
            patch("domain.brand_card.plan_generator.record_usage"),
        ):
            plan = generate_brand_card_plan(
                brand_id="b-1",
                keyword="다이어트한의원",
                strategy="trust_first",
                expression_level="balanced",
                template_id="clinic_trust",
                merged_assets=MergedAssets(),
                reuse_check=ReuseCheckResult(),
            )

        assert isinstance(plan, BrandCardPlan)
        assert plan.brand_id == "b-1"
        assert plan.keyword == "다이어트한의원"
        assert plan.strategy == "trust_first"
        assert len(plan.blocks) == 4
        assert plan.status == "draft"
