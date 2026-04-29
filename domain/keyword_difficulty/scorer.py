"""SERP 구성 → 난이도 점수 + 등급.

CLAUDE.md 의 공식을 단일 출처로 구현. 임계값은 본 모듈 상수.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.keyword_difficulty.model import (
    DifficultyGrade,
    KeywordDifficulty,
    SearchVolume,
    SerpComposition,
    SovValueGrade,
)

# ── 등급 임계값 (CLAUDE.md 와 동기화) ─────────────────────────

MIN_TOTAL_FOR_VISIBILITY = 8  # 이 이하 SERP 는 missing 처리 (네이버가 다중 섹션 안 띄움)
HIGH_BLOG_SLOTS_THRESHOLD = 2  # B ≤ 2 면 슬롯 좁음
HIGH_SPAM_RATIO_THRESHOLD = 0.5  # D/T ≥ 0.5 면 도배 비중 높음
LOW_BLOG_SLOTS_THRESHOLD = 5  # B ≥ 5 면 SOV 점유 유리

# 점수 가중치 — 보고용 정량 지표 (낮을수록 노출 유리)
SPAM_WEIGHT = 1.5  # D 1개당 +1.5
BLOG_WEIGHT = 3.0  # B 1개당 -3.0

# ── SOV 가치 임계값 (검색량 + 경쟁강도) ─────────────────────────
# 운영 데이터 누적 후 조정 가능. 본 모듈이 단일 출처.

SOV_VOLUME_VERY_LOW = 100  # 검색량 100 미만 → low_value (검색 자체가 적음)
SOV_VOLUME_HIGH = 10_000  # 검색량 10,000 이상 → high 영역
SOV_VOLUME_VERY_HIGH = 50_000  # 검색량 50,000 이상 → 빅키워드 (overheated 위험)
_HIGH_COMPETITION_LITERAL = "높음"


def score_difficulty(
    keyword: str,
    composition: SerpComposition,
    *,
    search_volume: SearchVolume | None = None,
    checked_at: datetime | None = None,
) -> KeywordDifficulty:
    """SERP 구성을 받아 점수 + 등급을 산출한다.

    score = D × SPAM_WEIGHT - B × BLOG_WEIGHT

    Grade 판정 (우선순위 순):
    1. MISSING: T < 8 또는 B = 0
    2. HIGH: B ≤ 2 AND D/T ≥ 0.5
    3. LOW: B ≥ 5
    4. MEDIUM: 그 외

    `search_volume` 이 주어지면 별도 SOV 가치 등급도 함께 산출 (보조 지표).
    """
    blog = composition.blog_slots
    spam = composition.spam_cards
    total = composition.total_cards

    score = round(spam * SPAM_WEIGHT - blog * BLOG_WEIGHT, 2)
    grade = _decide_grade(blog=blog, spam=spam, total=total)
    sov_grade = score_sov_value(search_volume)

    return KeywordDifficulty(
        keyword=keyword,
        score=score,
        grade=grade,
        composition=composition,
        search_volume=search_volume,
        sov_grade=sov_grade,
        checked_at=checked_at or datetime.now(UTC),
    )


def score_sov_value(search_volume: SearchVolume | None) -> SovValueGrade:
    """검색량 + 경쟁강도 → SOV 점유 가치 등급.

    매트릭스 (검색량 × 경쟁강도):

    | 검색량 \\ 경쟁  | 낮음        | 중간        | 높음        |
    |----------------|-------------|-------------|-------------|
    | <100           | low_value   | low_value   | low_value   |
    | 100~10,000     | high_value  | moderate    | moderate    |
    | 10,000~50,000  | high_value  | moderate    | overheated  |
    | 50,000+        | moderate    | overheated  | overheated  |

    검색량 데이터 없음 → UNKNOWN.
    """
    if search_volume is None:
        return SovValueGrade.UNKNOWN

    total = search_volume.monthly_total
    high_competition = (search_volume.competition_idx or "") == _HIGH_COMPETITION_LITERAL
    low_competition = (search_volume.competition_idx or "") == "낮음"

    if total < SOV_VOLUME_VERY_LOW:
        return SovValueGrade.LOW_VALUE

    if total >= SOV_VOLUME_VERY_HIGH:
        # 빅키워드 — 경쟁 낮음일 때만 moderate, 그 외엔 과열
        return SovValueGrade.MODERATE if low_competition else SovValueGrade.OVERHEATED

    if total >= SOV_VOLUME_HIGH:
        # 검색량 중상 — 경쟁 높음이면 과열, 낮음이면 high_value
        if high_competition:
            return SovValueGrade.OVERHEATED
        if low_competition:
            return SovValueGrade.HIGH_VALUE
        return SovValueGrade.MODERATE

    # 검색량 100~10,000
    if low_competition:
        return SovValueGrade.HIGH_VALUE
    return SovValueGrade.MODERATE


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
