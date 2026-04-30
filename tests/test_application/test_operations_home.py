"""operations_home batch enrichment and tab filter tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from application import operations_home
from domain.diagnosis.model import Diagnosis
from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SearchVolume,
    SerpComposition,
)
from domain.ranking.model import Publication, RankingSnapshot


@pytest.fixture
def ranking_storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(operations_home, "ranking_storage", mock)
    return mock


@pytest.fixture
def diagnosis_storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(operations_home, "diagnosis_storage", mock)
    return mock


@pytest.fixture
def difficulty_storage_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.list_recent.return_value = []
    monkeypatch.setattr(operations_home, "difficulty_storage", mock)
    return mock


def _pub(pub_id: str, **overrides: Any) -> Publication:
    base: dict[str, Any] = {
        "id": pub_id,
        "keyword": f"kw-{pub_id}",
        "url": f"https://m.blog.naver.com/u/{pub_id}",
    }
    base.update(overrides)
    return Publication(**base)


def _difficulty(keyword: str, **overrides: Any) -> KeywordDifficulty:
    base: dict[str, Any] = {
        "keyword": keyword,
        "score": 3.0,
        "grade": DifficultyGrade.LOW,
        "composition": SerpComposition(total_cards=8),
        "search_volume": SearchVolume(monthly_pc=100, monthly_mobile=200),
        "checked_at": datetime.now(UTC) - timedelta(days=1),
    }
    base.update(overrides)
    return KeywordDifficulty(**base)


class TestListPublicationsForTab:
    def test_uses_batch_fetch_not_n_plus_1(
        self,
        ranking_storage_mock: MagicMock,
        diagnosis_storage_mock: MagicMock,
        difficulty_storage_mock: MagicMock,
    ) -> None:
        pubs = [_pub(f"pub-{i:03d}") for i in range(100)]
        ranking_storage_mock.list_publications.return_value = pubs
        ranking_storage_mock.list_latest_snapshots_batch.return_value = {
            "pub-000": RankingSnapshot(
                publication_id="pub-000",
                section="VIEW",
                position=3,
                captured_at=datetime(2026, 4, 27, tzinfo=UTC),
            ),
        }
        diagnosis_storage_mock.list_latest_diagnoses_batch.return_value = {
            "pub-001": Diagnosis(
                publication_id="pub-001",
                reason="lost_visibility",
                confidence=0.85,
            ),
        }
        difficulty_storage_mock.list_recent.return_value = [_difficulty("KW-PUB-000")]

        result = operations_home.list_publications_for_tab("all", limit=100)

        ranking_storage_mock.list_latest_snapshots_batch.assert_called_once()
        diagnosis_storage_mock.list_latest_diagnoses_batch.assert_called_once()
        difficulty_storage_mock.list_recent.assert_called_once()
        assert ranking_storage_mock.list_snapshots.call_count == 0
        assert diagnosis_storage_mock.list_diagnoses_by_publication.call_count == 0

        first = next(r for r in result if r["id"] == "pub-000")
        assert first["latest_snapshot"]["position"] == 3
        assert first["latest_diagnosis"] is None
        assert first["keyword_difficulty"]["grade"] == "low"
        assert first["keyword_difficulty"]["monthly_total_search"] == 300

        second = next(r for r in result if r["id"] == "pub-001")
        assert second["latest_snapshot"] is None
        assert second["latest_diagnosis"]["reason"] == "lost_visibility"
        assert second["keyword_difficulty"] is None

    def test_unknown_tab_raises(
        self,
        ranking_storage_mock: MagicMock,
        diagnosis_storage_mock: MagicMock,
        difficulty_storage_mock: MagicMock,
    ) -> None:
        with pytest.raises(ValueError, match="unknown tab"):
            operations_home.list_publications_for_tab("invalid")

    def test_batch_failure_falls_back_to_empty(
        self,
        ranking_storage_mock: MagicMock,
        diagnosis_storage_mock: MagicMock,
        difficulty_storage_mock: MagicMock,
    ) -> None:
        ranking_storage_mock.list_publications.return_value = [_pub("p1")]
        ranking_storage_mock.list_latest_snapshots_batch.side_effect = RuntimeError("rpc down")
        diagnosis_storage_mock.list_latest_diagnoses_batch.side_effect = RuntimeError("rpc down")
        difficulty_storage_mock.list_recent.side_effect = RuntimeError("rpc down")

        result = operations_home.list_publications_for_tab("all")

        assert len(result) == 1
        assert result[0]["latest_snapshot"] is None
        assert result[0]["latest_diagnosis"] is None
        assert result[0]["keyword_difficulty"] is None


class TestSummary:
    def test_returns_workflow_counts_with_total(
        self,
        ranking_storage_mock: MagicMock,
        difficulty_storage_mock: MagicMock,
    ) -> None:
        ranking_storage_mock.count_publications_by_workflow_status.return_value = {
            "active": 30,
            "action_required": 12,
            "held": 5,
            "republishing": 2,
            "dismissed": 3,
            "__exposed": 25,
        }
        ranking_storage_mock.list_publications.return_value = [_pub("p1"), _pub("p2")]
        difficulty_storage_mock.list_recent.return_value = [_difficulty("kw-p1")]

        summary = operations_home.get_summary()

        assert summary["active"] == 25
        assert summary["action_required"] == 12
        assert summary["held"] == 5
        assert summary["republishing"] == 2
        assert summary["dismissed"] == 3
        assert summary["total"] == 52
        assert summary["difficulty_missing"] == 1
        assert summary["difficulty_stale"] == 0

    def test_counts_stale_difficulty(
        self,
        ranking_storage_mock: MagicMock,
        difficulty_storage_mock: MagicMock,
    ) -> None:
        ranking_storage_mock.count_publications_by_workflow_status.return_value = {
            "active": 1,
            "__exposed": 0,
        }
        ranking_storage_mock.list_publications.return_value = [_pub("p1")]
        difficulty_storage_mock.list_recent.return_value = [
            _difficulty(
                "kw-p1",
                checked_at=datetime.now(UTC)
                - timedelta(days=operations_home.DIFFICULTY_STALE_DAYS),
            )
        ]

        summary = operations_home.get_summary()

        assert summary["active"] == 0
        assert summary["total"] == 1
        assert summary["difficulty_missing"] == 0
        assert summary["difficulty_stale"] == 1
