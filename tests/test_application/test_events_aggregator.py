"""P1-#7: events_aggregator 3종 소스 merge 시나리오 테스트.

`list_publication_events` 가 snapshot/diagnosis/action 을 시간순(역순)
으로 합치는지 확인. 빈/단일/혼합 시나리오 모두 커버.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from application import events_aggregator
from domain.diagnosis.model import Diagnosis
from domain.ranking.model import RankingSnapshot
from domain.ranking.publication_actions import PublicationAction


def _at(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


class TestEmptyAndSingleSource:
    def test_all_sources_empty(self) -> None:
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=[]),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=[],
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert events == []

    def test_only_snapshots(self) -> None:
        snaps = [
            RankingSnapshot(
                publication_id="p-1",
                section="VIEW",
                position=5,
                captured_at=_at(2026, 4, 27),
            )
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=snaps),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=[],
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert len(events) == 1
        assert events[0].type == "snapshot"
        assert events[0].data["position"] == 5

    def test_snapshot_with_no_captured_at_skipped(self) -> None:
        """captured_at=None 인 snapshot 은 시간순 merge 불가 → 스킵."""
        snaps = [
            RankingSnapshot(publication_id="p-1", position=5, captured_at=None),
            RankingSnapshot(
                publication_id="p-1",
                position=3,
                captured_at=_at(2026, 4, 27),
            ),
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=snaps),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=[],
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert len(events) == 1  # captured_at=None 제외


class TestMixedSourcesTimeOrder:
    def test_three_sources_merged_descending(self) -> None:
        """3종 소스가 occurred_at desc 로 인터리브됨."""
        snaps = [
            RankingSnapshot(
                publication_id="p-1",
                section="VIEW",
                position=5,
                captured_at=_at(2026, 4, 27, 10),
            ),
            RankingSnapshot(
                publication_id="p-1",
                section="VIEW",
                position=None,
                captured_at=_at(2026, 4, 25, 10),
            ),
        ]
        diagnoses = [
            Diagnosis(
                publication_id="p-1",
                diagnosed_at=_at(2026, 4, 26, 9),
                reason="lost_visibility",
                confidence=0.75,
                evidence=["최근 3회 미노출"],
                metrics={"null_streak": 3},
            )
        ]
        actions = [
            PublicationAction(
                publication_id="p-1",
                created_at=_at(2026, 4, 26, 14),
                action="republished",
                metadata={"strategy": "full_rewrite"},
            )
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=snaps),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=diagnoses,
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=actions,
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        # 4건: snap(4/27 10) > action(4/26 14) > diagnosis(4/26 9) > snap(4/25 10)
        assert [e.type for e in events] == ["snapshot", "action", "diagnosis", "snapshot"]
        assert events[0].occurred_at > events[1].occurred_at
        assert events[1].occurred_at > events[2].occurred_at
        assert events[2].occurred_at > events[3].occurred_at

    def test_diagnosis_payload_contains_evidence_and_metrics(self) -> None:
        diagnoses = [
            Diagnosis(
                publication_id="p-1",
                diagnosed_at=_at(2026, 4, 26),
                reason="never_indexed",
                confidence=0.6,
                evidence=["발행 후 D+12 미노출"],
                metrics={"days_since_publish": 12},
                recommended_action="콘텐츠 갭 분석 후 재발행",
            )
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=[]),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=diagnoses,
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=[],
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert len(events) == 1
        data = events[0].data
        assert data["reason"] == "never_indexed"
        assert data["confidence"] == 0.6
        assert data["evidence"] == ["발행 후 D+12 미노출"]
        assert data["metrics"] == {"days_since_publish": 12}
        assert data["recommended_action"] == "콘텐츠 갭 분석 후 재발행"

    def test_action_payload_preserves_metadata(self) -> None:
        actions = [
            PublicationAction(
                publication_id="p-1",
                created_at=_at(2026, 4, 26),
                action="held",
                note="경쟁 강도 높음",
                metadata={"days": 7, "trigger": "manual"},
            )
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=[]),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=actions,
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert events[0].type == "action"
        assert events[0].data["action"] == "held"
        assert events[0].data["note"] == "경쟁 강도 높음"
        assert events[0].data["metadata"]["days"] == 7

    def test_same_timestamp_keeps_both_events(self) -> None:
        """같은 occurred_at 도 누락 없이 보존 (정렬 안정성은 미보장이지만 둘 다 존재)."""
        ts = _at(2026, 4, 26, 12)
        snaps = [RankingSnapshot(publication_id="p-1", position=5, section="VIEW", captured_at=ts)]
        actions = [PublicationAction(publication_id="p-1", created_at=ts, action="url_registered")]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=snaps),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=actions,
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert len(events) == 2
        types = sorted(e.type for e in events)
        assert types == ["action", "snapshot"]


class TestNullPositionSnapshot:
    def test_null_position_serialized_correctly(self) -> None:
        """미노출(position=None) 도 snapshot 이벤트로 정상 직렬화."""
        snaps = [
            RankingSnapshot(
                publication_id="p-1",
                section=None,
                position=None,
                captured_at=_at(2026, 4, 27),
            )
        ]
        with (
            patch.object(events_aggregator.ranking_storage, "list_snapshots", return_value=snaps),
            patch.object(
                events_aggregator.diag_storage,
                "list_diagnoses_by_publication",
                return_value=[],
            ),
            patch.object(
                events_aggregator.publication_actions,
                "list_actions_by_publication",
                return_value=[],
            ),
        ):
            events = events_aggregator.list_publication_events("p-1")
        assert events[0].data["position"] is None
        assert events[0].data["section"] is None
