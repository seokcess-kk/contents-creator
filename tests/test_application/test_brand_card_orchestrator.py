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
    """Phase 2.5: render_card_set — 통합 흐름 검증 (renderer/image_gen mock)."""

    def _approved_plan(self, plan_id: str = "p-1") -> BrandCardPlan:
        return BrandCardPlan(
            id=plan_id,
            brand_id="b-1",
            keyword="kw",
            strategy="trust_first",
            expression_level="balanced",
            template_id="clinic_trust",
            angle="...",
            blocks=[
                CardBlock(
                    card_type="hero",
                    headline="제목 1",
                    recommended_position="after_intro",
                ),
                CardBlock(
                    card_type="problem",
                    headline="고민 2",
                    recommended_position="after_problem",
                ),
            ],
            reuse_group_id="g-1",
            status="approved",
        )

    def test_no_plans_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from domain.brand_card.model import BrandCardError

        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = []
        monkeypatch.setattr(orch, "storage", mock_storage)
        with pytest.raises(BrandCardError, match="plan 없음"):
            orch.render_card_set("g-missing")

    def test_no_approved_plans_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from domain.brand_card.model import BrandCardError

        draft = self._approved_plan()
        draft.status = "draft"  # type: ignore[misc]
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [draft]
        monkeypatch.setattr(orch, "storage", mock_storage)
        with pytest.raises(BrandCardError, match="approved"):
            orch.render_card_set("g-1")

    def test_renders_each_block_and_writes_manifest(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        from pathlib import Path  # noqa: N814

        plan = self._approved_plan()
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [plan]
        monkeypatch.setattr(orch, "storage", mock_storage)

        # renderer mock — 호출 시 PNG 파일 생성 흉내
        def fake_render(**kwargs: object) -> Path:
            output = kwargs["output_path"]
            assert isinstance(output, Path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"\x89PNG fake")
            return output

        mock_renderer = MagicMock()
        mock_renderer.render_card_to_png.side_effect = fake_render
        mock_renderer.RenderContext = orch.renderer.RenderContext
        monkeypatch.setattr(orch, "renderer", mock_renderer)

        # image prefetch mock — AI 이미지 없는 케이스 (모든 block 이 image_asset_id 도 없음)
        monkeypatch.setattr(
            orch,
            "_prefetch_ai_images",
            lambda plans, **k: {p.id or "": {} for p in plans},
        )

        result = orch.render_card_set(
            "g-1",
            output_root=Path(str(tmp_path)),
            brand_name="대구한의원",
        )

        # 2 block × 1 plan = 2 PNG 호출
        assert mock_renderer.render_card_to_png.call_count == 2
        assert len(result.cards) == 2
        # variant_idx 가 1, 2 로 부여됨
        assert {c.variant_idx for c in result.cards} == {1, 2}
        # manifest 파일 작성됨
        assert result.manifest_path.exists()
        # status 전이 호출 — approved → published
        mock_storage.update_card_status.assert_called_with("p-1", status="published")

    def test_filename_pattern(self, monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
        """SPEC §3 파일명: card-{template_id}-{strategy}-{NN}.png."""
        from pathlib import Path  # noqa: N814

        plan = self._approved_plan()
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [plan]
        monkeypatch.setattr(orch, "storage", mock_storage)
        captured: list[Path] = []

        def fake_render(**kwargs: object) -> Path:
            output = kwargs["output_path"]
            assert isinstance(output, Path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"x")
            captured.append(output)
            return output

        mock_renderer = MagicMock()
        mock_renderer.render_card_to_png.side_effect = fake_render
        mock_renderer.RenderContext = orch.renderer.RenderContext
        monkeypatch.setattr(orch, "renderer", mock_renderer)
        monkeypatch.setattr(
            orch,
            "_prefetch_ai_images",
            lambda plans, **k: {p.id or "": {} for p in plans},
        )

        orch.render_card_set("g-1", output_root=Path(str(tmp_path)), brand_name="b")
        names = [p.name for p in captured]
        assert "card-clinic_trust-trust_first-01.png" in names
        assert "card-clinic_trust-trust_first-02.png" in names
