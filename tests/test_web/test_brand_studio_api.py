"""brand_studio 라우터 통합 테스트 — orchestrator/storage 모두 mock."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from domain.brand_card.model import (
    BrandCardPlan,
    BrandMediaAsset,
    BrandMessageSource,
    BrandProfile,
    CardBlock,
    CardCampaignInput,
    StatusTransitionError,
)
from domain.brand_card.storage_signed import (
    SignedUploadUrl,
    StorageSignedError,
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


def _plan(
    strategy: str = "trust_first",
    plan_id: str = "p-1",
    *,
    keyword: str = "kw",
) -> BrandCardPlan:
    return BrandCardPlan(
        id=plan_id,
        brand_id="brand-1",
        keyword=keyword,
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


# ── 2. POST /brands ─────────────────────────────────────────


class TestRegisterBrand:
    def test_creates_brand(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand_by_slug", lambda _s: None)

        captured: dict[str, Any] = {}

        def fake_insert(profile: BrandProfile) -> BrandProfile:
            captured["profile"] = profile
            return profile.model_copy(update={"id": "brand-new"})

        monkeypatch.setattr(brand_studio.storage, "insert_brand", fake_insert)

        resp = client.post(
            "/api/brand-studio/brands",
            json={
                "name": "신규의원",
                "slug": "new-clinic",
                "homepage_url": "https://newclinic.example.com",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == "brand-new"
        assert body["slug"] == "new-clinic"
        assert captured["profile"].locale == "ko-KR"

    def test_duplicate_slug_409(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "get_brand_by_slug",
            lambda _s: _profile(slug="dup"),
        )
        resp = client.post(
            "/api/brand-studio/brands",
            json={
                "name": "중복",
                "slug": "dup",
                "homepage_url": "https://dup.example.com",
            },
        )
        assert resp.status_code == 409

    def test_invalid_slug_format_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/brand-studio/brands",
            json={
                "name": "X",
                "slug": "BAD SLUG WITH SPACES",
                "homepage_url": "https://x.example.com",
            },
        )
        assert resp.status_code == 422

    def test_missing_required_field_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/brand-studio/brands",
            json={"name": "X", "slug": "x-clinic"},
        )
        assert resp.status_code == 422


# ── 3-4. sources ────────────────────────────────────────────


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


# ── 3-4b. sources presigned (init/confirm) ───────────────────


class TestSourcesPresigned:
    def _payload(self, **overrides: Any) -> dict[str, Any]:
        sha = hashlib.sha256(b"hello world").hexdigest()
        base: dict[str, Any] = {
            "file_name": "doc.txt",
            "file_size": 11,
            "sha256": sha,
            "source_type": "brand_common",
        }
        base.update(overrides)
        return base

    def test_init_unknown_brand_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.post("/api/brand-studio/brands/missing/sources/init", json=self._payload())
        assert resp.status_code == 404

    def test_init_invalid_source_type_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/init",
            json=self._payload(source_type="hack"),
        )
        assert resp.status_code == 422

    def test_init_too_large_413(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr("config.settings.settings.brand_sources_max_bytes", 100)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/init",
            json=self._payload(file_size=999_999),
        )
        assert resp.status_code == 413

    def test_init_unsupported_suffix_415(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/init",
            json=self._payload(file_name="evil.exe"),
        )
        assert resp.status_code == 415

    def test_init_returns_signed_url(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        def fake_create(brand_id: str, sha256: str, suffix: str) -> SignedUploadUrl:
            return SignedUploadUrl(
                upload_url="https://supabase.example/sign/PUT",
                upload_token="tok-1",
                storage_path=f"{brand_id}/sources/{sha256}{suffix}",
                expires_at=datetime.now(UTC) + timedelta(seconds=300),
            )

        monkeypatch.setattr(brand_studio.storage_signed, "create_upload_url", fake_create)
        resp = client.post("/api/brand-studio/brands/brand-1/sources/init", json=self._payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["upload_url"].startswith("https://supabase.example/")
        assert body["storage_path"].startswith("brand-1/sources/")
        assert body["storage_path"].endswith(".txt")

    def test_init_storage_failure_502(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        def fake_create(*_a: Any, **_k: Any) -> SignedUploadUrl:
            raise StorageSignedError("supabase down")

        monkeypatch.setattr(brand_studio.storage_signed, "create_upload_url", fake_create)
        resp = client.post("/api/brand-studio/brands/brand-1/sources/init", json=self._payload())
        assert resp.status_code == 502

    def test_confirm_path_mismatch_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        sha = hashlib.sha256(b"x").hexdigest()
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/confirm",
            json={
                "storage_path": "evil/../escape.txt",
                "source_type": "brand_common",
                "file_name": "doc.txt",
                "sha256": sha,
            },
        )
        assert resp.status_code == 400

    def test_confirm_sha256_mismatch_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        # 클라이언트가 보낸 sha256 — 다운로드 본문과 의도적으로 다르게
        client_sha = hashlib.sha256(b"claimed").hexdigest()
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "download_object",
            lambda _p: b"actually different bytes",
        )
        removed: dict[str, str] = {}
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "remove_object",
            lambda p: removed.setdefault("path", p) is None or True,
        )
        path = f"brand-1/sources/{client_sha}.txt"
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/confirm",
            json={
                "storage_path": path,
                "source_type": "brand_common",
                "file_name": "doc.txt",
                "sha256": client_sha,
            },
        )
        assert resp.status_code == 422
        assert removed.get("path") == path

    def test_confirm_persists_record(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        body = "안녕하세요".encode()
        sha = hashlib.sha256(body).hexdigest()
        monkeypatch.setattr(brand_studio.storage_signed, "download_object", lambda _p: body)

        captured: dict[str, Any] = {}

        def fake_insert(record: BrandMessageSource) -> BrandMessageSource:
            captured["record"] = record
            return record.model_copy(update={"id": "s-confirmed"})

        monkeypatch.setattr(brand_studio.storage, "insert_message_source", fake_insert)

        path = f"brand-1/sources/{sha}.txt"
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/confirm",
            json={
                "storage_path": path,
                "source_type": "campaign",
                "file_name": "doc.txt",
                "sha256": sha,
            },
        )
        assert resp.status_code == 201
        record = captured["record"]
        assert record.storage_path == path
        assert record.file_sha256 == sha
        assert record.file_size_bytes == len(body)
        assert record.source_type == "campaign"
        assert "안녕" in (record.content_text or "")

    def test_delete_unknown_source_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """2026-05-11 — sources 삭제 API. 미존재 id → 404."""
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_message_source", lambda _id: None)
        resp = client.delete("/api/brand-studio/sources/missing")
        assert resp.status_code == 404

    def test_delete_source_removes_db_and_storage(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """2026-05-11 — sources 삭제: DB row 제거 + Supabase Storage 객체 제거."""
        from web.api.routers import brand_studio

        existing = BrandMessageSource(
            id="s-1",
            brand_id="brand-1",
            source_type="brand_common",
            file_name="원장 프로필.txt",
            storage_path="brand-1/sources/abc.txt",
            file_sha256="a" * 64,
        )
        monkeypatch.setattr(brand_studio.storage, "get_message_source", lambda _id: existing)

        deleted: dict[str, str] = {}

        def fake_delete(source_id: str) -> bool:
            deleted["id"] = source_id
            return True

        monkeypatch.setattr(brand_studio.storage, "delete_message_source", fake_delete)

        removed: dict[str, str] = {}
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "remove_object",
            lambda path: removed.setdefault("path", path) is None or True,
        )

        resp = client.delete("/api/brand-studio/sources/s-1")
        assert resp.status_code == 204
        assert deleted["id"] == "s-1"
        assert removed["path"] == "brand-1/sources/abc.txt"

    def test_confirm_preserves_unicode_filename(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """2026-05-11 — 한글 파일명이 _sanitize_filename 에서 _ 치환되던 버그 회귀 차단.

        저장은 sha256 기반이라 file_name 은 표시 전용. ASCII whitelist 가
        '원장 프로필.docx' 를 '__ ___.docx' 로 망가뜨리던 동작을 차단하고
        유니코드 그대로 보존하는지 검증.
        """
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        body = b"hello"
        sha = hashlib.sha256(body).hexdigest()
        monkeypatch.setattr(brand_studio.storage_signed, "download_object", lambda _p: body)

        captured: dict[str, Any] = {}

        def fake_insert(record: BrandMessageSource) -> BrandMessageSource:
            captured["record"] = record
            return record.model_copy(update={"id": "s-utf8"})

        monkeypatch.setattr(brand_studio.storage, "insert_message_source", fake_insert)

        path = f"brand-1/sources/{sha}.txt"
        resp = client.post(
            "/api/brand-studio/brands/brand-1/sources/confirm",
            json={
                "storage_path": path,
                "source_type": "brand_common",
                "file_name": "원장 프로필.txt",
                "sha256": sha,
            },
        )
        assert resp.status_code == 201
        assert captured["record"].file_name == "원장 프로필.txt"


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
        """2026-05-11 — 동기 list 응답 → 비동기 JobSubmitResponse 전환.

        Vercel rewrites proxy timeout (502) 회피를 위해 JobManager 경유. 라우터는
        즉시 202 + job_id 반환, 실제 LLM 호출은 background.
        """
        from unittest.mock import MagicMock

        from web.api import main as main_module
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        fake_job = MagicMock()
        fake_job.id = "job-plan-xyz"
        monkeypatch.setattr(
            main_module.job_manager,
            "submit_brand_card_plan_generate",
            lambda params: fake_job,
        )

        resp = client.post(
            "/api/brand-studio/brands/brand-1/plans",
            json={"keyword": "kw", "strategy_count": 2},
        )
        assert resp.status_code == 202
        assert resp.json()["job_id"] == "job-plan-xyz"

    def test_invalid_strategy_count_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """라우터 사전 검증 — JobManager 진입 전 400 응답."""
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

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


# ── 6b. GET /brands/{id}/plan-groups ────────────────────────


class TestListPlanGroups:
    """2026-05-11 — 브랜드 상세 페이지의 기획안 묶음 목록 API."""

    def test_unknown_brand_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.get("/api/brand-studio/brands/missing/plan-groups")
        assert resp.status_code == 404

    def test_returns_grouped_summary(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        groups = [
            {
                "reuse_group_id": "g-1",
                "keyword": "다이어트",
                "latest_created_at": "2026-05-11T03:00:00+00:00",
                "plan_count": 3,
                "status_counts": {"draft": 2, "approved": 1},
            },
            {
                "reuse_group_id": "g-2",
                "keyword": "한의원",
                "latest_created_at": "2026-05-10T02:00:00+00:00",
                "plan_count": 2,
                "status_counts": {"published": 2},
            },
        ]
        monkeypatch.setattr(
            brand_studio.storage,
            "list_plan_groups_for_brand",
            lambda _bid: groups,
        )

        resp = client.get("/api/brand-studio/brands/brand-1/plan-groups")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert [g["reuse_group_id"] for g in body["items"]] == ["g-1", "g-2"]
        assert body["items"][0]["status_counts"]["approved"] == 1


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


# ── 7b. PATCH /plans/{plan_id} (edit blocks) ────────────────


class TestEditPlan:
    def _payload(self) -> dict[str, Any]:
        return {
            "blocks": [
                {
                    "card_type": "hero",
                    "headline": "수정된 헤드라인",
                    "subcopy": "수정된 부제",
                    "bullets": ["요점 A", "요점 B"],
                    "image_asset_id": "m-99",
                    "ai_image_prompt": None,
                    "recommended_position": "after_intro",
                }
            ]
        }

    def test_edit_draft_transitions_to_reviewed(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """draft 인 plan 을 수정하면 reviewed 로 자동 전이."""
        from web.api.routers import brand_studio

        captured: dict[str, Any] = {}

        def fake_edit(plan_id: str, *, blocks: Any) -> BrandCardPlan:
            captured["plan_id"] = plan_id
            captured["blocks"] = blocks
            return _plan().model_copy(
                update={
                    "status": "reviewed",
                    "blocks": blocks,
                }
            )

        monkeypatch.setattr(brand_studio.orch, "edit_plan", fake_edit)
        resp = client.patch("/api/brand-studio/plans/p-1", json=self._payload())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "reviewed"
        assert body["blocks"][0]["headline"] == "수정된 헤드라인"
        assert captured["plan_id"] == "p-1"

    def test_edit_published_409(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from application.brand_card_orchestrator import PlanEditNotAllowedError
        from web.api.routers import brand_studio

        def fake_edit(plan_id: str, *, blocks: Any) -> BrandCardPlan:
            raise PlanEditNotAllowedError("수정 가능한 status 가 아닙니다: published")

        monkeypatch.setattr(brand_studio.orch, "edit_plan", fake_edit)
        resp = client.patch("/api/brand-studio/plans/p-1", json=self._payload())
        assert resp.status_code == 409

    def test_edit_unknown_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.orch,
            "edit_plan",
            lambda plan_id, *, blocks: None,
        )
        resp = client.patch("/api/brand-studio/plans/missing", json=self._payload())
        assert resp.status_code == 404

    def test_empty_blocks_422(self, client: TestClient) -> None:
        resp = client.patch("/api/brand-studio/plans/p-1", json={"blocks": []})
        assert resp.status_code == 422

    def test_invalid_block_shape_422(self, client: TestClient) -> None:
        resp = client.patch(
            "/api/brand-studio/plans/p-1",
            json={"blocks": [{"card_type": "hero"}]},  # required: headline, recommended_position
        )
        assert resp.status_code == 422


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
        """2026-05-11 — params 에 keyword 가 포함되는지 검증.

        누락 시 Job.keyword 가 빈 string → /jobs/{id} 화면에 "(키워드 없음)"
        표시되던 버그 회귀 차단.
        """
        from unittest.mock import MagicMock

        from web.api.routers import brand_studio

        approved = _plan(keyword="대구다이어트").model_copy(update={"status": "approved"})
        monkeypatch.setattr(
            brand_studio.storage,
            "list_cards_by_reuse_group",
            lambda _gid: [approved],
        )

        from web.api import main as main_module

        fake_job = MagicMock()
        fake_job.id = "job-xyz"
        captured: dict[str, Any] = {}

        def fake_submit(params: dict[str, Any]) -> Any:
            captured["params"] = params
            return fake_job

        monkeypatch.setattr(
            main_module.job_manager,
            "submit_brand_card_render",
            fake_submit,
        )

        resp = client.post(
            "/api/brand-studio/plans/g-1/render",
            json={"brand_name": "테스트", "brand_url": "https://x"},
        )
        assert resp.status_code == 202
        assert resp.json()["job_id"] == "job-xyz"
        assert captured["params"]["keyword"] == "대구다이어트"
        assert captured["params"]["reuse_group_id"] == "g-1"


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


# ── 10. GET /cards/{group_id}/files/{filename} — PNG 다운로드 ──


class TestDownloadCardPng:
    def _setup_png(self, brand_studio: Any, tmp_path: Any) -> Any:
        cards_dir = tmp_path / "brand_cards" / "g-1" / "cards"
        cards_dir.mkdir(parents=True)
        png_path = cards_dir / "card-clinic_trust-trust_first-01.png"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-data")
        return png_path

    def test_returns_png_file(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio,
            "_resolve_output_root",
            lambda: tmp_path / "brand_cards",
        )
        self._setup_png(brand_studio, tmp_path)
        resp = client.get("/api/brand-studio/cards/g-1/files/card-clinic_trust-trust_first-01.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert b"fake-png-data" in resp.content
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_missing_file_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio,
            "_resolve_output_root",
            lambda: tmp_path / "brand_cards",
        )
        resp = client.get("/api/brand-studio/cards/g-1/files/nope.png")
        assert resp.status_code == 404

    def test_path_traversal_in_filename_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio,
            "_resolve_output_root",
            lambda: tmp_path / "brand_cards",
        )
        # `..` 인코딩 (`%2E%2E`) 으로 전송 — httpx 클라이언트의 path normalization 회피
        resp = client.get("/api/brand-studio/cards/g-1/files/%2E%2E")
        assert resp.status_code == 400

    def test_slash_in_filename_blocked(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio,
            "_resolve_output_root",
            lambda: tmp_path / "brand_cards",
        )
        # encoded slash (`%2F`) 는 starlette 라우터가 segment 분리 → 404
        # (라우트 미매칭). 헬퍼 함수가 추가 방어선 역할.
        resp = client.get("/api/brand-studio/cards/g-1/files/sub%2Fevil.png")
        assert resp.status_code in (400, 404)

    def test_helper_is_safe_path_segment(self) -> None:
        from web.api.routers.brand_studio import _is_safe_path_segment

        assert _is_safe_path_segment("card-01.png") is True
        assert _is_safe_path_segment("g-1") is True
        assert _is_safe_path_segment("a_b.c-d") is True
        # 차단 케이스
        for bad in ("", ".", "..", "a/b", "a\\b", "a\x00b"):
            assert _is_safe_path_segment(bad) is False, bad


# ── 12-16. media-assets ─────────────────────────────────────


def _make_png_bytes(width: int = 4, height: int = 4) -> bytes:
    """테스트용 작은 PNG 바이트 — Pillow 디코드 통과 보장."""
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _media(asset_id: str = "m-1", **overrides: Any) -> BrandMediaAsset:
    base: dict[str, Any] = {
        "id": asset_id,
        "brand_id": "brand-1",
        "type": "doctor",
        "file_path": f"/tmp/{asset_id}.png",
        "file_sha256": "deadbeef" * 8,
        "title": "원장 프로필",
        "width": 800,
        "height": 600,
        "orientation": "landscape",
    }
    base.update(overrides)
    return BrandMediaAsset(**base)


class TestMediaAssetList:
    def test_unknown_brand_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.get("/api/brand-studio/brands/missing/media-assets")
        assert resp.status_code == 404

    def test_returns_assets(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(
            brand_studio.storage,
            "list_media_assets",
            lambda _id: [_media()],
        )
        resp = client.get("/api/brand-studio/brands/brand-1/media-assets")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["type"] == "doctor"


class TestMediaAssetUpload:
    def test_upload_unknown_brand_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.post(
            "/api/brand-studio/brands/missing/media-assets",
            files={"file": ("a.png", b"", "image/png")},
        )
        assert resp.status_code == 404

    def test_upload_unsupported_extension_415(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(brand_studio, "_ASSET_ROOT", tmp_path)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets",
            files={"file": ("a.bmp", b"binary", "image/bmp")},
        )
        assert resp.status_code == 415

    def test_upload_empty_file_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets",
            files={"file": ("empty.png", b"", "image/png")},
        )
        assert resp.status_code == 400

    def test_upload_corrupt_image_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(brand_studio, "_ASSET_ROOT", tmp_path)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets",
            files={"file": ("bad.png", b"not-a-png", "image/png")},
        )
        assert resp.status_code == 422

    def test_upload_persists_with_dimensions(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr(brand_studio, "_ASSET_ROOT", tmp_path)

        captured: dict[str, Any] = {}

        def fake_insert(asset: BrandMediaAsset) -> BrandMediaAsset:
            captured["asset"] = asset
            return asset.model_copy(update={"id": "m-new"})

        monkeypatch.setattr(brand_studio.storage, "insert_media_asset", fake_insert)

        png = _make_png_bytes(width=400, height=300)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets",
            files={"file": ("doctor.png", png, "image/png")},
            data={"asset_type": "doctor", "title": "원장님"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] == "m-new"
        assert body["width"] == 400
        assert body["height"] == 300
        assert body["orientation"] == "landscape"
        assert captured["asset"].type == "doctor"
        assert captured["asset"].title == "원장님"


class TestMediaAssetPresigned:
    def _payload(self, **overrides: Any) -> dict[str, Any]:
        sha = hashlib.sha256(b"placeholder").hexdigest()
        base: dict[str, Any] = {
            "file_name": "doctor.png",
            "file_size": 12345,
            "sha256": sha,
            "asset_type": "doctor",
        }
        base.update(overrides)
        return base

    def test_init_unknown_brand_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: None)
        resp = client.post(
            "/api/brand-studio/brands/missing/media-assets/init", json=self._payload()
        )
        assert resp.status_code == 404

    def test_init_invalid_asset_type_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/init",
            json=self._payload(asset_type="hack"),
        )
        assert resp.status_code == 422

    def test_init_too_large_413(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        monkeypatch.setattr("config.settings.settings.brand_media_max_bytes", 1000)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/init",
            json=self._payload(file_size=999_999),
        )
        assert resp.status_code == 413

    def test_init_unsupported_suffix_415(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/init",
            json=self._payload(file_name="img.bmp"),
        )
        assert resp.status_code == 415

    def test_init_returns_signed_url_with_media_prefix(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())

        captured_kwargs: dict[str, Any] = {}

        def fake_create(brand_id: str, sha256: str, suffix: str, **kw: Any) -> SignedUploadUrl:
            captured_kwargs.update(kw)
            return SignedUploadUrl(
                upload_url="https://supabase.example/sign/PUT",
                upload_token="tok",
                storage_path=f"{brand_id}/media/{sha256}{suffix}",
                expires_at=datetime.now(UTC) + timedelta(seconds=300),
            )

        monkeypatch.setattr(brand_studio.storage_signed, "create_upload_url", fake_create)
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/init", json=self._payload()
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "/media/" in body["storage_path"]
        assert body["storage_path"].endswith(".png")
        # 미디어는 brand-media 버킷 + media prefix 로 호출되어야 한다
        assert captured_kwargs.get("prefix") == "media"
        assert captured_kwargs.get("bucket") == "brand-media"

    def test_confirm_path_mismatch_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        sha = hashlib.sha256(b"x").hexdigest()
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/confirm",
            json={
                "storage_path": "evil/../escape.png",
                "asset_type": "doctor",
                "file_name": "img.png",
                "sha256": sha,
            },
        )
        assert resp.status_code == 400

    def test_confirm_sha256_mismatch_422(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        client_sha = hashlib.sha256(b"claimed").hexdigest()
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "download_object",
            lambda _p, **_kw: b"actually different",
        )
        removed: dict[str, str] = {}
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "remove_object",
            lambda p, **_kw: removed.setdefault("path", p) is None or True,
        )
        path = f"brand-1/media/{client_sha}.png"
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/confirm",
            json={
                "storage_path": path,
                "asset_type": "doctor",
                "file_name": "img.png",
                "sha256": client_sha,
            },
        )
        assert resp.status_code == 422
        assert removed.get("path") == path

    def test_confirm_persists_record(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_brand", lambda _id: _profile())
        png = _make_png_bytes(width=200, height=100)
        sha = hashlib.sha256(png).hexdigest()
        monkeypatch.setattr(brand_studio.storage_signed, "download_object", lambda _p, **_kw: png)

        captured: dict[str, Any] = {}

        def fake_insert(asset: BrandMediaAsset) -> BrandMediaAsset:
            captured["asset"] = asset
            return asset.model_copy(update={"id": "m-confirmed"})

        monkeypatch.setattr(brand_studio.storage, "insert_media_asset", fake_insert)

        path = f"brand-1/media/{sha}.png"
        resp = client.post(
            "/api/brand-studio/brands/brand-1/media-assets/confirm",
            json={
                "storage_path": path,
                "asset_type": "facility",
                "file_name": "img.png",
                "sha256": sha,
                "title": "정문",
            },
        )
        assert resp.status_code == 201
        asset = captured["asset"]
        assert asset.storage_path == path
        assert asset.file_path is None
        assert asset.file_sha256 == sha
        assert asset.file_size_bytes == len(png)
        assert asset.width == 200 and asset.height == 100
        assert asset.orientation == "landscape"
        assert asset.title == "정문"
        assert asset.type == "facility"


class TestMediaAssetGet:
    def test_get_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_media_asset", lambda _id: None)
        resp = client.get("/api/brand-studio/media-assets/missing")
        assert resp.status_code == 404

    def test_get_returns_asset(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_media_asset", lambda _id: _media())
        resp = client.get("/api/brand-studio/media-assets/m-1")
        assert resp.status_code == 200
        assert resp.json()["title"] == "원장 프로필"


class TestMediaAssetDelete:
    def test_delete_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_media_asset", lambda _id: None)
        resp = client.delete("/api/brand-studio/media-assets/missing")
        assert resp.status_code == 404

    def test_delete_204(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        # 디스크 파일 생성 → unlink 동작 검증
        f = tmp_path / "asset.png"
        f.write_bytes(b"\x89PNG")
        monkeypatch.setattr(
            brand_studio.storage,
            "get_media_asset",
            lambda _id: _media(file_path=str(f)),
        )
        deleted: dict[str, Any] = {}

        def fake_delete(asset_id: str) -> bool:
            deleted["id"] = asset_id
            return True

        monkeypatch.setattr(brand_studio.storage, "delete_media_asset", fake_delete)
        resp = client.delete("/api/brand-studio/media-assets/m-1")
        assert resp.status_code == 204
        assert deleted["id"] == "m-1"
        assert not f.exists(), "디스크 파일도 삭제되어야 함"


class TestMediaAssetDownload:
    def test_asset_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(brand_studio.storage, "get_media_asset", lambda _id: None)
        resp = client.get("/api/brand-studio/media-assets/missing/file")
        assert resp.status_code == 404

    def test_disk_missing_404(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "get_media_asset",
            lambda _id: _media(file_path="/nope/missing.png"),
        )
        resp = client.get("/api/brand-studio/media-assets/m-1/file")
        assert resp.status_code == 404

    def test_returns_image_with_content_type(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from web.api.routers import brand_studio

        png = _make_png_bytes()
        f = tmp_path / "asset.png"
        f.write_bytes(png)
        monkeypatch.setattr(
            brand_studio.storage,
            "get_media_asset",
            lambda _id: _media(file_path=str(f)),
        )
        resp = client.get("/api/brand-studio/media-assets/m-1/file")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == png

    def test_storage_path_redirects_to_signed_url(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """presigned 자산 (storage_path 만 있음) → 302 redirect to Supabase."""
        from web.api.routers import brand_studio

        monkeypatch.setattr(
            brand_studio.storage,
            "get_media_asset",
            lambda _id: _media(file_path=None, storage_path="brand-1/media/abc.png"),
        )
        monkeypatch.setattr(
            brand_studio.storage_signed,
            "create_download_url",
            lambda _p, **_kw: "https://supabase.example/signed-download",
        )
        resp = client.get("/api/brand-studio/media-assets/m-1/file", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "https://supabase.example/signed-download"


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
