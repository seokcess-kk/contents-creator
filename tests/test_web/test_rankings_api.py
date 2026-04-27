"""rankings 라우터 단위 테스트 — orchestrator + storage 모두 mock."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from application import ranking_orchestrator
from domain.ranking import storage
from domain.ranking.model import (
    Publication,
    RankingMatchError,
    RankingSnapshot,
    RankingTimeline,
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPI TestClient — 인증 비활성 + 스케줄러 비활성 모드."""
    # 스케줄러는 lifespan 비용이 높으니 테스트에서는 끔
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    # 인증 비활성 (admin_api_key None) — auth.py 가 _warned 로 한 번 경고 후 통과
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)

    from web.api.main import app

    return TestClient(app)


def _publication(**overrides: Any) -> Publication:
    base = {
        "id": "pub-1",
        "keyword": "kw",
        "slug": "kw-slug",
        "url": "https://m.blog.naver.com/u/123456789",
    }
    base.update(overrides)
    return Publication(**base)


class TestPostPublications:
    def test_creates_publication(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ranking_orchestrator,
            "register_publication",
            lambda **_: _publication(),
        )
        resp = client.post(
            "/api/rankings/publications",
            json={
                "keyword": "다이어트 한의원",
                "slug": "diet-hanuiwon",
                "url": "https://blog.naver.com/u/123456789",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "pub-1"

    def test_invalid_url_400(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(**_: Any) -> Publication:
            raise ValueError("네이버 블로그 포스트 URL 형식이 아닙니다")

        monkeypatch.setattr(ranking_orchestrator, "register_publication", _raise)
        resp = client.post(
            "/api/rankings/publications",
            json={"keyword": "kw", "slug": "s", "url": "bad"},
        )
        assert resp.status_code == 400

    def test_creates_external_url_without_slug(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """slug 미제공 — 외부 URL 등록 경로."""
        captured: dict[str, Any] = {}

        def _capture(**kwargs: Any) -> Publication:
            captured.update(kwargs)
            return _publication(slug=None)

        monkeypatch.setattr(ranking_orchestrator, "register_publication", _capture)
        resp = client.post(
            "/api/rankings/publications",
            json={
                "keyword": "다이어트 한의원",
                "url": "https://blog.naver.com/u/123456789",
            },
        )
        assert resp.status_code == 200
        assert captured.get("slug") is None
        assert resp.json()["slug"] is None


class TestListPublications:
    def test_returns_items(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            storage,
            "list_publications",
            lambda keyword=None, limit=50: [_publication()],
        )
        resp = client.get("/api/rankings/publications")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1


class TestGetPublicationWithTimeline:
    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ranking_orchestrator, "get_publication_timeline", lambda *_, **__: None)
        resp = client.get("/api/rankings/publications/pub-x")
        assert resp.status_code == 404

    def test_returns_timeline(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        timeline = RankingTimeline(
            publication=_publication(),
            snapshots=[
                RankingSnapshot(publication_id="pub-1", position=3),
                RankingSnapshot(publication_id="pub-1", position=5),
            ],
        )
        monkeypatch.setattr(
            ranking_orchestrator,
            "get_publication_timeline",
            lambda *_, **__: timeline,
        )
        resp = client.get("/api/rankings/publications/pub-1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["snapshots"]) == 2


class TestPatchPublication:
    def test_updates_keyword(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ranking_orchestrator,
            "update_publication",
            lambda _id, **_: _publication(keyword="updated"),
        )
        resp = client.patch(
            "/api/rankings/publications/pub-1",
            json={"keyword": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["keyword"] == "updated"

    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ranking_orchestrator, "update_publication", lambda *_, **__: None)
        resp = client.patch("/api/rankings/publications/pub-x", json={"keyword": "x"})
        assert resp.status_code == 404

    def test_400_on_invalid_url(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_: Any, **__: Any) -> None:
            raise ValueError("네이버 블로그 포스트 URL 형식이 아닙니다")

        monkeypatch.setattr(ranking_orchestrator, "update_publication", _raise)
        resp = client.patch("/api/rankings/publications/pub-1", json={"url": "bad"})
        assert resp.status_code == 400


class TestDeletePublication:
    def test_204_on_success(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ranking_orchestrator, "delete_publication", lambda _id: True)
        resp = client.delete("/api/rankings/publications/pub-1")
        assert resp.status_code == 204

    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ranking_orchestrator, "delete_publication", lambda _id: False)
        resp = client.delete("/api/rankings/publications/pub-x")
        assert resp.status_code == 404


class TestGetCalendar:
    def test_returns_calendar(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from domain.ranking.model import CalendarRow, RankingCalendar

        cal = RankingCalendar(
            month="2026-04",
            rows=[
                CalendarRow(publication=_publication(), days={"2026-04-10": 5}),
            ],
        )
        monkeypatch.setattr(ranking_orchestrator, "get_monthly_calendar", lambda *_: cal)
        resp = client.get("/api/rankings/calendar?month=2026-04")
        assert resp.status_code == 200
        body = resp.json()
        assert body["month"] == "2026-04"
        assert body["rows"][0]["days"]["2026-04-10"] == 5

    def test_400_on_invalid_format(self, client: TestClient) -> None:
        resp = client.get("/api/rankings/calendar?month=2026-4")
        assert resp.status_code == 422  # FastAPI Query pattern 검증

    def test_400_on_invalid_value(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_: Any, **__: Any) -> None:
            raise ValueError("월은 1~12 범위: 13")

        monkeypatch.setattr(ranking_orchestrator, "get_monthly_calendar", _raise)
        resp = client.get("/api/rankings/calendar?month=2026-13")
        assert resp.status_code == 400


class TestTriggerCheck:
    def test_404_when_missing(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(_: str) -> RankingSnapshot:
            raise ValueError("publication 미존재")

        monkeypatch.setattr(ranking_orchestrator, "check_rankings_for_publication", _raise)
        resp = client.post("/api/rankings/check/pub-x")
        assert resp.status_code == 404

    def test_502_on_match_error(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(_: str) -> RankingSnapshot:
            raise RankingMatchError("network down")

        monkeypatch.setattr(ranking_orchestrator, "check_rankings_for_publication", _raise)
        resp = client.post("/api/rankings/check/pub-1")
        assert resp.status_code == 502


class TestListSnapshots:
    def test_404_when_publication_missing(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage, "get_publication", lambda _: None)
        resp = client.get("/api/rankings/pub-x")
        assert resp.status_code == 404

    def test_returns_snapshots(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(storage, "get_publication", lambda _: _publication())
        monkeypatch.setattr(
            storage,
            "list_snapshots",
            lambda _id, limit=90: [
                RankingSnapshot(publication_id="pub-1", position=1),
            ],
        )
        resp = client.get("/api/rankings/pub-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1


class TestAuthEnforcement:
    def test_401_when_api_key_set_and_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", "secret-test-key")
        # auth 모듈의 _warned flag 가 이전 테스트에서 True 일 수 있음 — 리셋
        monkeypatch.setattr("web.api.auth._warned", False)
        from web.api.main import app

        with TestClient(app) as c:
            resp = c.get("/api/rankings/publications")
            assert resp.status_code == 401

    def test_200_when_correct_key_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", "secret-test-key")
        monkeypatch.setattr(storage, "list_publications", lambda keyword=None, limit=50: [])
        from web.api.main import app

        with TestClient(app) as c:
            resp = c.get(
                "/api/rankings/publications",
                headers={"X-API-Key": "secret-test-key"},
            )
            assert resp.status_code == 200
