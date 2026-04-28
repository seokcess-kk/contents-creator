"""brand_card/storage.py — Supabase mock CRUD 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from domain.brand_card import storage as st
from domain.brand_card.model import (
    BrandCardPlan,
    BrandMessageSource,
    CardBlock,
    CardCampaignInput,
)


def _supabase_chain(rows: list[dict]) -> MagicMock:
    """Supabase chain mock: client.table(...).select(...).execute() → SimpleNamespace(data=rows)."""
    chain = MagicMock()
    chain.execute.return_value = SimpleNamespace(data=rows)
    return chain


def _client_with_table(table_chain: MagicMock) -> MagicMock:
    client = MagicMock()
    client.table.return_value = table_chain
    return client


# ── brand_message_sources ──────────────────────────────────────


class TestMessageSourceCRUD:
    def test_insert_message_source(self) -> None:
        row = {
            "id": "s-1",
            "brand_id": "b-1",
            "source_type": "brand_common",
            "file_name": "intro.txt",
            "content_text": "본문",
            "content_summary": {"tags": ["mission"]},
            "created_at": "2026-04-28T00:00:00+00:00",
        }
        chain = MagicMock()
        chain.insert.return_value.execute.return_value = SimpleNamespace(data=[row])
        client = _client_with_table(chain)

        with patch.object(st, "get_client", return_value=client):
            src = BrandMessageSource(
                brand_id="b-1", source_type="brand_common", content_text="본문"
            )
            saved = st.insert_message_source(src)
        assert saved.id == "s-1"
        assert saved.content_summary["tags"] == ["mission"]

    def test_insert_raises_on_empty_response(self) -> None:
        chain = MagicMock()
        chain.insert.return_value.execute.return_value = SimpleNamespace(data=[])
        client = _client_with_table(chain)
        with (
            patch.object(st, "get_client", return_value=client),
            pytest.raises(RuntimeError, match="no row returned"),
        ):
            st.insert_message_source(BrandMessageSource(brand_id="b-1", source_type="brand_common"))

    def test_list_message_sources(self) -> None:
        rows = [
            {
                "id": f"s-{i}",
                "brand_id": "b-1",
                "source_type": "brand_common",
                "content_summary": {},
            }
            for i in range(3)
        ]
        chain = MagicMock()
        chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=rows
        )
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.list_message_sources("b-1", limit=10)
        assert len(result) == 3
        assert all(r.brand_id == "b-1" for r in result)

    def test_get_message_sources_by_ids_empty_returns_empty(self) -> None:
        with patch.object(st, "get_client") as gc:
            assert st.get_message_sources_by_ids([]) == []
            gc.assert_not_called()  # 빈 리스트면 클라이언트 미호출

    def test_get_message_sources_by_ids(self) -> None:
        rows = [
            {"id": "s-1", "brand_id": "b-1", "source_type": "campaign"},
            {"id": "s-2", "brand_id": "b-1", "source_type": "reference"},
        ]
        chain = MagicMock()
        chain.select.return_value.in_.return_value.execute.return_value = SimpleNamespace(data=rows)
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.get_message_sources_by_ids(["s-1", "s-2"])
        assert {s.id for s in result} == {"s-1", "s-2"}


# ── card_campaign_inputs ───────────────────────────────────────


class TestCampaignInputCRUD:
    def test_insert_campaign_input_persists_arrays(self) -> None:
        row = {
            "id": "ci-1",
            "brand_id": "b-1",
            "keyword": "다이어트",
            "expression_level": "hooking",
            "required_phrases": ["대구 동성로"],
            "forbidden_phrases": ["100% 보장"],
            "attached_source_ids": ["s-1"],
            "reference_image_paths": [],
        }
        chain = MagicMock()
        chain.insert.return_value.execute.return_value = SimpleNamespace(data=[row])
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            ci = CardCampaignInput(
                brand_id="b-1",
                keyword="다이어트",
                expression_level="hooking",
                required_phrases=["대구 동성로"],
                forbidden_phrases=["100% 보장"],
                attached_source_ids=["s-1"],
            )
            saved = st.insert_campaign_input(ci)
        assert saved.id == "ci-1"
        assert saved.required_phrases == ["대구 동성로"]
        assert saved.expression_level == "hooking"

    def test_get_latest_returns_none_when_empty(self) -> None:
        chain = MagicMock()
        chain.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.get_latest_campaign_input("b-1", "kw")
        assert result is None

    def test_get_latest_returns_first_row(self) -> None:
        row = {
            "id": "ci-1",
            "brand_id": "b-1",
            "keyword": "kw",
            "expression_level": "balanced",
        }
        chain = MagicMock()
        chain.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=[row]
        )
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.get_latest_campaign_input("b-1", "kw")
        assert result is not None
        assert result.id == "ci-1"


# ── brand_cards (plan) ─────────────────────────────────────────


def _plan(plan_id: str | None = None, status: str = "draft") -> BrandCardPlan:
    return BrandCardPlan(
        id=plan_id,
        brand_id="b-1",
        keyword="kw",
        strategy="trust_first",
        expression_level="balanced",
        template_id="clinic_trust",
        angle="...",
        blocks=[
            CardBlock(
                card_type="hero",
                headline="제목",
                recommended_position="after_intro",
            )
        ],
        status=status,
    )


class TestCardPlanCRUD:
    def test_insert_card_plan_serializes_blocks_to_source_summary(self) -> None:
        captured: dict[str, object] = {}

        def capture_insert(payload: dict[str, object]) -> MagicMock:
            captured["payload"] = payload
            inner = MagicMock()
            inner.execute.return_value = SimpleNamespace(
                data=[{**payload, "id": "p-1", "created_at": "2026-04-28T00:00:00Z"}]
            )
            return inner

        chain = MagicMock()
        chain.insert.side_effect = capture_insert
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            saved = st.insert_card_plan(_plan())
        assert saved.id == "p-1"
        # source_summary 안에 blocks 직렬화됨
        payload = captured["payload"]
        assert isinstance(payload, dict)
        summary = payload["source_summary"]
        assert isinstance(summary, dict)
        assert "blocks" in summary

    def test_get_card_plan_returns_none_for_missing(self) -> None:
        chain = MagicMock()
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            SimpleNamespace(data=[])
        )
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            assert st.get_card_plan("missing") is None

    def test_update_card_status_with_compliance_report(self) -> None:
        captured: dict[str, object] = {}

        def capture_update(payload: dict[str, object]) -> MagicMock:
            captured["payload"] = payload
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = SimpleNamespace(
                data=[
                    {
                        "id": "p-1",
                        "brand_id": "b-1",
                        "keyword": "kw",
                        "template_id": "clinic_trust",
                        "status": "approved",
                    }
                ]
            )
            return inner

        chain = MagicMock()
        chain.update.side_effect = capture_update
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.update_card_status(
                "p-1", "approved", compliance_report={"passed": True, "violations": []}
            )
        payload = captured["payload"]
        assert isinstance(payload, dict)
        assert payload["status"] == "approved"
        assert payload["compliance_report"] == {"passed": True, "violations": []}
        assert result is not None
        assert result.status == "approved"

    def test_update_card_status_returns_none_when_not_found(self) -> None:
        chain = MagicMock()
        chain.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[])
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.update_card_status("missing", "approved")
        assert result is None

    def test_list_recent_cards_for_brand_uses_30_day_window(self) -> None:
        captured: dict[str, object] = {}

        def capture_gte(col: str, value: str) -> MagicMock:
            captured["col"] = col
            captured["value"] = value
            inner = MagicMock()
            inner.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
                data=[]
            )
            return inner

        chain_after_eq = MagicMock()
        chain_after_eq.gte.side_effect = capture_gte
        chain = MagicMock()
        chain.select.return_value.eq.return_value = chain_after_eq

        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            st.list_recent_cards_for_brand("b-1", days=30)
        assert captured["col"] == "created_at"
        # ISO datetime — 'T' 구분자 포함
        assert "T" in str(captured["value"])

    def test_list_cards_by_reuse_group(self) -> None:
        rows = [
            {
                "id": f"p-{i}",
                "brand_id": "b-1",
                "keyword": "kw",
                "template_id": "clinic_trust",
                "strategy": "trust_first",
                "status": "draft",
                "reuse_group_id": "g-1",
                "source_summary": {"blocks": []},
                "variant_idx": i,
            }
            for i in range(3)
        ]
        chain = MagicMock()
        chain.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            SimpleNamespace(data=rows)
        )
        with patch.object(st, "get_client", return_value=_client_with_table(chain)):
            result = st.list_cards_by_reuse_group("g-1")
        assert len(result) == 3
        assert all(p.reuse_group_id == "g-1" for p in result)


class TestParseDtHelper:
    def test_iso_string_with_z_suffix(self) -> None:
        result = st._parse_dt("2026-04-28T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_invalid_string_returns_none(self) -> None:
        result = st._parse_dt("not-a-date")
        assert result is None

    def test_datetime_passthrough(self) -> None:
        ts = datetime(2026, 4, 28, tzinfo=UTC)
        assert st._parse_dt(ts) is ts

    def test_none_returns_none(self) -> None:
        assert st._parse_dt(None) is None
