"""패턴 카드 생성 테스트."""

from __future__ import annotations

from domain.analysis.model import (
    HookPattern,
    L1Analysis,
    L2Analysis,
    SectionInfo,
    TitlePattern,
    VisualAnalysis,
)
from domain.analysis.pattern_card import _p25_p75, build_pattern_card


class TestP25P75:
    def test_normal_range(self) -> None:
        values = [1000, 2000, 2500, 3000, 4000]
        result = _p25_p75(values)
        assert len(result) == 2
        assert result[0] < result[1]

    def test_single_value(self) -> None:
        result = _p25_p75([2000])
        assert len(result) == 2
        assert result[0] < result[1]

    def test_empty(self) -> None:
        result = _p25_p75([])
        assert result == [0, 0]


class TestBuildPatternCard:
    def _make_test_data(self) -> tuple[L1Analysis, L2Analysis, VisualAnalysis]:
        posts = [
            SectionInfo(total_chars=2000, total_paragraphs=10, subtitle_count=4, image_count=5),
            SectionInfo(total_chars=2500, total_paragraphs=12, subtitle_count=5, image_count=6),
            SectionInfo(total_chars=3000, total_paragraphs=15, subtitle_count=6, image_count=7),
            SectionInfo(total_chars=2200, total_paragraphs=11, subtitle_count=4, image_count=5),
            SectionInfo(total_chars=2800, total_paragraphs=14, subtitle_count=5, image_count=6),
        ]
        l1 = L1Analysis(post_count=5, per_post=posts)
        l2 = L2Analysis(
            title_patterns=[
                TitlePattern(type="질문형", count=3, weight=0.6),
                TitlePattern(type="방법론형", count=2, weight=0.4),
            ],
            hook_patterns=[
                HookPattern(type="공감형", count=3),
                HookPattern(type="통계형", count=2),
            ],
            persuasion_structures=["문제-원인-솔루션"],
            related_keywords=["피부과", "여드름", "관리"],
            lsi_keywords=["피부 관리법", "여드름 치료"],
        )
        visual = VisualAnalysis(
            dominant_palette=["#ffffff", "#333333", "#4a90d9"],
            layout_pattern="mixed",
            mood="전문적",
        )
        return l1, l2, visual

    def test_creates_card(self) -> None:
        l1, l2, visual = self._make_test_data()
        card = build_pattern_card("강남 피부과", l1, l2, visual)

        assert card.keyword == "강남 피부과"
        assert card.source_post_count == 5
        assert card.confidence == "high"

    def test_text_pattern_has_char_range(self) -> None:
        l1, l2, visual = self._make_test_data()
        card = build_pattern_card("test", l1, l2, visual)

        assert "char_range" in card.text_pattern
        assert len(card.text_pattern["char_range"]) == 2

    def test_visual_pattern_has_palette(self) -> None:
        l1, l2, visual = self._make_test_data()
        card = build_pattern_card("test", l1, l2, visual)

        assert "color_palette" in card.visual_pattern
        assert len(card.visual_pattern["color_palette"]) > 0

    def test_constraints_has_skeleton_and_free(self) -> None:
        l1, l2, visual = self._make_test_data()
        card = build_pattern_card("test", l1, l2, visual)

        assert "skeleton" in card.constraints
        assert "free" in card.constraints
        assert "char_range" in card.constraints["skeleton"]

    def test_low_confidence_for_few_posts(self) -> None:
        l1 = L1Analysis(
            post_count=3,
            per_post=[SectionInfo(total_chars=2000, subtitle_count=4, image_count=5)] * 3,
        )
        l2 = L2Analysis()
        visual = VisualAnalysis()
        card = build_pattern_card("test", l1, l2, visual)

        assert card.confidence == "low"
