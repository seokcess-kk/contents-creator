"""brand_studio 라우터 통합 테스트 — orchestrator/storage 모두 mock."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from domain.brand_card.model import (
    BrandCardPlan,
    BrandMessageSource,
    BrandProfile,
    CardBlock,
    CardCampaignInput,
    StatusTransitionError,
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPI TestClient — 인증 비활성 + 스케줄러 비활성."""
    monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
    monkeypatch.setattr("config.settings.settings.admin_api_key", None)
    from web.api.main import app

    return TestClient(app)


def _profile(**overrides: Any) -> BrandProfile:
    base: dict[str, Any] = {
        "id": "brand-1",
        "name": "테스트의원",
        "slug": "test-clinic",
        "homepage_url": "https://example.com",
    }
    base.update(overrides)
    return BrandProfile(**base)


def _plan(strategy: str = "trust_first", plan_id: str = "p-1") -> BrandCardPlan:
    return BrandCardPlan(
        id=plan_id,
        brand_id="brand-1",
        keyword="kw",
        strategy=strategy,
        expression_level="balanced",
        template_id="clinic_trust",
        angle="...",
        blocks=[
            CardBlock(
                card_type="hero",
                headline=f"{strategy} 헤드",
                recommended_position="after_intro",
            ),
        ],
        reuse_group_id="g-1",
        status="draft",
    )


# ── 1. GET /brands ──────────────────────────────────────────


class TestListBrands:
    def test_returns_brands(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "list_brands", lambda: [_profile()])
        resp = client.get("/api/brand-studio/brands")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["slug"] == "test-clinic"

    def test_empty_returns_empty_list(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "list_brands", lambda: [])
        resp = client.get("/api/brand-studio/brands")
        assert resp.status_code == 200
        assert resp.json() == []


# ── 2-3. sources ────────────────────────────────────────────


