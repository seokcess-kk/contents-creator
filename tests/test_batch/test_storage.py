"""batch storage Supabase CRUD 테스트 — Supabase client mock."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from domain.batch import storage
from domain.batch.model import KeywordBatch, KeywordBatchItem


def _batch(**overrides: object) -> KeywordBatch:
    base = {"total_count": 5, "mode": "now"}
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


def _item(**overrides: object) -> KeywordBatchItem:
    base = {"batch_id": "b-1", "keyword": "kw"}
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


@pytest.fixture
def mock_client() -> MagicMock:
    """Supabase 체이닝 mock — table().insert/select/update/eq/order/limit/execute."""
    return MagicMock()


def test_insert_batch_returns_with_id(mock_client: MagicMock) -> None:
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": "b-uuid-1",
            "total_count": 5,
            "mode": "now",
            "status": "queued",
            "succeeded_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "needs_review_count": 0,
            "estimated_cost_usd": 0,
        }
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.insert_batch(_batch())
    assert result.id == "b-uuid-1"
    mock_client.table.assert_called_with("keyword_batches")


def test_insert_batch_raises_when_no_row_returned(mock_client: MagicMock) -> None:
    mock_client.table.return_value.insert.return_value.execute.return_value.data = []
    with (
        patch("domain.batch.storage.get_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="no row returned"),
    ):
        storage.insert_batch(_batch())


def test_insert_items_handles_empty_input(mock_client: MagicMock) -> None:
    """빈 리스트 입력 → 빈 결과 + Supabase 호출 안 함."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.insert_items([])
    assert result == []
    mock_client.table.assert_not_called()


def test_insert_items_strips_none_fields(mock_client: MagicMock) -> None:
    """None 값 필드는 INSERT payload 에서 제외 — DB default 사용."""
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "i-1", "batch_id": "b-1", "keyword": "kw"}
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.insert_items([_item()])
    call_args = mock_client.table.return_value.insert.call_args
    payload = call_args.args[0][0]
    # None 필드 제외 검증
    assert "intent" not in payload
    assert "search_volume" not in payload
    assert "pattern_card_id" not in payload
    # 필수 필드 포함
    assert payload["keyword"] == "kw"
    assert payload["status"] == "queued"


def test_get_batch_returns_none_for_missing(mock_client: MagicMock) -> None:
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.get_batch("missing-id")
    assert result is None


def test_update_item_status_includes_only_provided_fields(mock_client: MagicMock) -> None:
    """None 인자는 update payload 에서 제외."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_status(
            "i-1",
            "running",
            started_at=datetime(2026, 5, 4, 9, 0, tzinfo=UTC),
        )
    update_call = mock_client.table.return_value.update.call_args
    payload = update_call.args[0]
    assert payload["status"] == "running"
    assert "started_at" in payload
    assert "error" not in payload  # 안 넣었으니 없음
    assert "job_id" not in payload


def test_update_item_result_partial_payload(mock_client: MagicMock) -> None:
    """Phase B7 — None 아닌 인자만 update payload 에 포함."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_result(
            "i-1",
            pattern_card_id="pc-uuid-1",
            generated_content_id=None,  # None 은 제외
            compliance_passed=True,
        )
    update_call = mock_client.table.return_value.update.call_args
    payload = update_call.args[0]
    assert payload == {"pattern_card_id": "pc-uuid-1", "compliance_passed": True}


def test_update_item_result_all_none_is_noop(mock_client: MagicMock) -> None:
    """모든 인자 None 이면 Supabase 호출 없이 즉시 return."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_result("i-1")
    # get_client 은 호출되지 않거나 호출됐어도 update 자체가 호출되면 안 됨.
    mock_client.table.return_value.update.assert_not_called()


def test_update_item_result_propagates_supabase_error(mock_client: MagicMock) -> None:
    """본 함수는 raise — caller (batch_orchestrator) 가 try/except 로 graceful 처리."""
    mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        RuntimeError("supabase down")
    )
    with (
        patch("domain.batch.storage.get_client", return_value=mock_client),
        pytest.raises(RuntimeError, match="supabase down"),
    ):
        storage.update_item_result("i-1", pattern_card_id="pc-1")


def test_update_item_result_includes_prefilter_meta(mock_client: MagicMock) -> None:
    """Phase B8 — search_volume / difficulty_grade 도 partial update 에 포함."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_result(
            "i-1",
            search_volume=1500,
            difficulty_grade="MEDIUM",
        )
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert payload == {"search_volume": 1500, "difficulty_grade": "MEDIUM"}


def test_find_primary_in_cluster_returns_primary(mock_client: MagicMock) -> None:
    """primary role item 1건 발견."""
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "i-primary",
            "batch_id": "b-1",
            "keyword": "다이어트 한의원",
            "cluster_id": "c-1",
            "cluster_role": "primary",
            "status": "succeeded",
            "pattern_card_id": "pc-1",
        }
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        primary = storage.find_primary_in_cluster("b-1", "c-1")
    assert primary is not None
    assert primary.id == "i-primary"
    assert primary.cluster_role == "primary"
    assert primary.pattern_card_id == "pc-1"


def test_find_primary_in_cluster_missing_returns_none(mock_client: MagicMock) -> None:
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        primary = storage.find_primary_in_cluster("b-1", "c-x")
    assert primary is None


def test_count_items_by_status_aggregates(mock_client: MagicMock) -> None:
    items_payload = [
        {"id": "i-1", "batch_id": "b-1", "keyword": "k1", "status": "succeeded"},
        {"id": "i-2", "batch_id": "b-1", "keyword": "k2", "status": "succeeded"},
        {"id": "i-3", "batch_id": "b-1", "keyword": "k3", "status": "failed"},
        {"id": "i-4", "batch_id": "b-1", "keyword": "k4", "status": "skipped"},
        {"id": "i-5", "batch_id": "b-1", "keyword": "k5", "status": "needs_review"},
        {"id": "i-6", "batch_id": "b-1", "keyword": "k6", "status": "running"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = items_payload
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        counters = storage.count_items_by_status("b-1")
    assert counters == {
        "succeeded_count": 2,
        "failed_count": 1,
        "skipped_count": 1,
        "needs_review_count": 1,
    }
