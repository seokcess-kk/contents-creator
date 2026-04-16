"""아웃라인 생성 결과 검증. 미달 시 구체적 피드백 반환.

SPEC-SEO-TEXT.md §3 [6] 후 품질 게이트.
패턴 카드 기준으로 섹션 수, 이미지 수, 도입부 길이를 코드로 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline


@dataclass
class OutlineIssue:
    """아웃라인 검증 이슈 1건."""

    field: str
    expected: str
    actual: str


def validate_outline(
    outline: Outline,
    pattern_card: PatternCard,
) -> list[OutlineIssue]:
    """아웃라인이 패턴 카드 기준을 충족하는지 검증."""
    issues: list[OutlineIssue] = []
    issues.extend(_check_section_count(outline, pattern_card))
    issues.extend(_check_image_count(outline, pattern_card))
    issues.extend(_check_intro_length(outline))
    return issues


def _check_section_count(
    outline: Outline,
    pattern_card: PatternCard,
) -> list[OutlineIssue]:
    """섹션 수 검증 (intro 제외)."""
    non_intro = [s for s in outline.sections if not s.is_intro]
    required = len(pattern_card.sections.required)
    frequent = len(pattern_card.sections.frequent)
    min_sections = max(required + frequent, 3)

    if len(non_intro) < min_sections:
        return [
            OutlineIssue(
                field="section_count",
                expected=f">={min_sections}",
                actual=str(len(non_intro)),
            )
        ]
    return []


def _check_image_count(
    outline: Outline,
    pattern_card: PatternCard,
) -> list[OutlineIssue]:
    """이미지 수 검증."""
    avg = pattern_card.image_pattern.avg_count_per_post
    target = max(3, round(avg)) if avg > 0 else 3

    if len(outline.image_prompts) < target:
        return [
            OutlineIssue(
                field="image_count",
                expected=f">={target}",
                actual=str(len(outline.image_prompts)),
            )
        ]
    return []


def _check_intro_length(outline: Outline) -> list[OutlineIssue]:
    """도입부 길이 검증 (150~400자 허용 범위)."""
    intro_len = len(outline.intro)
    if intro_len < 150 or intro_len > 400:
        return [
            OutlineIssue(
                field="intro_length",
                expected="200~300자 (150~400 허용)",
                actual=f"{intro_len}자",
            )
        ]
    return []
