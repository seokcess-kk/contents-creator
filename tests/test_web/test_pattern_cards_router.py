"""pattern_cards 라우터 테스트 — Supabase client mock."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)
    from web.api.main import app

    return TestClient(app)


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "pc-1",
        "keyword": "강남 다이어트 한의원",
        "slug": "강남-다이어트-한의원",
        "analyzed_count": 8,
        "created_at": "2026-05-04T10:00:00",
        "output_path": "/tmp/output",
        "data": {"schema_version": "2.0", "keyword": "강남 다이어트 한의원"},
    }
    base.update(overrides)
    return base


def _make_client(rows: list[dict[str, Any]]) -> MagicMock:
    """Supabase client chain mock — execute().data 가 rows 반환."""
    client = MagicMock()
    chain = client.table.return_value
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=rows)
    return client


def _patch_supabase(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]) -> MagicMock:
    monkeypatch.setattr("config.settings.settings.supabase_url", "https://stub.supabase.co")
    monkeypatch.setattr("config.settings.settings.supabase_key", "stub-key")
    client = _make_client(rows)
    monkeypatch.setattr("web.api.routers.pattern_cards.get_client", lambda: client)
    return client


class TestListRecent:
    def test_returns_rows(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_supabase(monkeypatch, [_row()])
        resp = client.get("/api/pattern-cards/recent?limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["items"][0]["id"] == "pc-1"
        # data 는 list 응답에서 제외 (가벼움 우선)
        assert "data" not in body["items"][0]

    def test_supabase_unconfigured_returns_empty_warning(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.supabase_url", None)
        monkeypatch.setattr("config.settings.settings.supabase_key", None)
        resp = client.get("/api/pattern-cards/recent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["items"] == []
        assert "warning" in body


class TestGetById:
    def test_returns_full_detail(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_supabase(monkeypatch, [_row()])
        resp = client.get("/api/pattern-cards/by-id/pc-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "pc-1"
        assert body["data"]["schema_version"] == "2.0"

    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_supabase(monkeypatch, [])
        resp = client.get("/api/pattern-cards/by-id/missing")
        assert resp.status_code == 404

    def test_503_when_table_missing(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("config.settings.settings.supabase_url", "https://stub.supabase.co")
        monkeypatch.setattr("config.settings.settings.supabase_key", "stub-key")
        c = MagicMock()
        c.table.side_effect = RuntimeError('relation "pattern_cards" does not exist')
        monkeypatch.setattr("web.api.routers.pattern_cards.get_client", lambda: c)
        resp = client.get("/api/pattern-cards/by-id/pc-x")
        assert resp.status_code == 503
        assert "마이그레이션" in resp.json()["detail"]


class TestGetBySlugLatest:
    def test_returns_latest(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_supabase(monkeypatch, [_row()])
        resp = client.get("/api/pattern-cards/by-slug/강남-다이어트-한의원/latest")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "강남-다이어트-한의원"

    def test_404_when_no_match(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_supabase(monkeypatch, [])
        resp = client.get("/api/pattern-cards/by-slug/none/latest")
        assert resp.status_code == 404
