"""SPEC-BATCH Phase 2 PR2 — cluster 재사용 단위 테스트.

`_resolve_cluster_primary` 의 polling/대기/폴백 분기 + `_run_member_with_primary` 의
operation 별 재사용 분기. 모든 storage / orchestrator 호출은 mock 처리.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from application import batch_orchestrator
from application.models import GenerateResult, PipelineResult, StageStatus
from domain.batch.model import KeywordBatch, KeywordBatchItem


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "operation": "analyze",
        "cluster_id": "c-1",
        "cluster_role": "member",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def _batch(**overrides: object) -> KeywordBatch:
    base: dict[str, object] = {
        "id": "b-1",
        "total_count": 5,
        "cluster_dedupe": True,
    }
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


@pytest.fixture
def storage_mock() -> Any:
    with patch("application.batch_orchestrator.storage") as m:
        yield m


def _primary_succeeded() -> KeywordBatchItem:
    return KeywordBatchItem(
        id="i-primary",
        batch_id="b-1",
        keyword="primary-kw",
        cluster_id="c-1",
        cluster_role="primary",
        status="succeeded",
        pattern_card_id="pc-1",
    )


def test_primary_missing_returns_none(storage_mock: Any) -> None:
    """primary 부재 → None (자체 분석 폴백)."""
    storage_mock.find_primary_in_cluster.return_value = None
    item = _item()
    primary = batch_orchestrator._resolve_cluster_primary(item, _batch())
    assert primary is None


def test_primary_terminal_returns_none(storage_mock: Any) -> None:
    """primary failed/skipped → 폴백."""
    storage_mock.find_primary_in_cluster.return_value = KeywordBatchItem(
        id="i-primary",
        batch_id="b-1",
        keyword="x",
        cluster_id="c-1",
        cluster_role="primary",
        status="failed",
    )
    item = _item()
    assert batch_orchestrator._resolve_cluster_primary(item, _batch()) is None


def test_primary_succeeded_returns_primary(storage_mock: Any) -> None:
    """primary succeeded + pattern_card_id → 즉시 재사용."""
    storage_mock.find_primary_in_cluster.return_value = _primary_succeeded()
    primary = batch_orchestrator._resolve_cluster_primary(_item(), _batch())
    assert primary is not None
    assert primary.id == "i-primary"
    assert primary.pattern_card_id == "pc-1"


def test_primary_running_polls_until_succeeded(
    storage_mock: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """primary 가 running 이다가 succeeded 되면 그 시점에 반환."""
    states = [
        KeywordBatchItem(
            id="i-primary",
            batch_id="b-1",
            keyword="x",
            cluster_id="c-1",
            cluster_role="primary",
            status="running",
        ),
        _primary_succeeded(),
    ]
    storage_mock.find_primary_in_cluster.side_effect = states
    monkeypatch.setattr("application.batch_orchestrator.time.sleep", lambda _s: None)
    monkeypatch.setattr("config.settings.settings.batch_cluster_poll_interval_sec", 0.0)
    monkeypatch.setattr("config.settings.settings.batch_cluster_primary_timeout_sec", 5)

    primary = batch_orchestrator._resolve_cluster_primary(_item(), _batch())
    assert primary is not None
    assert primary.status == "succeeded"


def test_primary_running_timeout_returns_none(
    storage_mock: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """primary 가 계속 running → 타임아웃 → 폴백."""
    storage_mock.find_primary_in_cluster.return_value = KeywordBatchItem(
        id="i-primary",
        batch_id="b-1",
        keyword="x",
        cluster_id="c-1",
        cluster_role="primary",
        status="running",
    )
    monkeypatch.setattr("application.batch_orchestrator.time.sleep", lambda _s: None)
    monkeypatch.setattr("config.settings.settings.batch_cluster_poll_interval_sec", 0.01)
    # 타임아웃 0초 → 첫 polling 실패 직후 deadline 초과
    monkeypatch.setattr("config.settings.settings.batch_cluster_primary_timeout_sec", 0)

    primary = batch_orchestrator._resolve_cluster_primary(_item(), _batch())
    assert primary is None


def test_run_member_analyze_copies_pattern_card_id(storage_mock: Any) -> None:
    """analyze member: pattern_card_id 복사 + run_analyze_only 호출 0."""
    primary = _primary_succeeded()
    item = _item(operation="analyze")
    with patch("application.batch_orchestrator.orchestrator") as orch_mock:
        batch_orchestrator._run_member_with_primary(item, primary)
        orch_mock.run_analyze_only.assert_not_called()
    storage_mock.update_item_result.assert_called_once()
    kwargs = storage_mock.update_item_result.call_args.kwargs
    assert kwargs["pattern_card_id"] == "pc-1"


def test_run_member_generate_uses_pattern_card_path(storage_mock: Any, tmp_path: Any) -> None:
    """generate member: pattern_card_path 주입해 run_generate_only 호출."""
    primary = _primary_succeeded()
    item = _item(operation="generate")
    pc_path = tmp_path / "pattern-card.json"
    pc_path.write_text("{}", encoding="utf-8")

    gen_result = GenerateResult(
        status=StageStatus.SUCCEEDED,
        keyword="kw",
        slug="kw",
        pattern_card_id="pc-1",
        generated_content_id="gen-1",
        compliance_passed=True,
    )
    with (
        patch.object(batch_orchestrator, "_resolve_primary_card_path", return_value=pc_path),
        patch("application.batch_orchestrator.orchestrator") as orch_mock,
    ):
        orch_mock.run_generate_only.return_value = gen_result
        batch_orchestrator._run_member_with_primary(item, primary)
        orch_mock.run_generate_only.assert_called_once_with(keyword="kw", pattern_card_path=pc_path)

    kwargs = storage_mock.update_item_result.call_args.kwargs
    assert kwargs["generated_content_id"] == "gen-1"
    assert kwargs["compliance_passed"] is True


def test_run_member_pipeline_uses_pattern_card_path(storage_mock: Any, tmp_path: Any) -> None:
    """pipeline member: pattern_card_path 주입해 run_pipeline 호출."""
    primary = _primary_succeeded()
    item = _item(operation="pipeline")
    pc_path = tmp_path / "pc.json"
    pc_path.write_text("{}", encoding="utf-8")

    with (
        patch.object(batch_orchestrator, "_resolve_primary_card_path", return_value=pc_path),
        patch("application.batch_orchestrator.orchestrator") as orch_mock,
    ):
        orch_mock.run_pipeline.return_value = PipelineResult(
            status=StageStatus.SUCCEEDED,
            keyword="kw",
            slug="kw",
            pattern_card_id="pc-1",
            generated_content_id="gen-2",
        )
        batch_orchestrator._run_member_with_primary(item, primary)
        orch_mock.run_pipeline.assert_called_once_with(keyword="kw", pattern_card_path=pc_path)

    kwargs = storage_mock.update_item_result.call_args.kwargs
    assert kwargs["generated_content_id"] == "gen-2"


def test_run_member_generate_path_missing_raises(storage_mock: Any) -> None:
    """primary 의 PatternCard 파일 부재 → RuntimeError (caller 가 retry/fail 처리)."""
    primary = _primary_succeeded()
    item = _item(operation="generate")
    with (
        patch.object(batch_orchestrator, "_resolve_primary_card_path", return_value=None),
        pytest.raises(RuntimeError, match="PatternCard 파일 부재"),
    ):
        batch_orchestrator._run_member_with_primary(item, primary)
