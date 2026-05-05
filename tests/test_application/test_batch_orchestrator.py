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

    Phase 3 PR2 — atomic claim 도입. claim_item_for_dispatch default 는 get_item 의
    return_value 를 그대로 반환 (single-worker 환경 가정). race-condition 검증
    테스트는 명시적으로 `claim_item_for_dispatch.return_value = None` override.
    """
    with patch("application.batch_orchestrator.storage") as m:
        m.get_batch.return_value = _batch()
        m.claim_item_for_dispatch.side_effect = lambda item_id, *, job_id: m.get_item.return_value
        yield m


@pytest.fixture
def manager_mock() -> Any:
    with patch("application.batch_orchestrator.batch_job_manager") as m:
        m.get_default_manager.return_value = MagicMock()
        yield m


class TestEnqueueFromCsv:
    def test_overnight_mode_persists_without_dispatch(
        self, storage_mock: Any, manager_mock: Any
    ) -> None:
        """Phase 3 PR1 — overnight 모드는 DB 저장만, 즉시 dispatch X."""
        storage_mock.insert_batch.return_value = _batch(id="b-overnight")
        storage_mock.insert_items.return_value = [_item(id="i-1", batch_id="b-overnight")]
        result = batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="overnight")
        assert result.batch_id == "b-overnight"
        # auto_dispatch=True 라도 mode='overnight' 이면 worker 에 submit 안 함
        manager_mock.get_default_manager.return_value.submit.assert_not_called()
        # batch insert 시 mode='overnight' 으로 저장됐는지
        inserted = storage_mock.insert_batch.call_args.args[0]
        assert inserted.mode == "overnight"

    def test_auto_mode_priority_routing(self, storage_mock: Any, manager_mock: Any) -> None:
        """Phase 3 (2026-05-05) — mode='auto' 활성화: priority<=3 즉시, >=4 overnight 보류."""
        storage_mock.insert_batch.return_value = _batch(id="b-auto")
        storage_mock.insert_items.return_value = [
            _item(id="i-prio2", batch_id="b-auto", priority=2),  # 즉시
            _item(id="i-prio5", batch_id="b-auto", priority=5),  # 보류
            _item(id="i-prio7", batch_id="b-auto", priority=7),  # 보류
        ]
        batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="auto")
        # priority<=3 인 1건만 submit
        submitted_ids = [
            c.args[1] for c in manager_mock.get_default_manager.return_value.submit.call_args_list
        ]
        assert submitted_ids == ["i-prio2"]

    def test_unknown_mode_raises_not_supported(self, storage_mock: Any) -> None:
        with pytest.raises(NotSupportedYetError):
            batch_orchestrator.enqueue_from_csv("keyword\nkw\n", mode="weekly")

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
        # Phase 3 PR2 — terminal status 는 claim 호출 전에 차단되어야 함
        storage_mock.claim_item_for_dispatch.assert_not_called()

    def test_claim_failed_skips_dispatch(self, storage_mock: Any) -> None:
        """Phase 3 PR2 — atomic claim 실패 (다른 worker 가 먼저 잡음) → run_* 호출 0."""
        storage_mock.get_item.return_value = _item(operation="analyze")
        storage_mock.claim_item_for_dispatch.side_effect = None
        storage_mock.claim_item_for_dispatch.return_value = None
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            batch_orchestrator._dispatch_item("i-1")
            orch_mock.run_analyze_only.assert_not_called()
            orch_mock.run_pipeline.assert_not_called()
            orch_mock.run_generate_only.assert_not_called()
        # 후속 status update 도 호출 안 됨
        storage_mock.update_item_status.assert_not_called()
        storage_mock.update_item_result.assert_not_called()

    def test_skips_ready_to_publish_terminal(self, storage_mock: Any) -> None:
        """Phase B9 fix — ready_to_publish 도 terminal 로 처리 (재진입 시 중복 실행 방지)."""
        storage_mock.get_item.return_value = _item(status="ready_to_publish")
        batch_orchestrator._dispatch_item("i-1")
        storage_mock.update_item_status.assert_not_called()

    def test_skips_needs_review_terminal(self, storage_mock: Any) -> None:
        """Phase B9 fix — needs_review 도 terminal (직접 dispatch 차단, retry_item 만 queued 복귀)."""
        storage_mock.get_item.return_value = _item(status="needs_review")
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
        # Phase 3 PR2 — running 마킹은 claim_item_for_dispatch 가 atomic 하게 처리.
        # update_item_status 는 최종 status 만 호출.
        storage_mock.claim_item_for_dispatch.assert_called_once()
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
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
                compliance_passed=True,
            )
            batch_orchestrator._dispatch_item("i-1")
            orch_mock.run_pipeline.assert_called_once_with("kw")
        # Phase B7 — pipeline 결과의 두 id 모두 전파
        storage_mock.update_item_result.assert_called_once()
        kwargs = storage_mock.update_item_result.call_args.kwargs
        assert kwargs["pattern_card_id"] == "pc-uuid-2"
        assert kwargs["generated_content_id"] == "gen-uuid-2"
        # Phase B9 — compliance_passed=True → ready_to_publish 마킹
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "ready_to_publish" in statuses

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

    def test_generate_compliance_failure_marks_needs_review(self, storage_mock: Any) -> None:
        """Phase B9 — generate + compliance_passed=False → needs_review."""
        storage_mock.get_item.return_value = _item(operation="generate")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_generate_only.return_value = GenerateResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=False,
            )
            batch_orchestrator._dispatch_item("i-1")
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "needs_review" in statuses
        assert "ready_to_publish" not in statuses

    def test_compliance_failure_triggers_violation_notifier(self, storage_mock: Any) -> None:
        """Phase 4 PR1 — generate/pipeline + compliance_passed=False 시 notifier 1회 호출."""
        storage_mock.get_item.return_value = _item(operation="pipeline")
        with (
            patch("application.batch_orchestrator.orchestrator") as orch_mock,
            patch("application.batch_orchestrator.notifier") as notif,
        ):
            orch_mock.run_pipeline.return_value = PipelineResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=False,
                compliance_violations=["효과 과장", "1인칭 홍보"],
            )
            batch_orchestrator._dispatch_item("i-1")
        notif.send_compliance_violation.assert_called_once()
        # 위반 카테고리 인자 검증
        categories = notif.send_compliance_violation.call_args.args[1]
        assert "효과 과장" in categories
        assert "1인칭 홍보" in categories

    def test_compliance_passed_no_violation_notifier(self, storage_mock: Any) -> None:
        """compliance_passed=True 면 notifier 호출 0."""
        storage_mock.get_item.return_value = _item(operation="pipeline")
        with (
            patch("application.batch_orchestrator.orchestrator") as orch_mock,
            patch("application.batch_orchestrator.notifier") as notif,
        ):
            orch_mock.run_pipeline.return_value = PipelineResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=True,
            )
            batch_orchestrator._dispatch_item("i-1")
        notif.send_compliance_violation.assert_not_called()

    def test_compliance_none_no_violation_notifier(self, storage_mock: Any) -> None:
        """compliance_passed=None (데이터 누락) 은 알림 X — False 일 때만 알림."""
        storage_mock.get_item.return_value = _item(operation="generate")
        with (
            patch("application.batch_orchestrator.orchestrator") as orch_mock,
            patch("application.batch_orchestrator.notifier") as notif,
        ):
            orch_mock.run_generate_only.return_value = GenerateResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=None,
            )
            batch_orchestrator._dispatch_item("i-1")
        notif.send_compliance_violation.assert_not_called()

    def test_analyze_compliance_no_violation_notifier(self, storage_mock: Any) -> None:
        """analyze 는 의료법 검증 무관 — 알림 X."""
        storage_mock.get_item.return_value = _item(operation="analyze")
        with (
            patch("application.batch_orchestrator.orchestrator") as orch_mock,
            patch("application.batch_orchestrator.notifier") as notif,
        ):
            orch_mock.run_analyze_only.return_value = AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
            )
            batch_orchestrator._dispatch_item("i-1")
        notif.send_compliance_violation.assert_not_called()

    def test_generate_compliance_none_marks_needs_review(self, storage_mock: Any) -> None:
        """Phase B9 — generate + compliance_passed=None → needs_review (데이터 누락 안전망)."""
        storage_mock.get_item.return_value = _item(operation="generate")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_generate_only.return_value = GenerateResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=None,
            )
            batch_orchestrator._dispatch_item("i-1")
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "needs_review" in statuses
        assert "ready_to_publish" not in statuses
        assert "succeeded" not in statuses

    def test_pipeline_compliance_none_marks_needs_review(self, storage_mock: Any) -> None:
        """Phase B9 — pipeline + compliance_passed=None → needs_review."""
        storage_mock.get_item.return_value = _item(operation="pipeline")
        with patch("application.batch_orchestrator.orchestrator") as orch_mock:
            orch_mock.run_pipeline.return_value = PipelineResult(
                status=StageStatus.SUCCEEDED,
                keyword="kw",
                slug="kw",
                pattern_card_id="pc-1",
                generated_content_id="gen-1",
                compliance_passed=None,
            )
            batch_orchestrator._dispatch_item("i-1")
        statuses = [c.args[1] for c in storage_mock.update_item_status.call_args_list]
        assert "needs_review" in statuses

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

    def test_ready_to_publish_can_be_retried(self, storage_mock: Any, manager_mock: Any) -> None:
        """Phase B9 fix — ready_to_publish 도 운영자가 수동 재생성 트리거 가능."""
        storage_mock.get_item.return_value = _item(status="ready_to_publish", retry_count=2)
        batch_orchestrator.retry_item("i-1")
        last_status = storage_mock.update_item_status.call_args_list[-1].args[1]
        assert last_status == "queued"
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

    # ── Phase 4 PR1 — 알림 hook ──

    def test_completed_first_time_calls_notifier(self, storage_mock: Any) -> None:
        """queued/running → completed 전이 시 send_batch_completed 1회 호출."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=3, status="running"),  # 호출 1: 전이 전
            _batch(id="b-1", total_count=3, status="completed"),  # 호출 2: refreshed
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 1,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 2,
        }
        with patch("application.batch_orchestrator.notifier") as notif:
            batch_orchestrator.recompute_batch_status("b-1")
        notif.send_batch_completed.assert_called_once()
        notif.send_batch_failed.assert_not_called()

    def test_already_completed_no_double_notification(self, storage_mock: Any) -> None:
        """이미 completed 상태에서 재호출 — 알림 스킵 (중복 방지)."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=3, status="completed"),  # 이미 completed
            _batch(id="b-1", total_count=3, status="completed"),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 3,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 0,
        }
        with patch("application.batch_orchestrator.notifier") as notif:
            batch_orchestrator.recompute_batch_status("b-1")
        notif.send_batch_completed.assert_not_called()

    def test_all_failed_calls_send_batch_failed(self, storage_mock: Any) -> None:
        """failed_count == total_count → send_batch_failed."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=3, status="running"),
            _batch(id="b-1", total_count=3, status="completed"),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 0,
            "failed_count": 3,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 0,
        }
        with patch("application.batch_orchestrator.notifier") as notif:
            batch_orchestrator.recompute_batch_status("b-1")
        notif.send_batch_failed.assert_called_once()
        notif.send_batch_completed.assert_not_called()

    def test_notifier_failure_does_not_raise(self, storage_mock: Any) -> None:
        """notifier.send_batch_completed 가 raise 해도 recompute 자체는 graceful."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=2, status="running"),
            _batch(id="b-1", total_count=2, status="completed"),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 2,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 0,
        }
        with patch("application.batch_orchestrator.notifier") as notif:
            notif.send_batch_completed.side_effect = RuntimeError("slack down")
            # 예외 raise 안 하고 정상 반환
            batch_orchestrator.recompute_batch_status("b-1")

    # ── Phase 4 PR2 — auto-publish auto-trigger ──

    def test_auto_publish_triggered_on_completion(self, storage_mock: Any) -> None:
        """completed 첫 진입 + auto_publish_enabled=True → auto_publisher 호출."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=2, status="running", auto_publish_enabled=True),
            _batch(id="b-1", total_count=2, status="completed", auto_publish_enabled=True),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 2,
        }
        with patch("application.auto_publisher.auto_publish_ready_items") as auto_pub:
            batch_orchestrator.recompute_batch_status("b-1")
        auto_pub.assert_called_once_with("b-1")

    def test_auto_publish_skipped_when_disabled(self, storage_mock: Any) -> None:
        """auto_publish_enabled=False 면 자동 호출 안 함."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=2, status="running", auto_publish_enabled=False),
            _batch(id="b-1", total_count=2, status="completed", auto_publish_enabled=False),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 2,
        }
        with patch("application.auto_publisher.auto_publish_ready_items") as auto_pub:
            batch_orchestrator.recompute_batch_status("b-1")
        auto_pub.assert_not_called()

    def test_auto_publish_failure_graceful(self, storage_mock: Any) -> None:
        """auto_publisher 가 raise 해도 recompute 는 정상 반환."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=2, status="running", auto_publish_enabled=True),
            _batch(id="b-1", total_count=2, status="completed", auto_publish_enabled=True),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 2,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 0,
        }
        with patch("application.auto_publisher.auto_publish_ready_items") as auto_pub:
            auto_pub.side_effect = RuntimeError("ranking storage down")
            # raise 없이 통과
            batch_orchestrator.recompute_batch_status("b-1")

    def test_auto_publish_not_triggered_on_already_completed(self, storage_mock: Any) -> None:
        """이미 completed 상태에서 재호출 — auto_publish 도 스킵 (중복 방지)."""
        storage_mock.get_batch.side_effect = [
            _batch(id="b-1", total_count=2, status="completed", auto_publish_enabled=True),
            _batch(id="b-1", total_count=2, status="completed", auto_publish_enabled=True),
        ]
        storage_mock.count_items_by_status.return_value = {
            "succeeded_count": 2,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "ready_to_publish_count": 0,
        }
        with patch("application.auto_publisher.auto_publish_ready_items") as auto_pub:
            batch_orchestrator.recompute_batch_status("b-1")
        auto_pub.assert_not_called()


