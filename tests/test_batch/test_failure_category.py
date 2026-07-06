"""failure_category 라우팅 + storage auto-clear 단위 테스트 (2026-05-14).

검증 대상:
- `application.batch_orchestrator._classify_exception` 7종 매핑
- `domain.batch.storage.update_item_status` 의 failure_category auto-clear
- `scripts.backfill_failure_category.classify_row` 정규식 매칭 (참고용 — 본격
  테스트는 tests/test_scripts/test_backfill_failure_category.py)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application.batch_orchestrator import _classify_exception
from domain.batch import storage
from domain.crawler.model import InsufficientCollectionError


class TestClassifyException:
    """orchestrator 가 RuntimeError 로 wrap 한 케이스를 메시지 prefix 로 분류."""

    def test_runtime_error_with_serp_message(self) -> None:
        # orchestrator 가 InsufficientCollectionError → result.error=str(exc) → RuntimeError 로 wrap.
        # 결과: RuntimeError("serp: 4 pages collected, minimum 5 required")
        exc = RuntimeError("serp: 4 pages collected, minimum 5 required")
        assert _classify_exception(exc) == "SERP_INSUFFICIENT"

    def test_runtime_error_with_scrape_message(self) -> None:
        exc = RuntimeError("scrape: 3 pages collected, minimum 5 required")
        assert _classify_exception(exc) == "SCRAPE_INSUFFICIENT"

    def test_insufficient_collection_error_directly(self) -> None:
        # 원본 예외 타입이 그대로 올라오는 경로 대비.
        exc = InsufficientCollectionError(minimum=5, actual=4, stage="serp")
        assert _classify_exception(exc) == "SERP_INSUFFICIENT"

    def test_arbitrary_runtime_error_falls_through_to_exception(self) -> None:
        exc = RuntimeError("Bright Data API timeout after 30s")
        assert _classify_exception(exc) == "EXCEPTION"

    def test_value_error_unknown_message(self) -> None:
        exc = ValueError("알 수 없는 operation: unknown")
        assert _classify_exception(exc) == "EXCEPTION"


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


def _last_update_payload(mock_client: MagicMock) -> dict[str, Any]:
    return mock_client.table.return_value.update.call_args.args[0]


class TestUpdateItemStatusFailureCategory:
    """update_item_status 의 failure_category auto-clear 시맨틱."""

    def test_failure_category_set_when_failed(self, mock_client: MagicMock) -> None:
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status(
                "i-1",
                "failed",
                error="serp: 4 pages collected, minimum 5 required",
                failure_category="SERP_INSUFFICIENT",
            )
        payload = _last_update_payload(mock_client)
        assert payload["status"] == "failed"
        assert payload["failure_category"] == "SERP_INSUFFICIENT"
        assert payload["error"] == "serp: 4 pages collected, minimum 5 required"

    def test_failure_category_set_when_skipped(self, mock_client: MagicMock) -> None:
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status(
                "i-1",
                "skipped",
                error="prefilter: search_volume=50<100",
                failure_category="PREFILTER_VOLUME",
            )
        payload = _last_update_payload(mock_client)
        assert payload["failure_category"] == "PREFILTER_VOLUME"

    def test_failure_category_set_when_needs_review(self, mock_client: MagicMock) -> None:
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status(
                "i-1",
                "needs_review",
                failure_category="BODY_SIMILARITY_HIGH",
            )
        payload = _last_update_payload(mock_client)
        assert payload["failure_category"] == "BODY_SIMILARITY_HIGH"

    def test_failure_category_auto_cleared_on_success_transition(
        self, mock_client: MagicMock
    ) -> None:
        # ready_to_publish 는 failure status 아님 → 자동 NULL clear.
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status("i-1", "ready_to_publish")
        payload = _last_update_payload(mock_client)
        assert payload["failure_category"] is None
        # error 도 동일 auto-clear (기존 시맨틱 회귀 방지).
        assert payload["error"] is None

    def test_failure_category_auto_cleared_on_succeeded(self, mock_client: MagicMock) -> None:
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status("i-1", "succeeded")
        payload = _last_update_payload(mock_client)
        assert payload["failure_category"] is None

    def test_failure_category_auto_cleared_on_queued_retry(self, mock_client: MagicMock) -> None:
        # 재시도 시 queued 로 복귀 — 잔존 카테고리 / 에러 모두 clear.
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status(
                "i-1",
                "queued",
                error="[retry 1/2] RuntimeError: serp: 4 pages",
                retry_count=1,
            )
        payload = _last_update_payload(mock_client)
        # error 는 명시적으로 전달했으니 유지.
        assert payload["error"].startswith("[retry 1/2]")
        # failure_category 는 미전달 + queued 는 failure 아님 → auto-clear.
        assert payload["failure_category"] is None

    def test_failure_category_preserved_on_needs_review_without_explicit(
        self, mock_client: MagicMock
    ) -> None:
        # needs_review 는 failure status 계열 → 미전달 시 컬럼 자체를 payload 에 넣지 않음.
        # (기존 값 보존 — partial update 시맨틱).
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status("i-1", "needs_review")
        payload = _last_update_payload(mock_client)
        # 명시 전달 안 했고 status 가 failure 계열이므로 컬럼이 payload 에 없음.
        assert "failure_category" not in payload

    def test_graceful_fallback_when_column_missing(self, mock_client: MagicMock) -> None:
        """failure_category 컬럼이 DB 에 없는 환경에서는 컬럼 빼고 retry."""
        # 1차 호출 실패, 2차 retry 성공 — execute 가 두 번 호출됨.
        call_count = {"n": 0}

        def execute_side_effect(*_args: Any, **_kwargs: Any) -> Any:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("column 'failure_category' does not exist")
            return MagicMock(data=None)

        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
            execute_side_effect
        )
        with patch("domain.batch.storage.get_client", return_value=mock_client):
            storage.update_item_status(
                "i-1",
                "failed",
                failure_category="EXCEPTION",
            )
        # 2회 호출 (1차 + retry).
        assert call_count["n"] == 2
