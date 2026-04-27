"""operations_home — 배치 fetch + tab filter 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from application import operations_home
from domain.diagnosis.model import Diagnosis
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


def _pub(pub_id: str, **overrides: Any) -> Publication:
    base: dict[str, Any] = {
        "id": pub_id,
        "keyword": f"kw-{pub_id}",
        "url": f"https://m.blog.naver.com/u/{pub_id}",
    }
    base.update(overrides)
    return Publication(**base)


class TestListPublicationsForTab:
    def test_uses_batch_fetch_not_n_plus_1(
        self,
        ranking_storage_mock: MagicMock,
        diagnosis_storage_mock: MagicMock,
    ) -> None:
        """100 pubs 도 RPC 2번만 호출 (snapshot batch + diagnosis batch)."""
        pubs = [_pub(f"pub-{i:03d}") for i in range(100)]
        ranking_storage_mock.list_publications.return_value = pubs

        # 배치 RPC 응답 — 일부만 매칭
        ranking_storage_mock.list_latest_snapshots_batch.return_value = {
            "pub-000": RankingSnapshot(
                publication_id="pub-000",
                section="인플루언서",
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

        result = operations_home.list_publications_for_tab("all", limit=100)

        # 1번씩만 호출 (N+1 X)
        ranking_storage_mock.list_latest_snapshots_batch.assert_called_once()
        diagnosis_storage_mock.list_latest_diagnoses_batch.assert_called_once()
        assert ranking_storage_mock.list_snapshots.call_count == 0
        assert diagnosis_storage_mock.list_diagnoses_by_publication.call_count == 0

        # enrich 결과 확인
        first = next(r for r in result if r["id"] == "pub-000")
        assert first["latest_snapshot"]["position"] == 3
        assert first["latest_diagnosis"] is None  # pub-000 진단 없음

        second = next(r for r in result if r["id"] == "pub-001")
        assert second["latest_snapshot"] is None  # pub-001 snapshot 없음
        assert second["latest_diagnosis"]["reason"] == "lost_visibility"

    def test_unknown_tab_raises(
        self, ranking_storage_mock: MagicMock, diagnosis_storage_mock: MagicMock
    ) -> None:
        with pytest.raises(ValueError, match="unknown tab"):
            operations_home.list_publications_for_tab("invalid")

    def test_batch_failure_falls_back_to_empty(
        self,
        ranking_storage_mock: MagicMock,
        diagnosis_storage_mock: MagicMock,
    ) -> None:
        """RPC 실패 시 큐 자체는 출력 (snapshot/diagnosis 만 None)."""
        ranking_storage_mock.list_publications.return_value = [_pub("p1")]
        ranking_storage_mock.list_latest_snapshots_batch.side_effect = RuntimeError("rpc down")
        diagnosis_storage_mock.list_latest_diagnoses_batch.side_effect = RuntimeError("rpc down")

        result = operations_home.list_publications_for_tab("all")

        assert len(result) == 1
        assert result[0]["latest_snapshot"] is None
        assert result[0]["latest_diagnosis"] is None


class TestSummary:
    def test_returns_workflow_counts_with_total(
        self, ranking_storage_mock: MagicMock
    ) -> None:
        ranking_storage_mock.count_publications_by_workflow_status.return_value = {
            "active": 30,
            "action_required": 12,
            "held": 5,
            "republishing": 2,
            "dismissed": 3,
        }
        s = operations_home.get_summary()
        assert s["active"] == 30
        assert s["action_required"] == 12
        assert s["held"] == 5
        assert s["republishing"] == 2
        assert s["dismissed"] == 3
        assert s["total"] == 52