class TestDispatchOvernightBatches:
    """Phase 3 PR1 — overnight batch 일괄 dispatch."""

    def test_no_overnight_queued_returns_zero(self, storage_mock: Any) -> None:
        storage_mock.list_batches.return_value = [_batch(id="b-1", mode="now", status="queued")]
        result = batch_orchestrator.dispatch_overnight_batches()
        assert result == {
            "dispatched_batches": 0,
            "dispatched_items": 0,
            "skipped_batches": 0,
        }

    def test_overnight_queued_dispatched(self, storage_mock: Any, manager_mock: Any) -> None:
        storage_mock.list_batches.return_value = [
            _batch(id="b-on", mode="overnight", status="queued"),
        ]
        storage_mock.list_items.return_value = [
            _item(id="i-1", batch_id="b-on"),
            _item(id="i-2", batch_id="b-on"),
        ]
        result = batch_orchestrator.dispatch_overnight_batches()
        assert result["dispatched_batches"] == 1
        assert result["dispatched_items"] == 2
        # batch.status='running' 갱신
        storage_mock.update_batch_status.assert_called_once()
        assert storage_mock.update_batch_status.call_args.args[1] == "running"
        # 2 item dispatch
        assert manager_mock.get_default_manager.return_value.submit.call_count == 2

    def test_specific_batch_id_filters(self, storage_mock: Any, manager_mock: Any) -> None:
        """batch_id 지정 시 해당 batch 만 처리."""
        storage_mock.get_batch.return_value = _batch(id="b-on", mode="overnight", status="queued")
        storage_mock.list_items.return_value = [_item(id="i-1", batch_id="b-on")]
        result = batch_orchestrator.dispatch_overnight_batches(batch_id="b-on")
        assert result["dispatched_batches"] == 1
        assert result["dispatched_items"] == 1

    def test_overnight_dispatch_calls_notifier(self, storage_mock: Any, manager_mock: Any) -> None:
        """Phase 4 PR1 — dispatched_items > 0 시 send_overnight_dispatched 호출."""
        storage_mock.list_batches.return_value = [
            _batch(id="b-on", mode="overnight", status="queued"),
        ]
        storage_mock.list_items.return_value = [
            _item(id="i-1", batch_id="b-on"),
            _item(id="i-2", batch_id="b-on"),
        ]
        with patch("application.batch_orchestrator.notifier") as notif:
            batch_orchestrator.dispatch_overnight_batches()
        notif.send_overnight_dispatched.assert_called_once_with(1, 2)

    def test_overnight_dispatch_no_items_skips_notifier(self, storage_mock: Any) -> None:
        """overnight queued batch 부재 → early return, notifier 호출 0."""
        storage_mock.list_batches.return_value = [_batch(id="b-1", mode="now", status="queued")]
        with patch("application.batch_orchestrator.notifier") as notif:
            batch_orchestrator.dispatch_overnight_batches()
        notif.send_overnight_dispatched.assert_not_called()

    def test_specific_batch_not_overnight_skips(self, storage_mock: Any) -> None:
        """batch_id 가 overnight/auto 가 아니면 skip."""
        storage_mock.get_batch.return_value = _batch(id="b-now", mode="now", status="queued")
        result = batch_orchestrator.dispatch_overnight_batches(batch_id="b-now")
        assert result["dispatched_batches"] == 0

    def test_auto_mode_batch_dispatched(self, storage_mock: Any, manager_mock: Any) -> None:
        """Phase 3 — mode=auto batch 도 dispatch_overnight 가 처리. priority 라우팅으로
        보류된 priority>=4 item 들이 일괄 실행."""
        storage_mock.list_batches.return_value = [
            _batch(id="b-auto", mode="auto", status="queued"),
        ]
        storage_mock.list_items.return_value = [
            _item(id="i-prio5", batch_id="b-auto", priority=5),
        ]
        result = batch_orchestrator.dispatch_overnight_batches()
        assert result["dispatched_batches"] == 1
        assert result["dispatched_items"] == 1


