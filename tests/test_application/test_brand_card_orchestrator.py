"""brand_card_orchestrator — generate_card_plan 통합 테스트.

storage / plan_generator / asset_merge / reuse_guard 호출 흐름 검증.
실제 LLM/Supabase 호출은 mock.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application import brand_card_orchestrator as orch
from domain.brand_card.model import (
    BrandCardError,
    BrandCardPlan,
    CardBlock,
    StatusTransitionError,
)
from domain.compliance.model import ComplianceReport, Violation


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


@pytest.fixture
def compliance_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """기본: 위반 없음 — plan 그대로 echo, ComplianceReport(passed=True)."""
    mock = MagicMock()
    mock.validate_brand_card_plan.side_effect = lambda p, **kw: (
        p,
        ComplianceReport(passed=True, iterations=0, final_text=""),
    )
    monkeypatch.setattr(orch, "bc_compliance", mock)
    return mock


class TestGenerateCardPlan:
    def test_generates_n_variants_with_different_strategies(
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
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
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
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
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
    ) -> None:
        with pytest.raises(ValueError, match="strategy_count"):
            orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=0)
        with pytest.raises(ValueError, match="strategy_count"):
            orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=5)

    def test_strategy_template_mapping(
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
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
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
    ) -> None:
        plan_gen_mock.generate_brand_card_plan.side_effect = [
            _plan("trust_first"),
            _plan("empathy_first"),
        ]

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=2)

        assert storage_mock.insert_card_plan.call_count == 2


class TestApproveAndReject:
    def test_approve_transitions_draft_to_approved(self) -> None:
        draft = _plan()
        with (
            patch.object(orch.storage, "get_card_plan", return_value=draft),
            patch.object(orch.storage, "update_card_status") as upd,
        ):
            orch.approve_plan("plan-1")
            upd.assert_called_once_with("plan-1", status="approved")

    def test_reject_transitions_draft_to_rejected(self) -> None:
        draft = _plan()
        with (
            patch.object(orch.storage, "get_card_plan", return_value=draft),
            patch.object(orch.storage, "update_card_status") as upd,
        ):
            orch.reject_plan("plan-1")
            upd.assert_called_once_with("plan-1", status="rejected")

    def test_approve_invalid_transition_raises(self) -> None:
        """이미 published 인 plan 은 approved 로 되돌릴 수 없다."""
        published = _plan()
        published.status = "published"  # type: ignore[misc]
        with (
            patch.object(orch.storage, "get_card_plan", return_value=published),
            pytest.raises(StatusTransitionError),
        ):
            orch.approve_plan("plan-1")

    def test_reject_idempotent_on_same_status(self) -> None:
        """rejected 인 plan 을 다시 reject 해도 raise 하지 않는다."""
        rejected = _plan()
        rejected.status = "rejected"  # type: ignore[misc]
        with (
            patch.object(orch.storage, "get_card_plan", return_value=rejected),
            patch.object(orch.storage, "update_card_status") as upd,
        ):
            orch.reject_plan("plan-1")
            upd.assert_called_once_with("plan-1", status="rejected")

    def test_approve_missing_plan_returns_none(self) -> None:
        with patch.object(orch.storage, "get_card_plan", return_value=None):
            assert orch.approve_plan("plan-1") is None


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

    @staticmethod
    def _install_clean_compliance(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        mock = MagicMock()
        mock.validate_brand_card_plan.side_effect = lambda p, **kw: (
            p,
            ComplianceReport(passed=True, iterations=0, final_text=""),
        )
        monkeypatch.setattr(orch, "bc_compliance", mock)
        return mock

    def test_no_plans_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = []
        monkeypatch.setattr(orch, "storage", mock_storage)
        self._install_clean_compliance(monkeypatch)
        with pytest.raises(BrandCardError, match="plan 없음"):
            orch.render_card_set("g-missing")

    def test_no_approved_plans_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        draft = self._approved_plan()
        draft.status = "draft"  # type: ignore[misc]
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [draft]
        monkeypatch.setattr(orch, "storage", mock_storage)
        self._install_clean_compliance(monkeypatch)
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
        self._install_clean_compliance(monkeypatch)

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
        # status 전이 호출 — approved → published, compliance_report 함께 전달
        update_call = mock_storage.update_card_status.call_args
        assert update_call.args[0] == "p-1"
        assert update_call.kwargs["status"] == "published"
        assert update_call.kwargs.get("compliance_report") is not None

    def test_filename_pattern(self, monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
        """SPEC §3 파일명: card-{template_id}-{strategy}-{NN}.png."""
        from pathlib import Path  # noqa: N814

        plan = self._approved_plan()
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [plan]
        monkeypatch.setattr(orch, "storage", mock_storage)
        self._install_clean_compliance(monkeypatch)
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


class TestPhase3Compliance:
    """Phase 3: generate / render 흐름의 compliance 통합 검증."""

    def test_generate_invokes_compliance_per_plan(
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
    ) -> None:
        """plan_generator → compliance.validate_brand_card_plan → storage.insert 순."""
        plan_gen_mock.generate_brand_card_plan.side_effect = [
            _plan("trust_first"),
            _plan("empathy_first"),
        ]

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=2)

        assert compliance_mock.validate_brand_card_plan.call_count == 2
        # storage.insert_card_plan 도 2회 호출 (compliance 통과 후)
        assert storage_mock.insert_card_plan.call_count == 2

    def test_generate_persists_compliance_report_in_summary(
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
    ) -> None:
        """compliance_report 가 source_summary 에 병합되어 storage 로 전달된다."""
        plan_gen_mock.generate_brand_card_plan.return_value = _plan("trust_first")

        report = ComplianceReport(
            passed=True,
            iterations=1,
            violations=[],
            final_text="fixed",
        )
        compliance_mock.validate_brand_card_plan.side_effect = lambda p, **kw: (p, report)

        orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=1)

        inserted = storage_mock.insert_card_plan.call_args.args[0]
        summary = inserted.source_summary
        assert "compliance_report" in summary
        assert summary["compliance_report"]["passed"] is True
        assert summary["compliance_report"]["iterations"] == 1

    def test_generate_keeps_draft_status_on_violation(
        self,
        storage_mock: MagicMock,
        plan_gen_mock: MagicMock,
        compliance_mock: MagicMock,
    ) -> None:
        """compliance 가 fail 해도 plan 은 draft 로 저장 — 사용자 판단 위임."""
        plan_gen_mock.generate_brand_card_plan.return_value = _plan("trust_first")
        failed_report = ComplianceReport(
            passed=False,
            iterations=2,
            violations=[
                Violation(
                    category="absolute_guarantee",
                    text_snippet="100%",
                    severity="high",
                    reason="잔존",
                ),
            ],
        )
        compliance_mock.validate_brand_card_plan.side_effect = lambda p, **kw: (p, failed_report)

        plans = orch.generate_card_plan(brand_id="b-1", keyword="kw", strategy_count=1)

        assert plans[0].status == "draft"  # rejected 자동 전환 안 함
        inserted = storage_mock.insert_card_plan.call_args.args[0]
        assert inserted.source_summary["compliance_report"]["passed"] is False

    def test_render_propagates_compliance_report_to_card(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        """RenderedBrandCard.compliance_report 에 실 검증 결과 반영."""
        from pathlib import Path  # noqa: N814

        plan = TestRenderCardSet()._approved_plan()
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [plan]
        monkeypatch.setattr(orch, "storage", mock_storage)

        report = ComplianceReport(
            passed=True,
            iterations=0,
            violations=[],
            final_text="ok",
        )
        compliance = MagicMock()
        compliance.validate_brand_card_plan.side_effect = lambda p, **kw: (p, report)
        monkeypatch.setattr(orch, "bc_compliance", compliance)

        def fake_render(**kwargs: Any) -> Path:
            output = kwargs["output_path"]
            assert isinstance(output, Path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"\x89PNG")
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

        result = orch.render_card_set(
            "g-1",
            output_root=Path(str(tmp_path)),
            brand_name="b",
        )

        for card in result.cards:
            assert card.compliance_report["passed"] is True
            assert card.compliance_report["iterations"] == 0

    def test_render_publishes_via_status_transition(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        """approved → published 전이는 assert_status_transition 통과해야 한다."""
        from pathlib import Path  # noqa: N814

        plan = TestRenderCardSet()._approved_plan()
        mock_storage = MagicMock()
        mock_storage.list_cards_by_reuse_group.return_value = [plan]
        monkeypatch.setattr(orch, "storage", mock_storage)

        compliance = MagicMock()
        compliance.validate_brand_card_plan.side_effect = lambda p, **kw: (
            p,
            ComplianceReport(passed=True, iterations=0, final_text=""),
        )
        monkeypatch.setattr(orch, "bc_compliance", compliance)

        def fake_render(**kwargs: Any) -> Path:
            output = kwargs["output_path"]
            assert isinstance(output, Path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"\x89PNG")
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

        orch.render_card_set(
            "g-1",
            output_root=Path(str(tmp_path)),
            brand_name="b",
        )
        # 정상 전이 — update_card_status 호출 발생
        assert mock_storage.update_card_status.called
