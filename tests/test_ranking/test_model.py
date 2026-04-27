"""ranking 도메인 Pydantic 모델 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.ranking.model import (
    Publication,
    RankingCheckSummary,
    RankingSnapshot,
    RankingTimeline,
)


class TestPublication:
    def test_minimal_required_fields(self) -> None:
        p = Publication(
            keyword="다이어트",
            slug="diet",
            url="https://m.blog.naver.com/u/123456789",
        )
        assert p.id is None
        assert p.keyword == "다이어트"

    def test_serialization_roundtrip(self) -> None:
        published = datetime(2026, 4, 24, tzinfo=UTC)
        p = Publication(
            keyword="다이어트",
            slug="diet",
            url="https://m.blog.naver.com/u/123456789",
            published_at=published,
        )
        data = p.model_dump_json()
        restored = Publication.model_validate_json(data)
        assert restored.published_at == published


class TestRankingSnapshot:
    def test_position_in_range(self) -> None:
        s = RankingSnapshot(publication_id="abc", position=1)
        assert s.position == 1

    def test_position_none_means_off_chart(self) -> None:
        s = RankingSnapshot(publication_id="abc")
        assert s.position is None

    def test_position_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RankingSnapshot(publication_id="abc", position=0)

    def test_section_field_optional(self) -> None:
        s = RankingSnapshot(publication_id="abc", section="인플루언서", position=3)
        assert s.section == "인플루언서"
        assert s.position == 3


class TestRankingTimeline:
    def test_groups_publication_with_snapshots(self) -> None:
        pub = Publication(keyword="kw", slug="s", url="https://m.blog.naver.com/u/123456789")
        snaps = [RankingSnapshot(publication_id="x", position=p) for p in (5, 3, 1)]
        timeline = RankingTimeline(publication=pub, snapshots=snaps)
        assert len(timeline.snapshots) == 3
        assert timeline.publication.keyword == "kw"


class TestRankingCheckSummary:
    def test_all_zero_default(self) -> None:
        s = RankingCheckSummary(checked_count=0, found_count=0, errors_count=0, duration_seconds=0)
        assert s.checked_count == 0

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RankingCheckSummary(checked_count=-1, found_count=0, errors_count=0, duration_seconds=0)
