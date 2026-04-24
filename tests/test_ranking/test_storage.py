"""storage 단위 테스트 — Supabase mock."""

from __future__ import annotations

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


class TestUniqueViolationDetection:
    def test_detects_postgres_code(self) -> None:
        assert storage._is_unique_violation(Exception("Code 23505 unique violation"))

    def test_detects_keyword(self) -> None:
        assert storage._is_unique_violation(Exception("duplicate key error"))

    def test_passes_other(self) -> None:
        assert not storage._is_unique_violation(Exception("connection refused"))
