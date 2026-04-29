"""SERP 구성 → 난이도 점수 + 등급.

CLAUDE.md 의 공식을 단일 출처로 구현. 임계값은 본 모듈 상수.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SerpComposition,
)

# ── 등급 임계값 (CLAUDE.md 와 동기화) ─────────────────────────

MIN_TOTAL_FOR_VISIBILITY = 8  # 이 이하 SERP 는 missing 처리 (네이버가 다중 섹션 안 띄움)
HIGH_BLOG_SLOTS_THRESHOLD = 2  # B ≤ 2 면 슬롯 좁음
HIGH_SPAM_RATIO_THRESHOLD = 0.5  # D/T ≥ 0.5 면 도배 비중 높음
LOW_BLOG_SLOTS_THRESHOLD = 5  # B ≥ 5 면 SOV 점유 유리

# 점수 가중치 — 보고용 정량 지표 (낮을수록 노출 유리)
SPAM_WEIGHT = 1.5  # D 1개당 +1.5
BLOG_WEIGHT = 3.0  # B 1개당 -3.0


def score_difficulty(
    keyword: str,
    composition: SerpComposition,
    *,
    checked_at: datetime | None = None,
) -> KeywordDifficulty:
    """SERP 구성을 받아 점수 + 등급을 산출한다.

    score = D × SPAM_WEIGHT - B × BLOG_WEIGHT

    Grade 판정 (우선순위 순):
    1. MISSING: T < 8 또는 B = 0
    2. HIGH: B ≤ 2 AND D/T ≥ 0.5
    3. LOW: B ≥ 5
    4. MEDIUM: 그 외
    """
    blog = composition.blog_slots
    spam = composition.spam_cards
    total = composition.total_cards

    score = round(spam * SPAM_WEIGHT - blog * BLOG_WEIGHT, 2)
    grade = _decide_grade(blog=blog, spam=spam, total=total)

    return KeywordDifficulty(
        keyword=keyword,
        score=score,
        grade=grade,
        composition=composition,
        checked_at=checked_at or datetime.now(UTC),
    )


def _decide_grade(*, blog: int, spam: int, total: int) -> DifficultyGrade:
    """등급 판정 — 임계값 단일 출처."""
    if total < MIN_TOTAL_FOR_VISIBILITY or blog == 0:
        return DifficultyGrade.MISSING

    spam_ratio = spam / total if total > 0 else 0.0
    if blog <= HIGH_BLOG_SLOTS_THRESHOLD and spam_ratio >= HIGH_SPAM_RATIO_THRESHOLD:
        return DifficultyGrade.HIGH

    if blog >= LOW_BLOG_SLOTS_THRESHOLD:
        return DifficultyGrade.LOW

    return DifficultyGrade.MEDIUM
