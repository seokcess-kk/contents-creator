"""Phase J2 PR1 — web/api/job_store.py 회귀.

graceful degrade 우선 검증: Supabase 호출 실패 / 미설정 / 부재 시에도 본 흐름이
차단되지 않는지 확인. 실제 SQL 동작은 staging 검증으로 위임.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from web.api import job_store


def _chain(execute_data: list[dict[str, Any]] | None = None) -> MagicMock:
    """Supabase client chain mock — execute().data 가 execute_data 반환."""
    client = MagicMock()
    chain = client.table.return_value
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=execute_data or [])
    return client


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: MagicMock) -> None:
    monkeypatch.setattr("web.api.job_store.get_client", lambda: client)


class TestInsertJob:
    def test_success_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([{"id": "abc"}])
        _patch_client(monkeypatch, client)
        ok = job_store.insert_job(
            "abc",
            job_type="pipeline",
            keyword="다이어트",
            params={"keyword": "다이어트"},
            instance_id="render-srv-1",
        )
        assert ok is True
        client.table.assert_called_with("jobs")
        # insert payload 검증
        insert_args = client.table.return_value.insert.call_args
        payload = insert_args.args[0]
        assert payload["id"] == "abc"
        assert payload["type"] == "pipeline"
        assert payload["status"] == "pending"
        assert payload["keyword"] == "다이어트"
        assert payload["params"] == {"keyword": "다이어트"}
        assert payload["instance_id"] == "render-srv-1"

    def test_supabase_failure_returns_false_no_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("supabase down")
        _patch_client(monkeypatch, client)
        ok = job_store.insert_job("abc", job_type="pipeline")
        assert ok is False

    def test_no_instance_id_optional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([])
        _patch_client(monkeypatch, client)
        ok = job_store.insert_job("xyz", job_type="analyze")
        assert ok is True
        payload = client.table.return_value.insert.call_args.args[0]
        assert "instance_id" not in payload


class TestGetJob:
    def test_returns_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        row = {"id": "abc", "type": "pipeline", "status": "running"}
        _patch_client(monkeypatch, _chain([row]))
        result = job_store.get_job("abc")
        assert result == row

    def test_returns_none_when_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _chain([]))
        result = job_store.get_job("missing")
        assert result is None

    def test_supabase_failure_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("table missing")
        _patch_client(monkeypatch, client)
        result = job_store.get_job("abc")
        assert result is None


class TestUpdateJobStatus:
    def test_status_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([])
        _patch_client(monkeypatch, client)
        ok = job_store.update_job_status("abc", "running")
        assert ok is True
        payload = client.table.return_value.update.call_args.args[0]
        assert payload == {"status": "running"}

    def test_terminal_with_metadata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from datetime import UTC, datetime

        client = _chain([])
        _patch_client(monkeypatch, client)
        finished = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
        ok = job_store.update_job_status(
            "abc",
            "succeeded",
            finished_at=finished,
            result={"slug": "다이어트-한의원", "images_generated": 3},
        )
        assert ok is True
        payload = client.table.return_value.update.call_args.args[0]
        assert payload["status"] == "succeeded"
        assert payload["finished_at"] == "2026-05-08T12:00:00+00:00"
        assert payload["result"] == {"slug": "다이어트-한의원", "images_generated": 3}

    def test_failure_with_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([])
        _patch_client(monkeypatch, client)
        ok = job_store.update_job_status("abc", "failed", error="brightdata 4xx")
        assert ok is True
        payload = client.table.return_value.update.call_args.args[0]
        assert payload["status"] == "failed"
        assert payload["error"] == "brightdata 4xx"

    def test_supabase_failure_graceful(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("supabase 503")
        _patch_client(monkeypatch, client)
        ok = job_store.update_job_status("abc", "running")
        assert ok is False  # 본 흐름은 차단 안 됨


class TestUpdateHeartbeat:
    def test_sets_now(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([])
        _patch_client(monkeypatch, client)
        ok = job_store.update_heartbeat("abc")
        assert ok is True
        payload = client.table.return_value.update.call_args.args[0]
        assert "last_heartbeat" in payload
        # ISO 8601 형식 확인
        assert "T" in payload["last_heartbeat"]

    def test_supabase_failure_graceful(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("conn timeout")
        _patch_client(monkeypatch, client)
        ok = job_store.update_heartbeat("abc")
        assert ok is False


class TestAppendProgressEvent:
    def test_inserts_with_seq(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([])
        _patch_client(monkeypatch, client)
        ok = job_store.append_progress_event(
            "abc", 5, {"type": "stage_progress", "current": 3, "total": 7}
        )
        assert ok is True
        client.table.assert_called_with("progress_events")
        payload = client.table.return_value.insert.call_args.args[0]
        assert payload == {
            "job_id": "abc",
            "seq": 5,
            "event": {"type": "stage_progress", "current": 3, "total": 7},
        }

    def test_supabase_failure_graceful(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("PK collision")
        _patch_client(monkeypatch, client)
        ok = job_store.append_progress_event("abc", 1, {"type": "x"})
        assert ok is False


class TestListOrphanedJobs:
    def test_returns_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [
            {"id": "a", "status": "orphaned", "finished_at": "2026-05-08T10:00:00Z"},
            {"id": "b", "status": "orphaned", "finished_at": "2026-05-08T09:00:00Z"},
        ]
        _patch_client(monkeypatch, _chain(rows))
        result = job_store.list_orphaned_jobs(limit=10)
        assert len(result) == 2
        assert result[0]["id"] == "a"

    def test_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("supabase down")
        _patch_client(monkeypatch, client)
        result = job_store.list_orphaned_jobs()
        assert result == []


class TestMarkRunningAsOrphaned:
    def test_marks_instance_running(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([{"id": "a"}, {"id": "b"}])
        _patch_client(monkeypatch, client)
        count = job_store.mark_running_as_orphaned(instance_id="render-srv-1")
        assert count == 2
        payload = client.table.return_value.update.call_args.args[0]
        assert payload["status"] == "orphaned"
        assert "container restart" in payload["error"]
        # eq 필터 호출 검증 — instance_id + status
        eq_calls = client.table.return_value.update.return_value.eq.call_args_list
        eq_keys = {c.args[0] for c in eq_calls}
        assert {"instance_id", "status"}.issubset(eq_keys)

    def test_failure_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("supabase down")
        _patch_client(monkeypatch, client)
        count = job_store.mark_running_as_orphaned(instance_id="x")
        assert count == 0


class TestMarkStaleRunningAsOrphaned:
    def test_marks_stale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _chain([{"id": "stale-a"}])
        _patch_client(monkeypatch, client)
        count = job_store.mark_stale_running_as_orphaned(grace_seconds=300)
        assert count == 1
        payload = client.table.return_value.update.call_args.args[0]
        assert payload["status"] == "orphaned"
        assert "300s" in payload["error"]
        # lt 필터 호출 — last_heartbeat 임계 이전
        lt_calls = client.table.return_value.update.return_value.eq.return_value.lt.call_args_list
        assert lt_calls[0].args[0] == "last_heartbeat"

    def test_failure_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = MagicMock()
        client.table.side_effect = RuntimeError("supabase down")
        _patch_client(monkeypatch, client)
        count = job_store.mark_stale_running_as_orphaned(grace_seconds=300)
        assert count == 0
