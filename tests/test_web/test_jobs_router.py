"""Phase J2 PR3 — GET /api/jobs/{id} DB fallback 회귀.

검증:
1. in-memory hit → 200 + Job 응답 (기존 동작)
2. in-memory miss + flag off → 404 (DB 조회 안 함)
3. in-memory miss + flag on + DB miss → 404
4. in-memory miss + flag on + DB hit (orphaned) → 200 + status="orphaned"
5. DB row 의 datetime 직렬화 (Supabase ISO8601 → datetime 변환)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)
    from web.api.main import app

    return TestClient(app)


def _orphaned_row(job_id: str = "abc123def456") -> dict:
    return {
        "id": job_id,
        "type": "pipeline",
        "status": "orphaned",
        "keyword": "다이어트",
        "params": {"keyword": "다이어트"},
        "result": None,
        "error": "container restart — in-memory state lost",
        "created_at": "2026-05-08T10:00:00+00:00",
        "started_at": "2026-05-08T10:00:05+00:00",
        "finished_at": "2026-05-08T10:30:00+00:00",
        "last_heartbeat": "2026-05-08T10:25:00+00:00",
        "instance_id": "render-srv-1",
    }


class TestGetJobInMemoryHit:
    def test_returns_in_memory_job(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # in-memory 에 있는 job 은 DB 조회 없이 즉시 반환
        from web.api.main import job_manager

        get_mock = MagicMock()
        monkeypatch.setattr("web.api.routers.jobs.job_store.get_job", get_mock)

        # _submit 회피 — 직접 dict 에 Job 주입
        from datetime import UTC, datetime

        from web.api.job_manager import Job

        job = Job(id="memhit", type="analyze", keyword="kw", status="running")
        job.created_at = datetime.now(tz=UTC)
        job_manager._jobs["memhit"] = job
        try:
            resp = client.get("/api/jobs/memhit")
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == "memhit"
            assert body["status"] == "running"
            # DB 조회 없이 응답
            assert get_mock.call_count == 0
        finally:
            del job_manager._jobs["memhit"]


class TestGetJobMissFlagOff:
    def test_returns_404_without_db_call(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        get_mock = MagicMock(return_value=_orphaned_row())
        monkeypatch.setattr("web.api.routers.jobs.job_store.get_job", get_mock)

        resp = client.get("/api/jobs/nonexistent")
        assert resp.status_code == 404
        # flag off 라 DB 조회 자체 안 함
        assert get_mock.call_count == 0


class TestGetJobMissFlagOnDbMiss:
    def test_returns_404_when_db_also_empty(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        get_mock = MagicMock(return_value=None)
        monkeypatch.setattr("web.api.routers.jobs.job_store.get_job", get_mock)

        resp = client.get("/api/jobs/nonexistent")
        assert resp.status_code == 404
        assert get_mock.call_count == 1


class TestGetJobMissFlagOnDbHit:
    def test_returns_orphaned_row(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        row = _orphaned_row("orph123")
        monkeypatch.setattr("web.api.routers.jobs.job_store.get_job", MagicMock(return_value=row))

        resp = client.get("/api/jobs/orph123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "orph123"
        assert body["status"] == "orphaned"
        assert body["keyword"] == "다이어트"
        assert body["error"] == "container restart — in-memory state lost"
        # ISO8601 → JobResponse datetime 직렬화 확인
        assert body["created_at"].startswith("2026-05-08T10:00:00")
        assert body["finished_at"].startswith("2026-05-08T10:30:00")
        # progress 는 빈 list (PR3 범위 밖)
        assert body["progress"] == []
