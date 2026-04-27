"""storage 단위 테스트 — Supabase mock."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from unittest.mock import MagicMock

import pytest

from domain.ranking import storage
from domain.ranking.model import (
    Publication,
    RankingDuplicateUrlError,
    RankingSnapshot,
)


def _make_mock_table(insert_data: list[dict[str, Any]] | None = None) -> MagicMock:
    """체이닝되는 mock chain 생성: client.table(t).insert(p).execute()."""
    table = MagicMock()
    table.insert.return_value.execute.return_value = MagicMock(data=insert_data or [])
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=insert_data or []
    )
    table.select.return_value.order.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=insert_data or [])
    )
    table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=insert_data or []
    )
    return table


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    monkeypatch.setattr(storage, "get_client", lambda: client)
    return client


def _publication_row() -> dict[str, Any]:
    return {
        "id": "pub-1",
        "job_id": "job-1",
        "keyword": "kw",
        "slug": "kw-slug",
        "url": "https://m.blog.naver.com/u/123456789",
        "published_at": None,
        "created_at": "2026-04-24T00:00:00+00:00",
    }


def _snapshot_row() -> dict[str, Any]:
    return {
        "id": "snap-1",
        "publication_id": "pub-1",
        "position": 5,
        "total_results": 10,
        "captured_at": "2026-04-24T09:00:00+00:00",
        "serp_html_path": None,
    }


class TestInsertPublication:
    def test_returns_inserted_row(self, mock_client: MagicMock) -> None:
        mock_client.table.return_value = _make_mock_table([_publication_row()])
        p = Publication(keyword="kw", slug="kw-slug", url="https://m.blog.naver.com/u/123456789")
        result = storage.insert_publication(p)
        assert result.id == "pub-1"

    def test_unique_violation_raises_duplicate(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.insert.return_value.execute.side_effect = RuntimeError(
            "duplicate key value violates unique constraint"
        )
        mock_client.table.return_value = table
        p = Publication(keyword="kw", slug="kw-slug", url="https://m.blog.naver.com/u/123456789")
        with pytest.raises(RankingDuplicateUrlError):
            storage.insert_publication(p)

    def test_payload_omits_slug_when_none(self, mock_client: MagicMock) -> None:
        """slug=None 이면 payload 에서 제외 (DB NULL 기본값 활용)."""
        row = _publication_row()
        row["slug"] = None
        table = _make_mock_table([row])
        mock_client.table.return_value = table
        p = Publication(keyword="kw", url="https://m.blog.naver.com/u/123456789")
        result = storage.insert_publication(p)
        assert result.slug is None
        called_payload = table.insert.call_args.args[0]
        assert "slug" not in called_payload


class TestGetPublication:
    def test_returns_none_when_missing(self, mock_client: MagicMock) -> None:
        mock_client.table.return_value = _make_mock_table([])
        assert storage.get_publication("pub-x") is None

    def test_returns_publication_when_found(self, mock_client: MagicMock) -> None:
        mock_client.table.return_value = _make_mock_table([_publication_row()])
        result = storage.get_publication("pub-1")
        assert result is not None
        assert result.keyword == "kw"


class TestListPublications:
    def test_no_keyword_filter(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.select.return_value.order.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[_publication_row()])
        )
        mock_client.table.return_value = table
        result = storage.list_publications(limit=10)
        assert len(result) == 1

    def test_with_keyword_filter(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.select.return_value.order.return_value.limit.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_publication_row()]
        )
        mock_client.table.return_value = table
        result = storage.list_publications(keyword="kw", limit=10)
        assert len(result) == 1


class TestUpdatePublication:
    def test_partial_update(self, mock_client: MagicMock) -> None:
        row = _publication_row()
        row["keyword"] = "new"
        table = MagicMock()
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[row])
        mock_client.table.return_value = table
        result = storage.update_publication("pub-1", keyword="new")
        assert result is not None
        assert result.keyword == "new"
        called_payload = table.update.call_args.args[0]
        assert called_payload == {"keyword": "new"}

    def test_returns_none_when_missing(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = table
        assert storage.update_publication("pub-x", keyword="x") is None

    def test_no_changes_returns_existing(self, mock_client: MagicMock) -> None:
        """모든 필드 None 이면 update 안 하고 기존 row 반환."""
        # get_publication 경로를 타도록 mock_client 가 select 결과 반환
        table = MagicMock()
        table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[_publication_row()])
        )
        mock_client.table.return_value = table
        result = storage.update_publication("pub-1")
        assert result is not None
        assert result.id == "pub-1"
        # update 호출 안 됨
        table.update.assert_not_called()


class TestDeletePublication:
    def test_returns_true_on_success(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "pub-1"}]
        )
        mock_client.table.return_value = table
        assert storage.delete_publication("pub-1") is True

    def test_returns_false_when_missing(self, mock_client: MagicMock) -> None:
        table = MagicMock()
        table.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = table
        assert storage.delete_publication("pub-x") is False


class TestInsertSnapshot:
    def test_inserts_and_returns(self, mock_client: MagicMock) -> None:
        mock_client.table.return_value = _make_mock_table([_snapshot_row()])
        snap = RankingSnapshot(publication_id="pub-1", position=5, total_results=10)
        result = storage.insert_snapshot(snap)
        assert result.id == "snap-1"
        assert result.position == 5

    def test_position_none_persisted(self, mock_client: MagicMock) -> None:
        row = _snapshot_row()
        row["position"] = None
        mock_client.table.return_value = _make_mock_table([row])
        snap = RankingSnapshot(publication_id="pub-1")
        result = storage.insert_snapshot(snap)
        assert result.position is None


class TestListSnapshots:
    def test_returns_ordered_list(self, mock_client: MagicMock) -> None:
        rows = [_snapshot_row(), {**_snapshot_row(), "id": "snap-2", "position": 7}]
        mock_client.table.return_value = _make_mock_table(rows)
        result = storage.list_snapshots("pub-1", limit=10)
        assert len(result) == 2


class TestListSnapshotsInRange:
    def test_passes_iso_bounds(self, mock_client: MagicMock) -> None:
        from datetime import datetime

        table = MagicMock()
        table.select.return_value.gte.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[_snapshot_row()]
        )
        mock_client.table.return_value = table

        start = datetime(2026, 3, 31, 15, 0, tzinfo=UTC)
        end = datetime(2026, 4, 30, 15, 0, tzinfo=UTC)
        result = storage.list_snapshots_in_range(start, end)
        assert len(result) == 1
        # gte/lt 호출 인자 검증 — ISO 문자열로 전달돼야
        gte_arg = table.select.return_value.gte.call_args.args[1]
        lt_arg = table.select.return_value.gte.return_value.lt.call_args.args[1]
        assert gte_arg.startswith("2026-03-31T15:00")
        assert lt_arg.startswith("2026-04-30T15:00")


class TestUniqueViolationDetection:
    def test_detects_postgres_code(self) -> None:
        assert storage._is_unique_violation(Exception("Code 23505 unique violation"))

    def test_detects_keyword(self) -> None:
        assert storage._is_unique_violation(Exception("duplicate key error"))

    def test_passes_other(self) -> None:
        assert not storage._is_unique_violation(Exception("connection refused"))
