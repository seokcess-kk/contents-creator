"""pattern_card 모델·상수·저장 테스트."""

from __future__ import annotations

from domain.analysis.model import TargetReader
from domain.analysis.pattern_card import (
    DIFFERENTIATING_MAX_RATIO,
    DIFFERENTIATING_MIN_COUNT,
    DIFFERENTIATING_MIN_SAMPLES,
    FREQUENT_RATIO,
    PATTERN_CARD_SCHEMA_VERSION,
    REQUIRED_RATIO,
    PatternCard,
    PatternCardStats,
    RangeStats,
    load_pattern_card,
    save_pattern_card,
)


class TestConstants:
    def test_ratio_values(self) -> None:
        assert REQUIRED_RATIO == 0.8
        assert FREQUENT_RATIO == 0.5
        assert DIFFERENTIATING_MAX_RATIO == 0.3
        assert DIFFERENTIATING_MIN_COUNT == 2
        assert DIFFERENTIATING_MIN_SAMPLES == 10

    def test_schema_version(self) -> None:
        assert PATTERN_CARD_SCHEMA_VERSION == "2.0"


def _card() -> PatternCard:
    zero = RangeStats(avg=0, min=0, max=0)
    return PatternCard(
        keyword="테스트",
        slug="test-slug",
        analyzed_count=7,
        stats=PatternCardStats(chars=zero, subtitles=zero, keyword_density=zero),
        target_reader=TargetReader(
            concerns=["고민"], search_intent="정보 탐색", expertise_level="초보"
        ),
    )


class TestPatternCardModel:
    def test_default_schema_version(self) -> None:
        card = _card()
        assert card.schema_version == "2.0"

    def test_roundtrip(self) -> None:
        card = _card()
        j = card.model_dump_json()
        loaded = PatternCard.model_validate_json(j)
        assert loaded.keyword == card.keyword
        assert loaded.schema_version == card.schema_version


class TestSaveLoad:
    def test_save_and_load(self, tmp_path: object) -> None:
        from pathlib import Path

        out = Path(str(tmp_path))
        card = _card()
        path = save_pattern_card(card, out)
        assert path.exists()
        loaded = load_pattern_card(path)
        assert loaded.keyword == "테스트"
        assert loaded.schema_version == "2.0"
