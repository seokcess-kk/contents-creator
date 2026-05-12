"""아웃라인 생성 결과 검증. 미달 시 구체적 피드백 반환.

SPEC-SEO-TEXT.md §3 [6] 후 품질 게이트.
패턴 카드 기준으로 섹션 수, 이미지 수, 도입부 길이를 코드로 검증한다.

P1 (2026-05-12) — 첫 본문 섹션의 intent 응답 검증 추가. intents[0] 의 핵심 명사가
첫 본문 섹션(subtitle + summary)에 recall ≥ 0.4 이상 등장해야 통과. 형태소 매칭은
title_validator 와 동일한 kiwipiepy singleton 재사용 (cold start 비용 분담).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline

logger = logging.getLogger(__name__)

# P1 — intents[0] 명사가 첫 본문 섹션 (subtitle + summary) 에 recall 이 이 값 이상
# 이면 매칭 통과. 0.4 보수적 임계값 — 부분 일치 허용해 over-rejection 방지.
INTENT_RECALL_THRESHOLD = 0.4


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
    """아웃라인이 패턴 카드 기준을 충족하는지 검증.

    P1 — pattern_card.intents 가 있으면 첫 본문 섹션의 intent 응답을 추가 검증.
    """
    issues: list[OutlineIssue] = []
    issues.extend(_check_section_count(outline, pattern_card))
    issues.extend(_check_image_count(outline, pattern_card))
    issues.extend(_check_intro_length(outline))
    issues.extend(_check_first_section_intent(outline, pattern_card.intents))
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
    target = max(3, min(round(avg), 10)) if avg > 0 else 3

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


def _check_first_section_intent(
    outline: Outline,
    intents: list[str],
) -> list[OutlineIssue]:
    """P1 — 첫 본문 섹션이 intents[0] 의 핵심 명사 recall ≥ 0.4 충족 여부 검증.

    intents 가 빈 리스트면 skip (graceful — Haiku 호출 실패 시 자연 통과).
    kiwipiepy 미설치 환경에서도 skip — title_validator 의 fallback 정책과 일관.
    """
    if not intents:
        return []
    first_intent = intents[0].strip()
    if not first_intent:
        return []

    first_body = next((s for s in outline.sections if not s.is_intro), None)
    if first_body is None:
        return []

    section_text = (first_body.subtitle or "") + " " + (first_body.summary or "")
    if not section_text.strip():
        return [
            OutlineIssue(
                field="first_section_intent",
                expected=f"의도 '{first_intent}' 를 다루는 첫 본문 섹션",
                actual="첫 본문 섹션이 비어 있음",
            )
        ]

    # title_validator 의 kiwipiepy singleton 을 재사용 (cold start 분담).
    from domain.generation.title_validator import _extract_nouns, _get_kiwi

    kiwi = _get_kiwi()
    if kiwi is None:
        # kiwipiepy 미설치 → 형태소 검증 skip (보수적 통과). title_validator 와 동일 정책.
        logger.warning("intent_validation.kiwi_unavailable — skipping recall check")
        return []

    intent_nouns = _extract_nouns(kiwi, first_intent)
    if not intent_nouns:
        return []  # 명사 없는 intent (조사·종결만) → 신뢰 못 함, skip

    section_lower = section_text.lower()
    matched = sum(1 for noun in intent_nouns if noun.lower() in section_lower)
    recall = matched / len(intent_nouns)

    if recall < INTENT_RECALL_THRESHOLD:
        return [
            OutlineIssue(
                field="first_section_intent",
                expected=(
                    f"첫 본문 섹션이 의도 '{first_intent}' 의 핵심 명사를 "
                    f"recall ≥ {INTENT_RECALL_THRESHOLD} 이상 다룰 것"
                ),
                actual=f"recall={recall:.2f} (명사 {matched}/{len(intent_nouns)} 일치)",
            )
        ]
    return []