class TestBackfillUnlinkedItems:
    """Phase B10 PR4 — fire-and-forget 회수 실패 사후 백필."""

    def test_matches_both_pc_and_gen(self, storage_mock: Any) -> None:
        items = [
            _item(id="i-1", keyword="kw1", operation="pipeline"),  # 둘 다 None
        ]
        storage_mock.list_items.return_value = items
        storage_mock.find_pattern_card_by_triple.return_value = "pc-1"
        storage_mock.find_generated_content_by_triple.return_value = "gen-1"

        result = batch_orchestrator.backfill_unlinked_items("b-1")
        assert result == {
            "matched_pattern_cards": 1,
            "matched_generated_contents": 1,
            "still_unlinked": 0,
        }
        storage_mock.update_item_result.assert_called_once()
        kwargs = storage_mock.update_item_result.call_args.kwargs
        assert kwargs["pattern_card_id"] == "pc-1"
        assert kwargs["generated_content_id"] == "gen-1"

    def test_matches_only_pattern_card(self, storage_mock: Any) -> None:
        """analyze item — pattern_card_id 만 매칭 (generated_content 는 검사 자체 안 함)."""
        items = [_item(id="i-1", keyword="kw1", operation="analyze")]
        storage_mock.list_items.return_value = items
        storage_mock.find_pattern_card_by_triple.return_value = "pc-2"
        # generated 검사는 호출 안 됨 (operation=analyze)

        result = batch_orchestrator.backfill_unlinked_items("b-1")
        assert result["matched_pattern_cards"] == 1
        assert result["matched_generated_contents"] == 0
        storage_mock.find_generated_content_by_triple.assert_not_called()

    def test_no_match_increments_still_unlinked(self, storage_mock: Any) -> None:
        items = [_item(id="i-1", keyword="kw1", operation="pipeline")]
        storage_mock.list_items.return_value = items
        storage_mock.find_pattern_card_by_triple.return_value = None
        storage_mock.find_generated_content_by_triple.return_value = None

        result = batch_orchestrator.backfill_unlinked_items("b-1")
        assert result["matched_pattern_cards"] == 0
        assert result["matched_generated_contents"] == 0
        assert result["still_unlinked"] == 1
        storage_mock.update_item_result.assert_not_called()

    def test_idempotent_skips_already_filled(self, storage_mock: Any) -> None:
        """이미 두 FK 가 모두 채워진 item 은 건너뜀."""
        items = [
            _item(
                id="i-1",
                keyword="kw1",
                operation="pipeline",
                pattern_card_id="pc-existing",
                generated_content_id="gen-existing",
            )
        ]
        storage_mock.list_items.return_value = items

        result = batch_orchestrator.backfill_unlinked_items("b-1")
        assert result == {
            "matched_pattern_cards": 0,
            "matched_generated_contents": 0,
            "still_unlinked": 0,
        }
        storage_mock.find_pattern_card_by_triple.assert_not_called()
        storage_mock.update_item_result.assert_not_called()

    def test_partial_match_counts_still_unlinked(self, storage_mock: Any) -> None:
        """Phase B9 fix — 둘 중 하나만 매칭되고 다른 하나 None 인 item 도 still_unlinked."""
        items = [_item(id="i-1", keyword="kw1", operation="pipeline")]  # 둘 다 None
        storage_mock.list_items.return_value = items
        storage_mock.find_pattern_card_by_triple.return_value = "pc-1"
        storage_mock.find_generated_content_by_triple.return_value = None  # gen 매칭 실패

        result = batch_orchestrator.backfill_unlinked_items("b-1")
        assert result["matched_pattern_cards"] == 1
        assert result["matched_generated_contents"] == 0
        # 부분 매칭 — generated_content_id 가 여전히 None 이라 still_unlinked 카운트
        assert result["still_unlinked"] == 1
        # update_item_result 는 호출됨 (pc 만 채움)
        storage_mock.update_item_result.assert_called_once()
