"""pattern_card 모델·상수·저장 테스트."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    _extract_inserted_id,
    _save_to_supabase,
    load_pattern_card,
    migrate_pattern_card,
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
        assert PATTERN_CARD_SCHEMA_VERSION == "2.1"


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
        assert card.schema_version == "2.1"

    def test_roundtrip(self) -> None:
        card = _card()
        j = card.model_dump_json()
        loaded = PatternCard.model_validate_json(j)
        assert loaded.keyword == card.keyword
        assert loaded.schema_version == card.schema_version

    def test_intents_default_empty(self) -> None:
        """P1 — intents 필드는 default 빈 리스트."""
        card = _card()
        assert card.intents == []

    def test_intents_max_length(self) -> None:
        """P1 — intents 는 max 5개. 6개 입력 시 Pydantic 검증 실패."""
        import pytest
        from pydantic import ValidationError

        zero = RangeStats(avg=0, min=0, max=0)
        with pytest.raises(ValidationError):
            PatternCard(
                keyword="x",
                slug="x",
                analyzed_count=7,
                stats=PatternCardStats(chars=zero, subtitles=zero, keyword_density=zero),
                intents=["a", "b", "c", "d", "e", "f"],
            )


class TestSaveLoad:
    def test_save_and_load(self, tmp_path: object) -> None:
        from pathlib import Path

        out = Path(str(tmp_path))
        card = _card()
        path, supabase_id = save_pattern_card(card, out)
        assert path.exists()
        # Supabase 미설정 환경에서는 id None 이 정상 (graceful fire-and-forget).
        assert supabase_id is None or isinstance(supabase_id, str)
        loaded = load_pattern_card(path)
        assert loaded.keyword == "테스트"
        assert loaded.schema_version == "2.1"


class TestMigratePatternCard:
    """P1 — 2.0 → 2.1 migration. intents + DIA+ AEO 3종 default 주입."""

    def test_2_0_to_2_1_adds_intents(self) -> None:
        raw = {"schema_version": "2.0", "keyword": "x"}
        migrated = migrate_pattern_card(raw, "2.0", "2.1")
        assert migrated["intents"] == []
        assert migrated["schema_version"] == "2.1"

    def test_2_0_to_2_1_adds_dia_plus_aeo_keys(self) -> None:
        raw = {
            "schema_version": "2.0",
            "keyword": "x",
            "dia_plus": {"tables": 0.5},
        }
        migrated = migrate_pattern_card(raw, "2.0", "2.1")
        assert migrated["dia_plus"]["direct_answer_blocks"] == 0.0
        assert migrated["dia_plus"]["cited_sources"] == 0.0
        assert migrated["dia_plus"]["definition_blocks"] == 0.0
        # 기존 키 보존
        assert migrated["dia_plus"]["tables"] == 0.5

    def test_2_0_to_2_1_no_dia_plus_dict(self) -> None:
        """dia_plus 가 dict 가 아니면 변형하지 않음."""
        raw = {"schema_version": "2.0", "keyword": "x"}
        migrated = migrate_pattern_card(raw, "2.0", "2.1")
        assert "dia_plus" not in migrated or migrated.get("dia_plus") is None

    def test_same_version_passthrough(self) -> None:
        raw = {"schema_version": "2.1", "intents": ["a"]}
        migrated = migrate_pattern_card(raw, "2.1", "2.1")
        assert migrated is raw

    def test_unknown_version_passthrough(self) -> None:
        raw = {"schema_version": "1.0"}
        migrated = migrate_pattern_card(raw, "1.0", "2.1")
        assert migrated["schema_version"] == "2.1"

    def test_load_2_0_file_auto_migrates(self, tmp_path: object) -> None:
        """2.0 JSON 파일을 load 하면 자동으로 2.1 로 migrate 되어 PatternCard 반환."""
        import json
        from pathlib import Path

        path = Path(str(tmp_path)) / "old.json"
        raw = {
            "schema_version": "2.0",
            "keyword": "old",
            "slug": "old",
            "analyzed_count": 7,
            "stats": {
                "chars": {"avg": 0, "min": 0, "max": 0},
                "subtitles": {"avg": 0, "min": 0, "max": 0},
                "keyword_density": {"avg": 0, "min": 0, "max": 0},
            },
        }
        path.write_text(json.dumps(raw), encoding="utf-8")
        card = load_pattern_card(path)
        assert card.schema_version == "2.1"
        assert card.intents == []


class TestExtractInsertedId:
    """Phase B7 — Supabase insert 응답에서 id 안전 추출."""

    def test_normal_response(self) -> None:
        result = SimpleNamespace(data=[{"id": "abc-123", "keyword": "x"}])
        assert _extract_inserted_id(result) == "abc-123"

    def test_empty_data(self) -> None:
        assert _extract_inserted_id(SimpleNamespace(data=[])) is None

    def test_none_data(self) -> None:
        assert _extract_inserted_id(SimpleNamespace(data=None)) is None

    def test_no_data_attr(self) -> None:
        assert _extract_inserted_id(SimpleNamespace()) is None

    def test_first_row_no_id(self) -> None:
        result = SimpleNamespace(data=[{"keyword": "x"}])
        assert _extract_inserted_id(result) is None

    def test_first_row_id_none(self) -> None:
        result = SimpleNamespace(data=[{"id": None}])
        assert _extract_inserted_id(result) is None

    def test_first_row_not_dict(self) -> None:
        result = SimpleNamespace(data=["not a dict"])
        assert _extract_inserted_id(result) is None

    def test_id_coerced_to_str(self) -> None:
        result = SimpleNamespace(data=[{"id": 12345}])
        assert _extract_inserted_id(result) == "12345"


class TestSaveToSupabase:
    """Phase B7 — Supabase 호출 mock 기반 id 회수 / 실패 시 None."""

    def test_success_returns_id(self) -> None:
        card = _card()
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[{"id": "uuid-xyz"}]
        )
        with patch("config.supabase.get_client", return_value=client):
            assert _save_to_supabase(card, "/tmp/x") == "uuid-xyz"

    def test_failure_returns_none(self) -> None:
        card = _card()
        client = MagicMock()
        client.table.side_effect = RuntimeError("boom")
        with patch("config.supabase.get_client", return_value=client):
            assert _save_to_supabase(card, "/tmp/x") is None

    def test_empty_response_returns_none(self) -> None:
        card = _card()
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )
        with patch("config.supabase.get_client", return_value=client):
            assert _save_to_supabase(card, "/tmp/x") is None
