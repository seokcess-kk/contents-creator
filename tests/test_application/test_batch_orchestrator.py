"""batch_orchestrator — enqueue/dispatch/retry/cancel 테스트.

도메인 격리 검증: domain/batch 만 mock 하고 단일 흐름 (orchestrator.run_*) 도 mock.
실제 BrightData/Anthropic/Supabase 호출 0건.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application import batch_orchestrator
from application.models import (
    AnalyzeResult,
    GenerateResult,
    PipelineResult,
    StageStatus,
)
from domain.batch.model import (
    KeywordBatch,
    KeywordBatchItem,
    NotSupportedYetError,
)


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "operation": "analyze",
        "status": "queued",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def _batch(**overrides: object) -> KeywordBatch:
    base: dict[str, object] = {"id": "b-1", "total_count": 5}
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


@pytest.fixture
def storage_mock() -> Any:
    """storage 전체 mock + get_batch default 를 임계값 없는 KeywordBatch 로.

    Phase B8 — `_dispatch_item` 이 batch fetch 후 사전 필터/cluster 분기를 결정하므로
    각 테스트에서 명시 override 안 하면 임계값 None / cluster_dedupe False default 사용.
    """
    with patch("application.batch_orchestrator.storage") as m:
        m.get_batch.return_value = _batch()
        yield m


@pytest.fixture
def manager_mock() -> Any:
    with patch("application.batch_orchestrator.batch_job_manager") as m:
        m.get_default_manager.return_value = MagicMock()
        yield m


class TestEnqueueFromCsv:
    def test_overnight_mode_raises_not_supported(self, storage_mock: Any) -> None:
        with pytest.raises(NotSupportedYetError, match="now"):
            batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="overnight")
        storage_mock.insert_batch.assert_not_called()

    def test_auto_mode_raises_not_supported(self, storage_mock: Any) -> None:
        with pytest.raises(NotSupportedYetError):
            batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="auto")

    def test_creates_batch_and_items(self, storage_mock: Any, manager_mock: Any) -> None:
        storage_mock.insert_batch.return_value = _batch(id="b-new")
        storage_mock.insert_items.return_value = [
            _item(id="i-1", batch_id="b-new"),
            _item(id="i-2", batch_id="b-new", keyword="kw2"),
        ]
        result = batch_orchestrator.enqueue_from_csv(
            "keyword\nkw1\nkw2\n", mode="now", name="test-batch"
        )
        assert result.batch_id == "b-new"
        assert result.created == 2
        # batch_id 가 진짜 id 로 갱신된 채 insert_items 호출되어야 함
        items_arg = storage_mock.insert_items.call_args.args[0]
        assert all(it.batch_id == "b-new" for it in items_arg)
        # 2 item 모두 dispatch 됨
        assert manager_mock.get_default_manager.return_value.submit.call_count == 2

    def test_skips_dispatch_when_auto_dispatch_false(
        self, storage_mock: Any, manager_mock: Any
    ) -> None:
        storage_mock.insert_batch.return_value = _batch(id="b-x")
        storage_mock.insert_items.return_value = [_item(id="i-1", batch_id="b-x")]
        batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="now", auto_dispatch=False)
        manager_mock.get_default_manager.return_value.submit.assert_not_called()

    def test_separates_skipped_and_failed(self, storage_mock: Any, manager_mock: Any) -> None:
        storage_mock.insert_batch.return_value = _batch(id="b-x")
        storage_mock.insert_items.return_value = [_item(id="i-1", batch_id="b-x")]
        # 1 valid, 1 invalid operation, 1 duplicate
        result = batch_orchestrator.enqueue_from_csv(
            "keyword,operation\nkw1,analyze\nkw2,bogus\nkw1,analyze\n",
            mode="now",
        )
        assert result.created == 1  # storage mock 이 1건만 반환
        assert len(result.failed) == 1  # bogus operation
        assert len(result.skipped) == 1  # kw1 중복


class TestDispatchItem:
    def test_skips_already_done_items(self, storage_mock: Any) -> None:
        storage_mock.get_item.return_value = _item(status="succeeded")
        # mock 의 update 가 호출되면 안 됨
        batch_orchestrator._dispatch_item("i-1")
        storage_mock.update_item_status.assert_not_called()

    def test_analyze_operation_calls_run_analyze_only(self, storage_mock: Any) -> None:
        storage_mock.get_item.return_value = _item(operation="analyze")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_analyze_only.return_value = AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-uuid-1",
            )
            batch_orchestrator._dispatch_item("i-1")
            orch_mock.run_analyze_only.assert_called_once_with("kw")
            orch_mock.run_pipeline.assert_not_called()
        # running → succeeded
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "running" in statuses
        assert "succeeded" in statuses
        # Phase B7 — pattern_card_id 가 update_item_result 로 전파
        storage_mock.update_item_result.assert_called_once()
        kwargs = storage_mock.update_item_result.call_args.kwargs
        assert kwargs["pattern_card_id"] == "pc-uuid-1"
        assert kwargs["generated_content_id"] is None

    def test_pipeline_operation_calls_run_pipeline(self, storage_mock: Any) -> None:
        storage_mock.get_item.return_value = _item(operation="pipeline")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_pipeline.return_value = PipelineResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-uuid-2",
                generated_content_id="gen-uuid-2",
            )
            batch_orchestrator._dispatch_item("i-1")
            orch_mock.run_pipeline.assert_called_once_with("kw")
        # Phase B7 — pipeline 결과의 두 id 모두 전파
        storage_mock.update_item_result.assert_called_once()
        kwargs = storage_mock.update_item_result.call_args.kwargs
        assert kwargs["pattern_card_id"] == "pc-uuid-2"
        assert kwargs["generated_content_id"] == "gen-uuid-2"

    def test_generate_operation_propagates_ids(self, storage_mock: Any) -> None:
        """Phase B7 — generate 결과에서 두 id + compliance_passed 전파."""
        storage_mock.get_item.return_value = _item(operation="generate")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_generate_only.return_value = GenerateResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-3",
                generated_content_id="gen-3",
                compliance_passed=True,
            )
            batch_orchestrator._dispatch_item("i-1")
        storage_mock.update_item_result.assert_called_once()
        kwargs = storage_mock.update_item_result.call_args.kwargs
        assert kwargs["pattern_card_id"] == "pc-3"
        assert kwargs["generated_content_id"] == "gen-3"
        assert kwargs["compliance_passed"] is True

    def test_no_ids_no_update_item_result(self, storage_mock: Any) -> None:
        """모든 id None 일 때 update_item_result 호출 자체 스킵."""
        storage_mock.get_item.return_value = _item(operation="analyze")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_analyze_only.return_value = AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id=None,
            )
            batch_orchestrator._dispatch_item("i-1")
        storage_mock.update_item_result.assert_not_called()
        # succeeded 마킹은 진행
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "succeeded" in statuses

    def test_update_item_result_failure_does_not_block_succeeded(self, storage_mock: Any) -> None:
        """update_item_result 가 raise 해도 succeeded 마킹은 진행 (graceful)."""
        storage_mock.get_item.return_value = _item(operation="analyze")
        storage_mock.update_item_result.side_effect = RuntimeError("supabase down")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_analyze_only.return_value = AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
            )
            batch_orchestrator._dispatch_item("i-1")
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "succeeded" in statuses

    def test_failure_under_max_retries_reschedules(
        self, storage_mock: Any, manager_mock: Any
    ) -> None:
        storage_mock.get_item.return_value = _item(retry_count=0, max_retries=2)
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_analyze_only.side_effect = RuntimeError("brightdata 503")
            batch_orchestrator._dispatch_item("i-1")
        # 마지막 update 가 'queued' (재시도) 여야
        last_status = storage_mock.update_item_status.call_args_list[-1].args[1]
        assert last_status == "queued"
        # 재시도 worker 던짐
        assert manager_mock.get_default_manager.return_value.submit.called

    def test_failure_at_max_retries_marks_failed(
        self, storage_mock: Any, manager_mock: Any
    ) -> None:
        storage_mock.get_item.return_value = _item(retry_count=2, max_retries=2)
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_analyze_only.side_effect = RuntimeError("persistent")
            batch_orchestrator._dispatch_item("i-1")
        # 마지막 update 가 'failed'
        last_call = storage_mock.update_item_status.call_args_list[-1]
        assert last_call.args[1] == "failed"
        # 재시도 worker 던지지 X
        manager_mock.get_default_manager.return_value.submit.assert_not_called()

    def test_dispatcher_exception_marks_failed(self, storage_mock: Any) -> None:
        """_dispatch_item 자체가 raise 해도 _dispatch_item_safely 가 잡고 failed."""
        storage_mock.get_item.side_effect = RuntimeError("DB down")
        # safely wrapper 호출 — 외부에서 raise 안 함
        batch_orchestrator._dispatch_item_safely("i-1")
        # status='failed' 로 마킹 시도
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "failed" in statuses


class TestRetryItem:
    def test_failed_item_can_be_retried(self, storage_mock: Any, manager_mock: Any) -> None:
        storage_mock.get_item.return_value = _item(status="failed", retry_count=2)
        batch_orchestrator.retry_item("i-1")
        # queued 로 복귀
        last_status = storage_mock.update_item_status.call_args_list[-1].args[1]
        assert last_status == "queued"
        # worker 에 재투입
        manager_mock.get_default_manager.return_value.submit.assert_called_once()

    def test_running_item_cannot_be_manually_retried(self, storage_mock: Any) -> None:
        storage_mock.get_item.return_value = _item(status="running")
        with pytest.raises(ValueError, match="재시도 가능 상태 아님"):
            batch_orchestrator.retry_item("i-1")

    def test_missing_item_raises(self, storage_mock: Any) -> None:
        storage_mock.get_item.return_value = None
        with pytest.raises(ValueError, match="item 미존재"):
            batch_orchestrator.retry_item("i-x")


class TestCancelBatch:
    def test_marks_queued_items_as_skipped(self, storage_mock: Any) -> None:
        storage_mock.get_batch.return_value = _batch(id="b-1", total_count=3)
        storage_mock.list_items.return_value = [
            _item(id="i-1", status="queued"),
            _item(id="i-2", status="queued"),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 0,
            "failed_count": 0,
            "skipped_count": 2,
            "needs_review_count": 0,
        }
        cancelled = batch_orchestrator.cancel_batch("b-1")
        assert cancelled == 2
        # batch status='cancelled'
        storage_mock.update_batch_status.assert_called_once()
        assert storage_mock.update_batch_status.call_args.args[1] == "cancelled"

    def test_no_op_when_no_queued(self, storage_mock: Any) -> None:
        storage_mock.get_batch.return_value = _batch(id="b-1")
        storage_mock.list_items.return_value = []
        cancelled = batch_orchestrator.cancel_batch("b-1")
        assert cancelled == 0
        storage_mock.update_batch_status.assert_not_called()


class TestRecomputeBatchStatus:
    def test_partial_progress_keeps_running(self, storage_mock: Any) -> None:
        storage_mock.get_batch.return_value = _batch(id="b-1", total_count=5)
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 2,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
        }
        batch_orchestrator.recompute_batch_status("b-1")
        assert storage_mock.update_batch_status.call_args.args[1] == "running"

    def test_all_finished_marks_completed(self, storage_mock: Any) -> None:
        storage_mock.get_batch.return_value = _batch(id="b-1", total_count=3)
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 2,
            "failed_count": 1,
            "skipped_count": 0,
            "needs_review_count": 0,
        }
        batch_orchestrator.recompute_batch_status("b-1")
        assert storage_mock.update_batch_status.call_args.args[1] == "completed"
