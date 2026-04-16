"""[5] 교차 분석 → 패턴 카드 (코드 집계, LLM 불필요).

SPEC-SEO-TEXT.md §3 [5] 구현. [3][4a][4b] 결과를 통합하여
비율 기반 임계값으로 패턴 카드를 생성한다.
"""

from __future__ import annotations

import logging
from collections import Counter

from domain.analysis.model import (
    AppealAnalysis,
    PhysicalAnalysis,
    SemanticAnalysis,
    TargetReader,
)
from domain.analysis.pattern_card import (
    DIFFERENTIATING_MAX_RATIO,
    DIFFERENTIATING_MIN_COUNT,
    DIFFERENTIATING_MIN_SAMPLES,
    FREQUENT_RATIO,
    REQUIRED_RATIO,
    AggregatedAppealPoints,
    AggregatedTags,
    PatternCard,
    PatternCardStats,
    RangeStats,
    SectionClassification,
    TagFrequency,
    TopStructure,
)

logger = logging.getLogger(__name__)


def cross_analyze(
    keyword: str,
    slug: str,
    physicals: list[PhysicalAnalysis],
    semantics: list[SemanticAnalysis],
    appeals: list[AppealAnalysis],
) -> PatternCard:
    """[3][4a][4b] 결과를 집계해 PatternCard 를 반환.

    LLM 호출 없음. 순수 코드 집계만 수행.
    """
    n = len(physicals)
    logger.info("cross_analyze keyword=%s n=%s", keyword, n)

    return PatternCard(
        keyword=keyword,
        slug=slug,
        analyzed_count=n,
        top_structures=_extract_top_structures(semantics),
        sections=_classify_sections(semantics, n),
        stats=_aggregate_stats(physicals),
        distributions=_aggregate_distributions(semantics),
        dia_plus=_aggregate_dia_plus(physicals, n),
        target_reader=_aggregate_target_reader(semantics),
        related_keywords=_extract_related_keywords(physicals),
        aggregated_appeal_points=_aggregate_appeal_points(appeals, n),
        aggregated_tags=_aggregate_tags(physicals, n),
    )


def _classify_sections(semantics: list[SemanticAnalysis], n: int) -> SectionClassification:
    """역할별 등장 비율로 필수/빈출/차별화 분류."""
    if n == 0:
        return SectionClassification()

    role_counts: Counter[str] = Counter()
    for sem in semantics:
        seen_roles: set[str] = set()
        for sec in sem.semantic_structure:
            if sec.role not in seen_roles:
                role_counts[sec.role] += 1
                seen_roles.add(sec.role)

    required = [r for r, c in role_counts.items() if c / n >= REQUIRED_RATIO]
    frequent = [r for r, c in role_counts.items() if FREQUENT_RATIO <= c / n < REQUIRED_RATIO]

    if n >= DIFFERENTIATING_MIN_SAMPLES:
        differentiating = [
            r
            for r, c in role_counts.items()
            if c / n < DIFFERENTIATING_MAX_RATIO and c >= DIFFERENTIATING_MIN_COUNT
        ]
    else:
        differentiating = []

    return SectionClassification(
        required=required,
        frequent=frequent,
        differentiating=differentiating,
    )


def _aggregate_stats(physicals: list[PhysicalAnalysis]) -> PatternCardStats:
    """정량 통계 집계 (min/max/avg)."""
    if not physicals:
        zero = RangeStats(avg=0, min=0, max=0)
        return PatternCardStats(chars=zero, subtitles=zero, keyword_density=zero)

    chars = [float(p.total_chars) for p in physicals]
    subs = [float(p.subtitle_count) for p in physicals]
    dens = [p.keyword_analysis.density for p in physicals]

    return PatternCardStats(
        chars=_range(chars),
        subtitles=_range(subs),
        keyword_density=_range(dens),
        subtitle_keyword_ratio=_avg([p.keyword_analysis.subtitle_keyword_ratio for p in physicals]),
        first_keyword_sentence=_avg(
            [float(p.keyword_analysis.first_appearance_sentence) for p in physicals]
        ),
        paragraph_avg_chars=_avg([p.paragraph_stats.avg_paragraph_chars for p in physicals]),
    )


def _aggregate_distributions(
    semantics: list[SemanticAnalysis],
) -> dict[str, dict[str, float]]:
    """도입 방식, 마무리 방식, 제목 패턴 분포."""
    n = len(semantics)
    if n == 0:
        return {"intro_type": {}, "ending_type": {}, "title_pattern": {}}

    hook_counter: Counter[str] = Counter(s.hook_type for s in semantics)
    title_counter: Counter[str] = Counter(s.title_pattern for s in semantics)
    ending_counter: Counter[str] = Counter()
    for sem in semantics:
        if sem.semantic_structure:
            ending_counter[sem.semantic_structure[-1].role] += 1

    return {
        "intro_type": {k: round(v / n, 2) for k, v in hook_counter.items()},
        "ending_type": {k: round(v / n, 2) for k, v in ending_counter.items()},
        "title_pattern": {k: round(v / n, 2) for k, v in title_counter.items()},
    }