class TestSources:
    def test_list_unknown_brand_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.get("/api/brand-studio/brands/missing/sources")
        assert resp.status_code == 404

    def test_list_returns_sources(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(
            brand_studio.storage,
            "list_message_sources",
            lambda _id: [
                BrandMessageSource(id="s-1", brand_id="brand-1", source_type="brand_common"),
            ],
        )
        resp = client.get("/api/brand-studio/brands/brand-1/sources")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_upload_unknown_brand_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.post(
            "/api/brand-studio/brands/missing/sources",
            files={"file": ("test.txt", b"content", "text/plain")},
        )
        assert resp.status_code == 404

    def test_upload_empty_file_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_unsupported_extension_415(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(brand_studio, "_ASSET_ROOT", tmp_path)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources",
            files={"file": ("evil.exe", b"binary", "application/octet-stream")},
        )
        assert resp.status_code == 415

    def test_upload_text_persists(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(brand_studio, "_ASSET_ROOT", tmp_path)

        captured: dict[str, Any] = {}

        def fake_insert(record: BrandMessageSource) -> BrandMessageSource:
            captured["record"] = record
            return record.model_copy(update={"id": "s-new"})

        monkeypatch.setattr(brand_studio.storage, "insert_message_source", fake_insert)

        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources",
            files={"file": ("hello.txt", "안녕하세요".encode(), "text/plain")},
            data={"source_type": "campaign"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == "s-new"
        assert captured["record"].source_type == "campaign"
        assert "안녕" in (captured["record"].content_text or "")


# ── 4. campaign-inputs ──────────────────────────────────────


class TestCampaignInput:
    def test_save(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        captured: dict[str, Any] = {}

        def fake_insert(ci: CardCampaignInput) -> CardCampaignInput:
            captured["ci"] = ci
            return ci.model_copy(update={"id": "ci-1"})

        monkeypatch.setattr(brand_studio.storage, "insert_campaign_input", fake_insert)

        resp = client.post(
            "/api/brand-studio/brands/brand-1/campaign-inputs",
            json={
                "keyword": "다이어트 한약",
                "expression_level": "hooking",
                "required_phrases": ["체질"],
                "forbidden_phrases": ["수술"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "ci-1"
        assert captured["ci"].expression_level == "hooking"


# ── 5. POST /plans ──────────────────────────────────────────


class TestGeneratePlans:
    def test_unknown_brand_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.post(
            "/api/brand-studio/brands/missing/plans",
            json={"keyword": "kw"},
        )
        assert resp.status_code == 404

    def test_generates_plans(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(
            brand_studio.orch,
            "generate_card_plan",
            lambda **_: [_plan("trust_first"), _plan("empathy_first", "p-2")],
        )
        resp = client.post(
            "/api/brand-studio/brands/brand-1/plans",
            json={"keyword": "kw", "strategy_count": 2},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body) == 2
        assert {p["strategy"] for p in body} == {"trust_first", "empathy_first"}

    def test_invalid_strategy_count_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        def _raise(**_: Any) -> list[BrandCardPlan]:
            raise ValueError("strategy_count 는 1~4")

        monkeypatch.setattr(brand_studio.orch, "generate_card_plan", _raise)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/plans",
            json={"keyword": "kw", "strategy_count": 5},
        )
        assert resp.status_code == 400


# ── 6. GET /plans/{group_id} ────────────────────────────────


class TestGetPlans:
    def test_returns_plans(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [_plan()],
        )
        resp = client.get("/api/brand-studio/plans/g-1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_no_plans_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [],
        )
        resp = client.get("/api/brand-studio/plans/g-missing")
        assert resp.status_code == 404


# ── 7. approve / reject ─────────────────────────────────────


class TestApproveReject:
    def test_approve(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        approved = _plan().model_copy(update={"status": "approved"})
        monkeypatch.setattr(brand_studio.orch, "approve_plan", lambda _id: approved)
        resp = client.post("/api/brand-studio/plans/p-1/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        rejected = _plan().model_copy(update={"status": "rejected"})
        monkeypatch.setattr(brand_studio.orch, "reject_plan", lambda _id: rejected)
        resp = client.post("/api/brand-studio/plans/p-1/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_approve_missing_plan_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.orch, "approve_plan", lambda _id: None)
        resp = client.post("/api/brand-studio/plans/p-missing/approve")
        assert resp.status_code == 404

    def test_approve_invalid_transition_409(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        def _raise(_id: str) -> BrandCardPlan:
            raise StatusTransitionError("can't transition")

        monkeypatch.setattr(brand_studio.orch, "approve_plan", _raise)
        resp = client.post("/api/brand-studio/plans/p-1/approve")
        assert resp.status_code == 409


# ── 8. POST /plans/{group_id}/render ────────────────────────


class TestSubmitRender:
    def test_no_plans_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [],
        )
        resp = client.post("/api/brand-studio/plans/g-missing/render", json={})
        assert resp.status_code == 404

    def test_no_approved_409(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [_plan()],  # status=draft
        )
        resp = client.post("/api/brand-studio/plans/g-1/render", json={})
        assert resp.status_code == 409

    def test_submits_job(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import MagicMock

        from web.api.routers import brand_studio

        approved = _plan().model_copy(update={"status": "approved"})
        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [approved],
        )

        from web.api import main as main_module

        fake_job = MagicMock()
        fake_job.id = "job-xyz"
        monkeypatch.setattr(
            main_module.job_manager,
            "submit_brand_card_render",
            lambda params: fake_job,
        )

        resp = client.post(
            "/api/brand-studio/plans/g-1/render",
            json={"brand_name": "테스트", "brand_url": "https://x"},
        )
        assert resp.status_code == 202
        assert resp.json()["job_id"] == "job-xyz"


# ── 9. GET /cards/{group_id} ────────────────────────────────


class TestArchive:
    def test_no_cards_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [],
        )
        resp = client.get("/api/brand-studio/cards/g-missing")
        assert resp.status_code == 404

    def test_returns_8_fields(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        plan = _plan()
        plan = plan.model_copy(
            update={
                "source_summary": {
                    "compliance_report": {"passed": True, "iterations": 0},
                },
            },
        )
        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [plan],
        )
        # _resolve_output_root 를 직접 mock — settings 필드 의존성 회피
        monkeypatch.setattr(
            brand_studio,
            "_resolve_output_root",
            lambda: tmp_path / "brand_cards",
        )
        # 가짜 PNG 1개 배치
        cards_dir = tmp_path / "brand_cards" / "g-1" / "cards"
        cards_dir.mkdir(parents=True)
        (cards_dir / "card-clinic_trust-trust_first-01.png").write_bytes(b"\x89PNG")

        resp = client.get("/api/brand-studio/cards/g-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reuse_group_id"] == "g-1"
        assert len(body["items"]) == 1
        item = body["items"][0]
        # SPEC §14 결과 화면 8 항목 정합 — headline/blocks/compliance/recommended 등
        for key in (
            "plan_id",
            "template_id",
            "strategy",
            "headline",
            "blocks",
            "compliance_report",
            "recommended_position",
            "reuse_group_id",
            "png_paths",
        ):
            assert key in item, f"missing field {key}"
        assert item["compliance_report"]["passed"] is True
        assert len(item["png_paths"]) == 1


# ── 인증 ────────────────────────────────────────────────────


class TestAuth:
    def test_missing_api_key_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """admin_api_key 가 설정된 환경에서 키 미제공 시 401."""
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", "secret-key")
        from web.api.main import app

        client = TestClient(app)
        resp = client.get("/api/brand-studio/brands")
        assert resp.status_code == 401

    def test_valid_api_key_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", "secret-key")
        from web.api.main import app
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "list_brands", lambda: [])

        client = TestClient(app)
        resp = client.get(
            "/api/brand-studio/brands",
            headers={"X-API-Key": "secret-key"},
        )
        assert resp.status_code == 200
