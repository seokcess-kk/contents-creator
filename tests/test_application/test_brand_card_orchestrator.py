"""brand_card_orchestrator — generate_card_plan 통합 테스트.

storage / plan_generator / asset_merge / reuse_guard 호출 흐름 검증.
실제 LLM/Supabase 호출은 mock.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from application import brand_card_orchestrator as orch
from domain.brand_card.model import BrandCardPlan, CardBlock


def _plan(strategy: str = "trust_first", template_id: str = "clinic_trust") -> BrandCardPlan:
    return BrandCardPlan(
        id=f"plan-{strategy}",
        brand_id="b-1",
        keyword="다이어트한의원",
        strategy=strategy,
        expression_level="balanced",
        template_id=template_id,
        angle="...",
        blocks=[
            CardBlock(
                card_type="hero",
                headline=f"{strategy} 헤드",
                recommended_position="after_intro",
            )
        ],
    )


@pytest.fixture
def storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.get_latest_campaign_input.return_value = None
    mock.get_message_sources_by_ids.return_value = []
    mock.list_message_sources.return_value = []
    mock.list_recent_cards_for_brand.return_value = []
    mock.insert_card_plan.side_effect = lambda p: p  # echo
    monkeypatch.setattr(orch, "storage", mock)
    return mock


@pytest.fixture
def plan_gen_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(orch, "plan_generator", mock)
    return mock


class TestGenerateCardPlan:
    def test_generates_n_variants_with_different_strategies(
        self, storage_mock: MagicMock, plan_gen_mock: MagicMock
    ) -> None:
        plan_gen_mock.generate_brand_card_plan.side_effect = [
            _plan("trust_first"),
            _plan("empathy_first"),
            _plan("process_first"),
        ]

        plans = orch.generate_card_plan(brand_id="b-1", keyword="다이어트한의원", strategy_count=3)

        assert len(plans) == 3
        strategies = [p.strategy for p in plans]
        assert strategies == ["trust_first", "empathy_first", "process_first"]
        # plan_generator 가 3 번 호출되며 각 호출에 다른 strategy 전달
        assert plan_gen_mock.generate_brand_card_plan.call_count == 3

    def test_all_plans_share_reuse_group_id(
        self, storage_mock: MagicMock, plan_gen_mock: MagicMock
    ) -> None:
        """한 번의 호출 = 하나의 묶음."""
        plan_gen_mock.generate_brand_card_plan.side_effect = lambda **kwargs: _plan(
            strategy=kwargs["strategy"]
        )

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=2)

        calls = plan_gen_mock.generate_brand_card_plan.call_args_list
        group_ids = {c.kwargs["reuse_group_id"] for c in calls}
        assert len(group_ids) == 1  # 모든 호출이 같은 group_id 공유

    def test_invalid_strategy_count_raises(
        self, storage_mock: MagicMock, plan_gen_mock: MagicMock
    ) -> None:
        with pytest.raises(ValueError, match="strategy_count"):
            orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=0)
        with pytest.raises(ValueError, match="strategy_count"):
            orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=5)

    def test_strategy_template_mapping(
        self, storage_mock: MagicMock, plan_gen_mock: MagicMock
    ) -> None:
        """strategy → template_id 자동 매핑."""
        plan_gen_mock.generate_brand_card_plan.side_effect = lambda **kwargs: _plan(
            strategy=kwargs["strategy"], template_id=kwargs["template_id"]
        )

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=4)

        calls = plan_gen_mock.generate_brand_card_plan.call_args_list
        mapping = {c.kwargs["strategy"]: c.kwargs["template_id"] for c in calls}
        assert mapping == {
            "trust_first": "clinic_trust",
            "empathy_first": "diet_empathy",
            "process_first": "process_guide",
            "local_first": "local_info",
        }

    def test_each_plan_inserted_via_storage(
        self, storage_mock: MagicMock, plan_gen_mock: MagicMock
    ) -> None:
        plan_gen_mock.generate_brand_card_plan.side_effect = [
            _plan("trust_first"),
            _plan("empathy_first"),
        ]

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=2)

        assert storage_mock.insert_card_plan.call_count == 2


class TestApproveAndReject:
    def test_approve_calls_storage_update_status(self) -> None:
        with patch.object(orch.storage, "update_card_status") as upd:
            orch.approve_plan("plan-1")
            upd.assert_called_once_with("plan-1", status="approved")

    def test_reject_calls_storage_update_status(self) -> None:
        with patch.object(orch.storage, "update_card_status") as upd:
            orch.reject_plan("plan-1")
            upd.assert_called_once_with("plan-1", status="rejected")


class TestRenderCardSet:
    def test_not_implemented_phase_2_5(self) -> None:
        with pytest.raises(NotImplementedError, match="Phase 2.5"):
            orch.render_card_set("g-1")
