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

    def test_json_passes_prefilter_options(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase B8 — JSON 본문의 사전 필터/cluster 옵션이 enqueue_from_csv 로 전달."""
        captured: dict[str, Any] = {}

        def _capture(csv_text: str, **kwargs: Any) -> BatchEnqueueResult:
            captured.update(kwargs)
            return BatchEnqueueResult(batch_id="b-x", total=1, created=1, skipped=[], failed=[])

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _capture)
        resp = client.post(
            "/api/batches",
            json={
                "csv_text": "keyword\nkw1\n",
                "mode": "now",
                "min_search_volume": 200,
                "max_difficulty": "MEDIUM",
                "cluster_dedupe": True,
            },
        )
        assert resp.status_code == 202
        assert captured["min_search_volume"] == 200
        assert captured["max_difficulty"] == "MEDIUM"
        assert captured["cluster_dedupe"] is True

    def test_json_default_cluster_dedupe_off(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """cluster_dedupe 미지정 시 default False (보수적)."""
        captured: dict[str, Any] = {}

        def _capture(csv_text: str, **kwargs: Any) -> BatchEnqueueResult:
            captured.update(kwargs)
            return BatchEnqueueResult(batch_id="b-x", total=1, created=1, skipped=[], failed=[])

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _capture)
        resp = client.post("/api/batches", json={"csv_text": "keyword\nkw1\n", "mode": "now"})
        assert resp.status_code == 202
        assert captured["cluster_dedupe"] is False
        assert captured["min_search_volume"] is None
        assert captured["max_difficulty"] is None

    def test_multipart_passes_prefilter_options(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """multipart form data 도 동일 옵션 전달."""
        captured: dict[str, Any] = {}

        def _capture(csv_text: str, **kwargs: Any) -> BatchEnqueueResult:
            captured.update(kwargs)
            return BatchEnqueueResult(batch_id="b-y", total=1, created=1, skipped=[], failed=[])

        monkeypatch.setattr(batch_orchestrator, "enqueue_from_csv", _capture)
        files = {"csv_file": ("kw.csv", b"keyword\nkw1\n", "text/csv")}
        resp = client.post(
            "/api/batches",
            files=files,
            data={
                "mode": "now",
                "min_search_volume": "300",
                "max_difficulty": "HIGH",
                "cluster_dedupe": "true",
            },
        )
        assert resp.status_code == 202
        assert captured["min_search_volume"] == 300
        assert captured["max_difficulty"] == "HIGH"
        assert captured["cluster_dedupe"] is True
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

    def test_response_includes_keyword_slug(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase B7 — 응답 item 에 keyword_slug enrich (frontend 직링크용)."""
        from application.orchestrator import _slugify

        monkeypatch.setattr(storage, "get_batch", lambda _: _batch())
        monkeypatch.setattr(
            storage,
            "list_items",
            lambda _id, **_: [_item(id="i-1", keyword="강남 다이어트 한의원")],
        )
        resp = client.get("/api/batches/b-1/items")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"][0]["keyword_slug"] == _slugify("강남 다이어트 한의원")


class TestReviewQueue:
    """Phase B9 PR3 — 검수 큐 GET / 액션 POST."""

    def test_list_review_queue_with_keyword_slug_enrich(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from application.orchestrator import _slugify

        monkeypatch.setattr(storage, "get_batch", lambda _: _batch())
        monkeypatch.setattr(
            storage,
            "list_review_pending_items",
            lambda _id, **_: [_item(id="i-1", keyword="강남 다이어트")],
        )
        resp = client.get("/api/batches/b-1/review")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["items"][0]["keyword_slug"] == _slugify("강남 다이어트")

    def test_review_approve_transitions_status(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Phase B9 fix — review API 가 batch_id 소속 검증을 위해 get_item 호출.
        monkeypatch.setattr(storage, "get_item", lambda _: _item(id="i-1", batch_id="b-1"))
        captured: dict[str, Any] = {}

        def _capture(item_id: str, **kwargs: Any) -> None:
            captured["item_id"] = item_id
            captured.update(kwargs)

        monkeypatch.setattr(storage, "update_item_review", _capture)
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "approve", "reviewer": "alice"},
        )
        assert resp.status_code == 200
        assert captured["review_status"] == "approved"
        assert captured["status"] == "ready_to_publish"
        assert captured["reviewer"] == "alice"

    def test_review_needs_fix_keeps_status(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_item", lambda _: _item(id="i-1", batch_id="b-1"))
        captured: dict[str, Any] = {}

        monkeypatch.setattr(
            storage,
            "update_item_review",
            lambda item_id, **kwargs: captured.update({"item_id": item_id, **kwargs}),
        )
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "needs_fix"},
        )
        assert resp.status_code == 200
        assert captured["review_status"] == "needs_fix"
        assert captured["status"] is None  # status 그대로

    def test_review_reject_keeps_status(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_item", lambda _: _item(id="i-1", batch_id="b-1"))
        captured: dict[str, Any] = {}
        monkeypatch.setattr(
            storage,
            "update_item_review",
            lambda item_id, **kwargs: captured.update(kwargs),
        )
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "reject"},
        )
        assert resp.status_code == 200
        assert captured["review_status"] == "rejected"
        assert captured["status"] is None

    def test_review_invalid_action_returns_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "publish"},  # invalid
        )
        assert resp.status_code == 400

    def test_review_item_missing_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase B9 fix — item 미존재 → 404."""
        monkeypatch.setattr(storage, "get_item", lambda _: None)
        called = {"count": 0}
        monkeypatch.setattr(
            storage,
            "update_item_review",
            lambda *_a, **_k: called.update({"count": called["count"] + 1}),
        )
        resp = client.post(
            "/api/batches/b-1/items/missing/review",
            json={"action": "approve"},
        )
        assert resp.status_code == 404
        assert called["count"] == 0  # update 호출 안 됨

    def test_review_batch_mismatch_returns_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase B9 fix — item.batch_id != batch_id → 404, 다른 batch 의 item 변경 차단."""
        monkeypatch.setattr(storage, "get_item", lambda _: _item(id="i-1", batch_id="b-OTHER"))
        called = {"count": 0}
        monkeypatch.setattr(
            storage,
            "update_item_review",
            lambda *_a, **_k: called.update({"count": called["count"] + 1}),
        )
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "approve"},
        )
        assert resp.status_code == 404
        assert called["count"] == 0  # update 호출 안 됨

    def test_review_batch_match_proceeds(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """item.batch_id == batch_id 면 정상 처리."""
        monkeypatch.setattr(storage, "get_item", lambda _: _item(id="i-1", batch_id="b-1"))
        called: dict[str, Any] = {}
        monkeypatch.setattr(
            storage,
            "update_item_review",
            lambda item_id, **kwargs: called.update({"item_id": item_id, **kwargs}),
        )
        resp = client.post(
            "/api/batches/b-1/items/i-1/review",
            json={"action": "approve"},
        )
        assert resp.status_code == 200
        assert called["review_status"] == "approved"


class TestBackfillFk:
    """Phase B10 PR4 — POST /backfill-fk 동기 응답 검증."""

    def test_returns_match_counts(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            batch_orchestrator,
            "backfill_unlinked_items",
            lambda _id: {
                "matched_pattern_cards": 2,
                "matched_generated_contents": 3,
                "still_unlinked": 1,
            },
        )
        resp = client.post("/api/batches/b-1/backfill-fk")
        assert resp.status_code == 200
        body = resp.json()
        assert body["batch_id"] == "b-1"
        assert body["matched_pattern_cards"] == 2
        assert body["matched_generated_contents"] == 3
        assert body["still_unlinked"] == 1


class TestGetBatchReadyToPublishCount:
    """Phase B9 PR3 — GET /batches/{id} 응답에 ready_to_publish_count 항상 포함."""

    def test_response_includes_ready_to_publish_count(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_batch", lambda _: _batch())
        monkeypatch.setattr(
            storage,
            "count_items_by_status",
            lambda _id: {
                "succeeded_count": 1,
                "failed_count": 0,
                "skipped_count": 0,
                "needs_review_count": 1,
                "ready_to_publish_count": 3,
            },
        )
        resp = client.get("/api/batches/b-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ready_to_publish_count"] == 3
        assert body["needs_review_count"] == 1


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


class TestSupabaseFailureHandling:
    """Supabase 미설정·테이블 미존재·연결 실패 케이스의 graceful 처리.

    2026-05-04 /batches 페이지 진입 시 500 에러 사고 후속 — 마이그레이션 미적용
    상태에서도 페이지가 깨지지 않고, 운영자가 detail 메시지로 원인 인지 가능해야.
    """

    def test_list_batches_returns_empty_when_supabase_not_configured(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.supabase_url", "")
        monkeypatch.setattr("config.settings.settings.supabase_key", "")
        resp = client.get("/api/batches")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["items"] == []
        assert "warning" in body

    def test_list_batches_returns_503_when_table_missing(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Postgres 'relation X does not exist' 에러 → 503 + 마이그레이션 안내."""
        monkeypatch.setattr("config.settings.settings.supabase_url", "https://x.supabase.co")
        monkeypatch.setattr("config.settings.settings.supabase_key", "test-key")

        def _raise(limit: int = 20) -> list:
            raise RuntimeError('relation "public.keyword_batches" does not exist')

        monkeypatch.setattr(storage, "list_batches", _raise)
        resp = client.get("/api/batches")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert "마이그레이션" in detail
        assert "schema.sql" in detail

    def test_list_batches_returns_503_with_generic_error(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """테이블 미존재 외 일반 Supabase 에러도 500 대신 503."""
        monkeypatch.setattr("config.settings.settings.supabase_url", "https://x.supabase.co")
        monkeypatch.setattr("config.settings.settings.supabase_key", "test-key")
        monkeypatch.setattr(
            storage,
            "list_batches",
            lambda limit=20: (_ for _ in ()).throw(ConnectionError("network unreachable")),
        )
        resp = client.get("/api/batches")
        assert resp.status_code == 503
        assert "ConnectionError" in resp.json()["detail"]


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
