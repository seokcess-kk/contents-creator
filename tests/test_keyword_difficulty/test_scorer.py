"""scorer 단위 테스트 — SerpComposition 입력 → 점수 + 등급 검증.

CLAUDE.md 의 등급 임계값과 정합성 회귀.
"""

from __future__ import annotations

import pytest

from domain.keyword_difficulty.model import (
    DifficultyGrade,
    SerpComposition,
    SerpSection,
)
from domain.keyword_difficulty.scorer import (
    BLOG_WEIGHT,
    SPAM_WEIGHT,
    score_difficulty,
)


def _composition(
    *,
    blog_view: int = 0,
    influencer: int = 0,
    blog_integrated: int = 0,
    ad: int = 0,
    place: int = 0,
    shopping: int = 0,
    widget: int = 0,
    other: int = 0,
) -> SerpComposition:
    counts = {
        SerpSection.VIEW_BLOG: blog_view,
        SerpSection.INFLUENCER: influencer,
        SerpSection.BLOG_INTEGRATED: blog_integrated,
        SerpSection.AD: ad,
        SerpSection.PLACE: place,
        SerpSection.SHOPPING: shopping,
        SerpSection.WIDGET: widget,
        SerpSection.OTHER: other,
    }
    counts = {k: v for k, v in counts.items() if v > 0}
    total = sum(counts.values())
    return SerpComposition(section_counts=counts, total_cards=total)


class TestComposition:
    def test_blog_slots_aggregates_three_sources(self) -> None:
        c = _composition(blog_view=2, influencer=1, blog_integrated=3)
        assert c.blog_slots == 6

    def test_spam_cards_aggregates_four_sources(self) -> None:
        c = _composition(ad=3, place=2, shopping=1, widget=1)
        assert c.spam_cards == 7


class TestGrade:
    def test_missing_when_total_under_8(self) -> None:
        c = _composition(ad=2, place=1, blog_view=1)  # total=4
        result = score_difficulty("BMI계산하기", c)
        assert result.grade == DifficultyGrade.MISSING

    def test_missing_when_no_blog_slot(self) -> None:
        c = _composition(ad=5, shopping=4, widget=2)  # total=11, blog=0
        result = score_difficulty("감비정", c)
        assert result.grade == DifficultyGrade.MISSING

    def test_high_when_few_slots_and_spam_dominant(self) -> None:
        # B=2, T=20, D=15 (광고+쇼핑+플레이스), spam_ratio=0.75
        c = _composition(blog_view=2, ad=8, shopping=4, place=3, other=3)
        result = score_difficulty("다이어트약", c)
        assert result.grade == DifficultyGrade.HIGH

    def test_low_when_blog_slots_5_or_more(self) -> None:
        # B=6, T=15
        c = _composition(blog_view=3, influencer=2, blog_integrated=1, ad=4, other=5)
        result = score_difficulty("다이어트식단", c)
        assert result.grade == DifficultyGrade.LOW

    def test_medium_when_3_or_4_slots(self) -> None:
        c = _composition(blog_view=3, ad=5, other=4)  # B=3, T=12, D=5
        result = score_difficulty("비만치료", c)
        assert result.grade == DifficultyGrade.MEDIUM

    def test_medium_when_few_slots_but_low_spam(self) -> None:
        # B=2, T=15, D=5, ratio=0.33 → HIGH 분기 미해당
        c = _composition(blog_view=2, ad=3, place=2, other=8)
        result = score_difficulty("작은키워드", c)
        assert result.grade == DifficultyGrade.MEDIUM


class TestScore:
    def test_score_formula(self) -> None:
        c = _composition(blog_view=3, influencer=1, ad=4, place=2)
        # B=4, D=6 → score = 6*1.5 - 4*3 = 9 - 12 = -3.0
        result = score_difficulty("test", c)
        expected = 6 * SPAM_WEIGHT - 4 * BLOG_WEIGHT
        assert result.score == round(expected, 2)

    def test_score_rounded_to_2_decimals(self) -> None:
        c = _composition(blog_view=1, ad=1)
        # 1*1.5 - 1*3.0 = -1.5
        result = score_difficulty("test", c)
        assert result.score == -1.5


@pytest.mark.parametrize(
    "kw,c,expected",
    [
        (
            "다이어트식단_가상",
            _composition(blog_view=3, influencer=2, blog_integrated=2, ad=5, place=2, other=10),
            DifficultyGrade.LOW,
        ),
        (
            "다이어트약_가상",
            _composition(blog_view=2, ad=8, shopping=3, place=2, other=3),
            DifficultyGrade.HIGH,
        ),
        ("BMI계산하기_가상", _composition(widget=3, ad=2), DifficultyGrade.MISSING),  # T=5
        (
            "천안다이어트한의원_가상",
            _composition(blog_view=4, influencer=2, place=3, ad=2, other=4),
            DifficultyGrade.LOW,
        ),
        (
            "비만치료_가상",
            _composition(blog_view=3, ad=4, place=1, other=5),
            DifficultyGrade.MEDIUM,
        ),
    ],
)
def test_grade_examples_consistency(kw: str, c: SerpComposition, expected: DifficultyGrade) -> None:
    """대화에서 분류한 키워드 패턴과 등급 판정이 일치하는지 회귀."""
    result = score_difficulty(kw, c)
    assert result.grade == expected, f"{kw}: {result.grade} (score={result.score})"
