"""batches 라우터 테스트 — orchestrator + storage 모두 mock."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from application import batch_orchestrator
from domain.batch import storage
from domain.batch.model import (
    BatchEnqueueResult,
    KeywordBatch,
    KeywordBatchItem,
    NotSupportedYetError,
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)
    from web.api.main import app

    return TestClient(app)


def _batch(**overrides: Any) -> KeywordBatch:
    base: dict[str, Any] = {"id": "b-1", "total_count": 5}
    base.update(overrides)
    return KeywordBatch(**base)


def _item(**overrides: Any) -> KeywordBatchItem:
    base: dict[str, Any] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "operation": "analyze",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)


class TestCreateBatch:
    def test_json_csv_text_creates_batch(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            batch_orchestrator,
            "enqueue_from_csv",
            lambda csv_text, **_: BatchEnqueueResult(
                batch_id="b-new", total=1, created=1, skipped=[], failed=[]
            ),
        )
        resp = client.post(
            "/api/batches",
            json={"csv_text": "keyword\nkw1\n", "mode": "now", "name": "t"},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["batch_id"] == "b-new"
        assert body["created"] == 1

    def test_multipart_csv_file_creates_batch(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        def _capture(csv_text: str, **kwargs: Any) -> BatchEnqueueResult:
            captured["csv_text"] = csv_text
            captured.update(kwargs)
            return BatchEnqueueResult(batch_id="b-multi", total=2, created=2, skipped=[], failed=[])

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _capture)
        files = {"csv_file": ("kw.csv", b"keyword\nkw1\nkw2\n", "text/csv")}
        resp = client.post("/api/batches", files=files, data={"mode": "now"})
        assert resp.status_code == 202
        assert "kw1" in captured["csv_text"]
        assert captured["mode"] == "now"

    def test_overnight_mode_returns_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_: Any, **__: Any) -> BatchEnqueueResult:
            raise NotSupportedYetError("Phase 1 은 mode='now' 만 지원합니다.")

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _raise)
        resp = client.post(
            "/api/batches",
            json={"csv_text": "keyword\nkw\n", "mode": "overnight"},
        )
        assert resp.status_code == 400
        assert "now" in resp.json()["detail"]

    def test_csv_format_error_returns_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_: Any, **__: Any) -> BatchEnqueueResult:
            raise ValueError("필수 컬럼 누락: keyword")

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _raise)
        resp = client.post("/api/batches", json={"csv_text": "operation\nanalyze\n"})
        assert resp.status_code == 400

    def test_missing_body_returns_400(self, client: TestClient) -> None:
        """csv_file 도 csv_text 도 없으면 400."""
        resp = client.post("/api/batches")
        assert resp.status_code == 400


class TestListBatches:
    def test_returns_recent_batches(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            storage,
            "list_batches",
            lambda limit=20: [_batch(id="b-1"), _batch(id="b-2")],
        )
        resp = client.get("/api/batches")
        assert resp.status_code == 200
        assert resp.json()["count"] == 2


class TestGetBatch:
    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(storage, "get_batch", lambda _: None)
        resp = client.get("/api/batches/missing")
        assert resp.status_code == 404

    def test_includes_realtime_counters(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_batch", lambda _: _batch())
        monkeypatch.setattr(
            storage,
            "count_items_by_status",
            lambda _: {
                "succeeded_count": 3,
                "failed_count": 1,
                "skipped_count": 0,
                "needs_review_count": 0,
            },
        )
        resp = client.get("/api/batches/b-1")
        assert resp.status_code == 200
        body = resp.json()
        # 실시간 counters 가 응답에 머지
        assert body["succeeded_count"] == 3
        assert body["failed_count"] == 1


class TestListBatchItems:
    def test_returns_items_with_status_filter(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_batch", lambda _: _batch())

        def _list(_id: str, *, status: str | None = None, limit: int = 200) -> list:
            assert status == "failed"
            return [_item(id="i-1", status="failed")]

        monkeypatch.setattr(storage, "list_items", _list)
        resp = client.get("/api/batches/b-1/items?status=failed")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestCancelBatch:
    def test_returns_cancelled_count(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(batch_orchestrator, "cancel_batch", lambda _: 7)
        resp = client.post("/api/batches/b-1/cancel")
        assert resp.status_code == 200
        assert resp.json()["cancelled_count"] == 7

    def test_404_when_batch_missing(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(_: str) -> int:
            raise ValueError("batch 미존재")

        monkeypatch.setattr(batch_orchestrator, "cancel_batch", _raise)
        resp = client.post("/api/batches/missing/cancel")
        assert resp.status_code == 404


class TestRetryItem:
    def test_returns_202_on_success(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(batch_orchestrator, "retry_item", lambda _: None)
        resp = client.post("/api/batches/b-1/items/i-1/retry")
        assert resp.status_code == 202

    def test_400_when_invalid_state(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(_: str) -> None:
            raise ValueError("재시도 가능 상태 아님 (현재: running)")

        monkeypatch.setattr(batch_orchestrator, "retry_item", _raise)
        resp = client.post("/api/batches/b-1/items/i-1/retry")
        assert resp.status_code == 400
