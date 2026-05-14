"""batch storage Supabase CRUD 테스트 — Supabase client mock."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
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
    """None 인자는 update payload 에서 제외.

    단, error / failure_category 는 예외 — failure 외 status 로 전환될 때 자동
    NULL clear (ea2bf28, 2026-05-14). 운영 화면에 잔존 메시지·카테고리가 남지
    않도록 보장.
    """
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
    # auto-clear: running 은 failure status 가 아니므로 error / failure_category 가
    # 명시적으로 None 으로 들어가 운영 화면의 잔존 표시를 차단.
    assert payload["error"] is None
    assert payload["failure_category"] is None
    assert "job_id" not in payload  # 안 넣었으니 없음 (auto-clear 대상 아님)


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
        # Phase B9 — ready_to_publish 추가
        {"id": "i-7", "batch_id": "b-1", "keyword": "k7", "status": "ready_to_publish"},
        {"id": "i-8", "batch_id": "b-1", "keyword": "k8", "status": "ready_to_publish"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = items_payload
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        counters = storage.count_items_by_status("b-1")
    assert counters == {
        "succeeded_count": 2,
        "failed_count": 1,
        "skipped_count": 1,
        "needs_review_count": 1,
        "ready_to_publish_count": 2,
    }


# ── Phase B9 PR3 — 검수 큐 ──


def test_update_item_review_review_status_only(mock_client: MagicMock) -> None:
    """status None — review_status + reviewed_at 만 갱신 (needs_fix / reject 케이스)."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_review("i-1", review_status="needs_fix")
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert payload["review_status"] == "needs_fix"
    assert "reviewed_at" in payload
    assert "status" not in payload
    assert "completed_at" not in payload


def test_update_item_review_with_status_transition(mock_client: MagicMock) -> None:
    """approve 케이스 — status=ready_to_publish 동시 전환 + completed_at 도 갱신."""
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_review(
            "i-1",
            review_status="approved",
            status="ready_to_publish",
            reviewer="alice",
        )
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert payload["review_status"] == "approved"
    assert payload["status"] == "ready_to_publish"
    assert payload["reviewer"] == "alice"
    assert "reviewed_at" in payload
    assert "completed_at" in payload


def test_update_item_review_omits_reviewer_when_none(mock_client: MagicMock) -> None:
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        storage.update_item_review("i-1", review_status="approved", status="ready_to_publish")
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert "reviewer" not in payload


def test_list_review_pending_items_filters(mock_client: MagicMock) -> None:
    """status='needs_review' AND review_status='pending' 둘 다 eq 적용."""
    items_payload = [
        {"id": "i-1", "batch_id": "b-1", "keyword": "k1", "status": "needs_review"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = items_payload
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        items = storage.list_review_pending_items("b-1")
    assert len(items) == 1
    assert items[0].keyword == "k1"


def test_list_review_pending_items_empty(mock_client: MagicMock) -> None:
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        items = storage.list_review_pending_items("b-1")
    assert items == []


# ── Phase B10 PR4 — Triple link 사후 백필 ──


def test_find_pattern_card_by_triple_returns_id(mock_client: MagicMock) -> None:
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": "pc-uuid-1"}
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_pattern_card_by_triple("강남-다이어트", "강남 다이어트")
    assert result == "pc-uuid-1"


def test_find_pattern_card_by_triple_missing_returns_none(mock_client: MagicMock) -> None:
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_pattern_card_by_triple("slug-x", "kw-x")
    assert result is None


def test_find_generated_content_by_triple_primary_match(mock_client: MagicMock) -> None:
    """job_id + slug + keyword 1차 매칭 성공."""
    # 1차 매칭 응답 — eq 3번 chain
    chain_primary = mock_client.table.return_value.select.return_value
    chain_primary.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": "gen-uuid-1"}
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_generated_content_by_triple("job-1", "slug-1", "kw-1")
    assert result == "gen-uuid-1"


def test_find_generated_content_by_triple_falls_back_to_slug_keyword(
    mock_client: MagicMock,
) -> None:
    """1차 매칭 실패 → 2차 fallback (slug + keyword + order created_at desc) 매칭."""
    chain_select = mock_client.table.return_value.select.return_value

    def _execute_router() -> Any:
        # 매번 다른 응답 — 1차는 빈 array, 2차는 매칭
        return SimpleNamespace(data=[{"id": "gen-fallback"}])

    # 1차: eq.eq.eq.limit.execute → 빈 결과
    chain_select.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    # 2차: eq.eq.order.limit.execute → 매칭
    chain_select.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "gen-fallback"}]
    )

    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_generated_content_by_triple("job-1", "slug-1", "kw-1")
    assert result == "gen-fallback"
    # 잠재 사용 회피 경고 무력화
    _ = _execute_router


def test_find_generated_content_by_triple_job_id_none_skips_primary(
    mock_client: MagicMock,
) -> None:
    """job_id None → 1차 매칭 스킵, 바로 2차 fallback."""
    chain = mock_client.table.return_value.select.return_value
    # 2차 fallback 만 호출되어야 함 — primary path mock 안 함
    chain.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "gen-only-fallback"}]
    )

    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_generated_content_by_triple(None, "slug-1", "kw-1")
    assert result == "gen-only-fallback"


def test_find_generated_content_by_triple_all_missing(mock_client: MagicMock) -> None:
    chain = mock_client.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    chain.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )

    with patch("domain.batch.storage.get_client", return_value=mock_client):
        result = storage.find_generated_content_by_triple("job-1", "slug-1", "kw-1")
    assert result is None


# ── Phase 3 PR2 — atomic claim ──


def test_claim_item_for_dispatch_success(mock_client: MagicMock) -> None:
    """status='queued' 인 row 1건 → KeywordBatchItem 반환 + payload 검증."""
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "i-1",
            "batch_id": "b-1",
            "keyword": "kw",
            "status": "running",
            "job_id": "batch-i-1-abc123",
        }
    ]
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        claimed = storage.claim_item_for_dispatch("i-1", job_id="batch-i-1-abc123")
    assert claimed is not None
    assert claimed.id == "i-1"
    assert claimed.job_id == "batch-i-1-abc123"
    # payload 검증 — status/started_at/job_id 모두 set
    payload = mock_client.table.return_value.update.call_args.args[0]
    assert payload["status"] == "running"
    assert payload["job_id"] == "batch-i-1-abc123"
    assert "started_at" in payload


def test_claim_item_for_dispatch_already_taken(mock_client: MagicMock) -> None:
    """다른 worker 가 먼저 잡아서 status≠queued — eq filter 가 0 row 반환 → None."""
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    with patch("domain.batch.storage.get_client", return_value=mock_client):
        claimed = storage.claim_item_for_dispatch("i-1", job_id="batch-i-1-xyz")
    assert claimed is None
