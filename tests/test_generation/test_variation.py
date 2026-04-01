"""변이 엔진 테스트."""

from __future__ import annotations

from domain.analysis.model import PatternCard
from domain.generation.model import VariationConfig
from domain.generation.variation_engine import (
    format_variation_preview,
    recommend_variation,
)


def _make_card() -> PatternCard:
    return PatternCard(
        keyword="강남 피부과",
        text_pattern={
            "persuasion_structure": "문제-원인-솔루션",
            "hook_types": ["공감형", "통계형"],
        },
        visual_pattern={"color_palette": ["#333", "#fff", "#4a90d9"]},
    )


class TestRecommendVariation:
    def test_returns_config(self) -> None:
        card = _make_card()
        config = recommend_variation(card)
        assert isinstance(config, VariationConfig)
        assert config.structure != ""
        assert config.intro != ""

    def test_avoids_excluded(self) -> None:
        card = _make_card()
        first = recommend_variation(card)

        # 10회 시도하면 다른 조합이 나와야 함
        different_found = False
        for _ in range(10):
            second = recommend_variation(card, exclude_configs=[first])
            if second.structure != first.structure or second.intro != first.intro:
                different_found = True
                break
        assert different_found

    def test_all_fields_populated(self) -> None:
        card = _make_card()
        config = recommend_variation(card)
        assert config.structure
        assert config.intro
        assert config.subtitle_style
        assert config.expression_tone
        assert config.image_placement


class TestFormatPreview:
    def test_contains_all_layers(self) -> None:
        config = VariationConfig(
            structure="문제해결형",
            intro="통계형",
            subtitle_style="질문형",
            expression_tone="자연스러운",
            image_placement="균등분산형",
        )
        preview = format_variation_preview(config)
        assert "구조" in preview
        assert "도입부" in preview
        assert "소제목" in preview
        assert "이미지 배치" in preview
        assert "승인" in preview
