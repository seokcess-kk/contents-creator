"""Generation 도메인 테스트 공통 fixture."""

from __future__ import annotations

import pytest

from domain.analysis.model import TargetReader
from domain.analysis.pattern_card import (
    AggregatedAppealPoints,
    AggregatedTags,
    PatternCard,
    PatternCardStats,
    RangeStats,
    SectionClassification,
    TopStructure,
)
from domain.generation.model import (
    KeywordPlan,
    Outline,
    OutlineSection,
)


@pytest.fixture()
def sample_pattern_card() -> PatternCard:
    """테스트용 최소 PatternCard."""
    return PatternCard(
        keyword="다이어트 한의원",
        slug="diet-hanuiwon",
        analyzed_count=8,
        top_structures=[
            TopStructure(
                rank=1,
                sequence=["도입/공감", "정보제공", "방법제시", "요약"],
            ),
        ],
        sections=SectionClassification(
            required=["도입/공감", "방법제시", "요약"],
            frequent=["정보제공", "원인분석"],
            differentiating=["FAQ"],
        ),
        stats=PatternCardStats(
            chars=RangeStats(avg=2800, min=2100, max=3500),
            subtitles=RangeStats(avg=5, min=4, max=7),
            keyword_density=RangeStats(avg=0.013, min=0.009, max=0.017),
            subtitle_keyword_ratio=0.67,
            first_keyword_sentence=2.0,
            paragraph_avg_chars=95,
        ),
        distributions={
            "intro_type": {"공감형": 0.6, "통계형": 0.3, "질문형": 0.1},
            "title_pattern": {"질문형": 0.5, "방법론형": 0.3},
        },
        dia_plus={
            "tables": 0.8,
            "qa_sections": 0.6,
            "lists": 0.9,
            "statistics": 0.5,
        },
        target_reader=TargetReader(
            concerns=["다이어트 실패", "요요"],
            search_intent="정보 탐색",
            expertise_level="초보",
        ),
        related_keywords=["한약 다이어트", "체질 분석"],
        aggregated_appeal_points=AggregatedAppealPoints(
            common=["체질 분석 기반", "요요 방지"],
            promotional_ratio=0.6,
        ),
        aggregated_tags=AggregatedTags(
            common=["다이어트", "한의원"],
            frequent=["체질", "요요"],
            avg_tag_count_per_post=6.0,
        ),
    )


@pytest.fixture()
def sample_outline() -> Outline:
    """테스트용 Outline (도입부 섹션 포함)."""
    return Outline(
        title="다이어트 한의원 효과 정리",
        title_pattern="방법론형",
        target_chars=2800,
        suggested_tags=["다이어트", "한의원"],
        intro="체중 관리에 대한 관심이 높아지면서 한의원 다이어트를 찾는 분들이 늘고 있습니다. "
        "반복되는 요요와 실패 경험 속에서 한의학적 접근이 주목받는 이유를 정리했습니다.",
        sections=[
            OutlineSection(
                index=1,
                role="도입/공감",
                subtitle="(도입부)",
                is_intro=True,
            ),
            OutlineSection(
                index=2,
                role="정보제공",
                subtitle="한의원 다이어트가 주목받는 이유",
                summary="한의학적 접근 방법 설명",
                target_chars=450,
                dia_markers=["list"],
            ),
            OutlineSection(
                index=3,
                role="방법제시",
                subtitle="체질별 관리 방법 3가지",
                summary="체질에 따른 접근법",
                target_chars=520,
                dia_markers=["statistics"],
            ),
            OutlineSection(
                index=4,
                role="요약",
                subtitle="요점 정리",
                summary="핵심 내용 요약",
                target_chars=200,
            ),
        ],
        keyword_plan=KeywordPlan(
            main_keyword_target_count=14,
            subtitle_inclusion_target=0.67,
        ),
    )


@pytest.fixture()
def outline_without_intro(sample_outline: Outline) -> Outline:
    """is_intro=True 섹션이 제거된 Outline."""
    filtered = [s for s in sample_outline.sections if not s.is_intro]
    return sample_outline.model_copy(update={"sections": filtered})
