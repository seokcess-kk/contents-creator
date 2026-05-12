"""cross_analyzer 단위 테스트. LLM 호출 없음. fixture 데이터로 집계 검증."""

from __future__ import annotations

from domain.analysis.cross_analyzer import (
    _aggregate_dia_plus,
    _aggregate_distributions,
    _aggregate_stats,
    _aggregate_tags,
    _classify_sections,
    _dedupe_and_rank_intents,
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
        # 모든 글에 소제목 ≥ 2 보장 (FAQ 50% 가 소제목 분모 기준 검증되도록)
        sems = [_semantic(["정보제공", "요약"])] * 10
        sems[0] = _semantic(["정보제공", "요약", "FAQ"])
        sems[1] = _semantic(["정보제공", "요약", "FAQ"])
        sems[2] = _semantic(["정보제공", "요약", "FAQ"])
        sems[3] = _semantic(["정보제공", "요약", "FAQ"])
        sems[4] = _semantic(["정보제공", "요약", "FAQ"])
        result = _classify_sections(sems, 10)
        assert "정보제공" in result.required
        assert "FAQ" in result.frequent

    def test_n_under_10_no_differentiating(self) -> None:
        # 7개 모두 섹션 ≥ 2 보장하여 분모(=7)가 임계 검증되도록
        sems = [_semantic(["정보제공", "요약"])] * 7
        sems[0] = _semantic(["정보제공", "요약", "전문가의견"])
        sems[1] = _semantic(["정보제공", "요약", "전문가의견"])
        result = _classify_sections(sems, 7)
        assert result.differentiating == []

    def test_differentiating_with_n_10(self) -> None:
        sems = [_semantic(["정보제공", "요약"])] * 10
        sems[0] = _semantic(["정보제공", "요약", "전문가의견"])
        sems[1] = _semantic(["정보제공", "요약", "전문가의견"])
        result = _classify_sections(sems, 10)
        assert "전문가의견" in result.differentiating

    def test_all_single_section_returns_empty(self) -> None:
        """소제목 0개(섹션 1개) 글만 있으면 구조 분류는 비어야 한다 (lessons P2 발견 4)."""
        sems = [_semantic(["정보제공"])] * 10
        result = _classify_sections(sems, 10)
        assert result.required == []
        assert result.frequent == []
        assert result.differentiating == []

    def test_only_structured_blogs_count_for_ratio(self) -> None:
        """단일 섹션 글은 분모에서 제외되어야 한다.

        섹션 ≥ 2 인 블로그 5개 중 5개 모두 "정보제공" 보유 → 100% → required.
        단일 섹션 글 5개가 추가되어도 결과는 동일해야 한다.
        """
        sems = [_semantic(["정보제공", "요약"])] * 5 + [_semantic(["정보제공"])] * 5
        result = _classify_sections(sems, 10)
        assert "정보제공" in result.required
        assert "요약" in result.required


class TestAggregateDistributions:
    def test_ending_type_only_structured(self) -> None:
        """ending_type 은 소제목 있는 블로그만 분모. 단일 섹션 글의 역할은 ending 으로 잡지 않는다."""
        sems = [_semantic(["도입/공감", "요약"])] * 5 + [_semantic(["정보제공"])] * 5
        dist = _aggregate_distributions(sems)
        assert dist["ending_type"] == {"요약": 1.0}
        # intro/title 은 모든 글 대상 → 분모 10
        assert dist["intro_type"]["공감형"] == 1.0
        assert dist["title_pattern"]["방법론형"] == 1.0

    def test_all_single_section_ending_empty(self) -> None:
        sems = [_semantic(["정보제공"])] * 7
        dist = _aggregate_distributions(sems)
        assert dist["ending_type"] == {}
        assert dist["intro_type"]["공감형"] == 1.0


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

    def test_aeo_signals_present(self) -> None:
        """P1 — AEO 신호 3종 키가 집계 결과에 포함."""
        ps = [_physical()] * 5
        result = _aggregate_dia_plus(ps, 5)
        assert "direct_answer_blocks" in result
        assert "cited_sources" in result
        assert "definition_blocks" in result
        # default DiaPlus 의 3 필드는 0 → 비율 0.0
        assert result["direct_answer_blocks"] == 0.0
        assert result["cited_sources"] == 0.0
        assert result["definition_blocks"] == 0.0

    def test_aeo_signals_ratio_with_partial(self) -> None:
        """P1 — 일부 글에만 신호 있을 때 ratio 정확."""
        ps_with = [
            PhysicalAnalysis(
                url="https://blog.naver.com/x/100000001",  # type: ignore[arg-type]
                title="t",
                total_chars=2000,
                total_paragraphs=10,
                subtitle_count=3,
                keyword_analysis=KeywordAnalysis(
                    main_keyword="k",
                    first_appearance_sentence=1,
                    total_count=5,
                    density=0.01,
                    subtitle_keyword_ratio=0.5,
                    title_keyword_position="front",
                ),
                dia_plus=DiaPlus(
                    tables=0,
                    lists=0,
                    blockquotes=0,
                    bold_count=0,
                    separators=0,
                    qa_sections=False,
                    statistics_data=False,
                    direct_answer_blocks=2,
                    cited_sources=3,
                    definition_blocks=1,
                ),
                paragraph_stats=ParagraphStats(
                    avg_paragraph_chars=100.0,
                    avg_sentence_chars=30.0,
                    short_paragraph_ratio=0.1,
                ),
                section_ratios=SectionRatios(intro=0.15, body=0.7, conclusion=0.15),
            )
        ]
        ps_without = [_physical()] * 4
        result = _aggregate_dia_plus(ps_with + ps_without, 5)
        # 5 글 중 1 글만 신호 보유 → 0.2
        assert result["direct_answer_blocks"] == 0.2
        assert result["cited_sources"] == 0.2
        assert result["definition_blocks"] == 0.2


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
    def test_no_subtitles_returns_empty(self) -> None:
        """소제목 0~1개 글만 있으면 빈 리스트. prompt_builder 가 자체 설계 분기로 진입하도록."""
        sems = [_semantic(["정보제공"])] * 7
        result = _extract_top_structures(sems)
        assert result == []

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
        assert card.schema_version == "2.1"

    def test_intents_default_empty(self) -> None:
        """P1 — page_intents 미지정 시 intents 빈 리스트."""
        ps = [_physical()] * 7
        sems = [_semantic()] * 7
        apps = [_appeal()] * 7
        card = cross_analyze("kw", "slug", ps, sems, apps)
        assert card.intents == []

    def test_intents_populated_from_page_intents(self) -> None:
        """P1 — page_intents 가 dedupe + 빈도순 순위로 PatternCard.intents 에 주입."""
        ps = [_physical()] * 3
        sems = [_semantic()] * 3
        apps = [_appeal()] * 3
        page_intents = [
            ["비용", "보철물 종류", "회복 기간"],
            ["비용", "회복 기간"],
            ["비용", "사후 관리"],
        ]
        card = cross_analyze("kw", "slug", ps, sems, apps, page_intents=page_intents)
        # 비용 3회 > 회복 기간 2회 > 보철물 종류 1회 = 사후 관리 1회 (첫 등장 순)
        assert card.intents[0] == "비용"
        assert card.intents[1] == "회복 기간"


class TestDedupeAndRankIntents:
    """P1 — 페이지별 intent 빈도순 dedup."""

    def test_empty(self) -> None:
        assert _dedupe_and_rank_intents([]) == []

    def test_all_empty_pages(self) -> None:
        assert _dedupe_and_rank_intents([[], [], []]) == []

    def test_frequency_order(self) -> None:
        result = _dedupe_and_rank_intents(
            [
                ["A", "B"],
                ["A", "C"],
                ["A"],
            ]
        )
        # A:3, B:1, C:1 → A 가 첫번째, B/C 는 첫 등장 순
        assert result[0] == "A"
        assert "B" in result and "C" in result

    def test_case_insensitive_dedup(self) -> None:
        """대소문자·공백 정규화로 동일 의도 카운트."""
        result = _dedupe_and_rank_intents(
            [
                ["비용 정보"],
                [" 비용  정보 "],  # 공백 차이 → 동일
            ]
        )
        # 1개로 dedupe
        assert len(result) == 1

    def test_max_5(self) -> None:
        page_intents = [["a", "b", "c", "d", "e", "f", "g"]]
        result = _dedupe_and_rank_intents(page_intents)
        assert len(result) == 5

    def test_same_intent_in_one_page_counted_once(self) -> None:
        """한 페이지 내 중복은 1회만."""
        result = _dedupe_and_rank_intents(
            [
                ["A", "A", "A", "B"],  # A 1회로 카운트
                ["A", "B"],
            ]
        )
        # A:2, B:2 → 첫 등장 A 우선
        assert result == ["A", "B"]