def _aggregate_dia_plus(physicals: list[PhysicalAnalysis], n: int) -> dict[str, float]:
    """DIA+ 요소별 사용 비율."""
    if n == 0:
        return {}
    return {
        "tables": round(sum(1 for p in physicals if p.dia_plus.tables > 0) / n, 2),
        "lists": round(sum(1 for p in physicals if p.dia_plus.lists > 0) / n, 2),
        "blockquotes": round(sum(1 for p in physicals if p.dia_plus.blockquotes > 0) / n, 2),
        "bold": round(sum(1 for p in physicals if p.dia_plus.bold_count > 0) / n, 2),
        "separators": round(sum(1 for p in physicals if p.dia_plus.separators > 0) / n, 2),
        "qa_sections": round(sum(1 for p in physicals if p.dia_plus.qa_sections) / n, 2),
        "statistics": round(sum(1 for p in physicals if p.dia_plus.statistics_data) / n, 2),
    }


def _aggregate_target_reader(semantics: list[SemanticAnalysis]) -> TargetReader:
    """공통 고민 키워드, 검색 의도, 정보 수준 집계."""
    if not semantics:
        return TargetReader()

    concern_counter: Counter[str] = Counter()
    intent_counter: Counter[str] = Counter()
    level_counter: Counter[str] = Counter()
    for sem in semantics:
        for c in sem.target_reader.concerns:
            concern_counter[c] += 1
        if sem.target_reader.search_intent:
            intent_counter[sem.target_reader.search_intent] += 1
        if sem.target_reader.expertise_level:
            level_counter[sem.target_reader.expertise_level] += 1

    top_concerns = [c for c, _ in concern_counter.most_common(5)]
    top_intent = intent_counter.most_common(1)[0][0] if intent_counter else ""
    top_level = level_counter.most_common(1)[0][0] if level_counter else ""

    return TargetReader(
        concerns=top_concerns,
        search_intent=top_intent,
        expertise_level=top_level,
    )


def _aggregate_appeal_points(appeals: list[AppealAnalysis], n: int) -> AggregatedAppealPoints:
    """공통 소구 포인트 + 홍보성 비율."""
    if not appeals or n == 0:
        return AggregatedAppealPoints()

    point_counter: Counter[str] = Counter()
    for ap in appeals:
        for pt in ap.appeal_points:
            point_counter[pt.point] += 1
    common = [p for p, c in point_counter.items() if c >= 2]

    promo_count = sum(1 for ap in appeals if ap.overall_promotional_level in ("medium", "high"))
    return AggregatedAppealPoints(
        common=common[:10],
        promotional_ratio=round(promo_count / n, 2),
    )


def _aggregate_tags(physicals: list[PhysicalAnalysis], n: int) -> AggregatedTags:
    """태그 집계. 태그 부재 시 빈 기본값 폴백 (lessons.md P2 발견 5)."""
    if n == 0 or not any(p.tags for p in physicals):
        return AggregatedTags()

    tag_counter: Counter[str] = Counter()
    total_tag_count = 0
    blogs_with_tags = 0
    for p in physicals:
        if p.tags:
            blogs_with_tags += 1
            total_tag_count += len(p.tags)
            for t in p.tags:
                tag_counter[t] += 1

    common = [t for t, c in tag_counter.items() if c / n >= REQUIRED_RATIO]
    frequent = [t for t, c in tag_counter.items() if FREQUENT_RATIO <= c / n < REQUIRED_RATIO]
    top_tags = [
        TagFrequency(tag=t, frequency=round(c / n, 2)) for t, c in tag_counter.most_common(20)
    ]
    avg_count = total_tag_count / blogs_with_tags if blogs_with_tags else 0.0

    return AggregatedTags(
        common=common,
        frequent=frequent,
        top_tags=top_tags,
        avg_tag_count_per_post=round(avg_count, 1),
    )


def _extract_top_structures(
    semantics: list[SemanticAnalysis], top_k: int = 3
) -> list[TopStructure]:
    """가장 빈번한 역할 시퀀스 상위 K개. 소제목 있는 블로그만 대상."""
    sequences: list[tuple[str, ...]] = []
    for sem in semantics:
        if len(sem.semantic_structure) > 1:
            seq = tuple(s.role for s in sem.semantic_structure)
            sequences.append(seq)

    if not sequences:
        return [TopStructure(rank=1, sequence=["정보제공"])]

    counter: Counter[tuple[str, ...]] = Counter(sequences)
    return [
        TopStructure(rank=i + 1, sequence=list(seq))
        for i, (seq, _) in enumerate(counter.most_common(top_k))
    ]


def _extract_related_keywords(physicals: list[PhysicalAnalysis]) -> list[str]:
    """연관 키워드 통합 (빈도 내림차순)."""
    counter: Counter[str] = Counter()
    for p in physicals:
        for kw in p.keyword_analysis.related_keywords:
            counter[kw] += 1
    return [kw for kw, _ in counter.most_common(10)]


def _range(values: list[float]) -> RangeStats:
    return RangeStats(
        avg=round(sum(values) / len(values), 2),
        min=round(min(values), 2),
        max=round(max(values), 2),
    )


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0
