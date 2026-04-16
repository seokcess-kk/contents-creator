"""cross_analyzer 단위 테스트. LLM 호출 없음. fixture 데이터로 집계 검증."""

from __future__ import annotations

from domain.analysis.cross_analyzer import (
    _aggregate_dia_plus,
    _aggregate_stats,
    _aggregate_tags,
    _classify_sections,
    _extract_top_structures,
    cross_analyze,
)
from domain.analysis.model import (
    AppealAnalysis,
    AppealPoint,
    DiaPlus,
    KeywordAnalysis,
    ParagraphStats,
    PhysicalAnalysis,
    SectionRatios,
    SectionSemantic,
    SemanticAnalysis,
    TargetReader,
)
from domain.analysis.pattern_card import PATTERN_CARD_SCHEMA_VERSION


def _physical(
    chars: int = 2500, subtitles: int = 3, tags: list[str] | None = None
) -> PhysicalAnalysis:
    return PhysicalAnalysis(
        url="https://blog.naver.com/test/100000001",  # type: ignore[arg-type]
        title="test",
        total_chars=chars,
        total_paragraphs=10,
        subtitle_count=subtitles,
        keyword_analysis=KeywordAnalysis(
            main_keyword="kw",
            first_appearance_sentence=2,
            total_count=5,
            density=0.01,
            subtitle_keyword_ratio=0.5,
            title_keyword_position="front",
        ),
        dia_plus=DiaPlus(
            tables=1,
            lists=2,
            blockquotes=0,
            bold_count=3,
            separators=1,
            qa_sections=False,
            statistics_data=True,
        ),
        paragraph_stats=ParagraphStats(
            avg_paragraph_chars=120.0,
            avg_sentence_chars=40.0,
            short_paragraph_ratio=0.2,
        ),
        section_ratios=SectionRatios(intro=0.15, body=0.7, conclusion=0.15),
        tags=tags or [],
        tag_count=len(tags) if tags else 0,
    )


def _semantic(
    roles: list[str] | None = None,
    hook: str = "공감형",
    title_p: str = "방법론형",
) -> SemanticAnalysis:
    roles = roles or ["정보제공"]
    return SemanticAnalysis(
        url="https://blog.naver.com/test/100000001",  # type: ignore[arg-type]
        semantic_structure=[
            SectionSemantic(section=i + 1, role=r, summary="s", depth="중간")
            for i, r in enumerate(roles)
        ],
        title_pattern=title_p,  # type: ignore[arg-type]
        hook_type=hook,  # type: ignore[arg-type]
        target_reader=TargetReader(
            concerns=["고민A"], search_intent="정보 탐색", expertise_level="초보"
        ),
    )


def _appeal(level: str = "low") -> AppealAnalysis:
    return AppealAnalysis(
        url="https://blog.naver.com/test/100000001",  # type: ignore[arg-type]
        appeal_points=[
            AppealPoint(point="체질 분석", section=1, promotional_level=level)  # type: ignore[arg-type]
        ],
        subject_type="정보 주체",
        overall_promotional_level=level,  # type: ignore[arg-type]
    )


class TestClassifySections:
    def test_required_at_80(self) -> None:
        sems = [_semantic(["정보제공", "요약"]) for _ in range(10)]
        result = _classify_sections(sems, 10)
        assert "정보제공" in result.required
        assert "요약" in result.required

    def test_frequent_at_50(self) -> None:
        sems = [_semantic(["정보제공"])] * 10
        sems[0] = _semantic(["정보제공", "FAQ"])
        sems[1] = _semantic(["정보제공", "FAQ"])
        sems[2] = _semantic(["정보제공", "FAQ"])
        sems[3] = _semantic(["정보제공", "FAQ"])
        sems[4] = _semantic(["정보제공", "FAQ"])
        result = _classify_sections(sems, 10)
        assert "정보제공" in result.required
        assert "FAQ" in result.frequent

    def test_n_under_10_no_differentiating(self) -> None:
        sems = [_semantic(["정보제공"])] * 7
        sems[0] = _semantic(["정보제공", "전문가의견"])
        sems[1] = _semantic(["정보제공", "전문가의견"])
        result = _classify_sections(sems, 7)
        assert result.differentiating == []

    def test_differentiating_with_n_10(self) -> None:
        sems = [_semantic(["정보제공"])] * 10
        sems[0] = _semantic(["정보제공", "전문가의견"])
        sems[1] = _semantic(["정보제공", "전문가의견"])
        result = _classify_sections(sems, 10)
        assert "전문가의견" in result.differentiating


class TestAggregateStats:
    def test_range_calculation(self) -> None:
        ps = [_physical(chars=2000), _physical(chars=3000), _physical(chars=4000)]
        stats = _aggregate_stats(ps)
        assert stats.chars.min == 2000
        assert stats.chars.max == 4000
        assert stats.chars.avg == 3000


class TestAggregateDiaPlus:
    def test_ratio(self) -> None:
        ps = [_physical()] * 5
        result = _aggregate_dia_plus(ps, 5)
        assert result["tables"] == 1.0
        assert result["statistics"] == 1.0


class TestAggregateTags:
    def test_all_empty_fallback(self) -> None:
        ps = [_physical(tags=[]) for _ in range(7)]
        result = _aggregate_tags(ps, 7)
        assert result.common == []
        assert result.avg_tag_count_per_post == 0.0

    def test_partial_tags(self) -> None:
        ps = [_physical(tags=["다이어트", "건강"])] * 7 + [_physical(tags=[])] * 3
        result = _aggregate_tags(ps, 10)
        assert "다이어트" in result.common or "다이어트" in result.frequent
        assert result.avg_tag_count_per_post > 0


class TestTopStructures:
    def test_no_subtitles_fallback(self) -> None:
        sems = [_semantic(["정보제공"])] * 7
        result = _extract_top_structures(sems)
        assert len(result) == 1
        assert result[0].sequence == ["정보제공"]

    def test_mixed(self) -> None:
        sems = [
            _semantic(["도입/공감", "정보제공", "요약"]),
            _semantic(["도입/공감", "정보제공", "요약"]),
            _semantic(["정보제공"]),
        ]
        result = _extract_top_structures(sems)
        assert result[0].rank == 1
        assert len(result[0].sequence) == 3


class TestCrossAnalyze:
    def test_full_integration(self) -> None:
        n = 7
        ps = [_physical(chars=2000 + i * 100) for i in range(n)]
        sems = [_semantic(["정보제공", "요약"])] * n
        apps = [_appeal("low")] * n
        card = cross_analyze("테스트", "test-slug", ps, sems, apps)

        assert card.schema_version == PATTERN_CARD_SCHEMA_VERSION
        assert card.keyword == "테스트"
        assert card.slug == "test-slug"
        assert card.analyzed_count == n
        assert card.stats.chars.min == 2000
        assert len(card.sections.required) > 0

    def test_schema_version(self) -> None:
        ps = [_physical()] * 7
        sems = [_semantic()] * 7
        apps = [_appeal()] * 7
        card = cross_analyze("kw", "slug", ps, sems, apps)
        assert card.schema_version == "2.0"
