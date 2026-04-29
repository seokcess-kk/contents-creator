"""키워드 난이도 분석 도메인 모델."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SerpSection(StrEnum):
    """네이버 통합검색 1페이지의 카드 카테고리.

    단순 분류 — 한 카드는 한 섹션으로 분류된다.
    """

    AD = "ad"  # 파워링크·비즈사이트·매거진 광고
    PLACE = "place"  # 지도/플레이스/인기업체
    SHOPPING = "shopping"  # 네이버쇼핑 카드
    WIDGET = "widget"  # BMI 계산기·약학정보·지식백과·환율 등 도구·정보 위젯
    INFLUENCER = "influencer"  # 인플루언서 인증 콘텐츠
    VIEW_BLOG = "view_blog"  # VIEW 영역의 블로그 항목
    BLOG_INTEGRATED = "blog_integrated"  # 블로그 통합 영역
    CAFE = "cafe"  # 카페 글
    KNOWLEDGE_IN = "knowledge_in"  # 지식iN
    NEWS = "news"  # 뉴스
    OTHER = "other"  # 미분류


# ── SOV 점유 가능 슬롯 ─────────────────────────────────────────
# B (블로그 슬롯) = VIEW_BLOG + INFLUENCER + BLOG_INTEGRATED
BLOG_SLOT_SECTIONS: tuple[SerpSection, ...] = (
    SerpSection.VIEW_BLOG,
    SerpSection.INFLUENCER,
    SerpSection.BLOG_INTEGRATED,
)

# D (도배 카드) = AD + PLACE + SHOPPING + WIDGET
SPAM_SECTIONS: tuple[SerpSection, ...] = (
    SerpSection.AD,
    SerpSection.PLACE,
    SerpSection.SHOPPING,
    SerpSection.WIDGET,
)


class SerpComposition(BaseModel):
    """SERP 1페이지의 섹션별 카드 수 + 총합.

    `parse_serp()` 의 반환값. `scorer` 가 이를 받아 등급 산출.
    """

    section_counts: dict[SerpSection, int] = Field(default_factory=dict)
    total_cards: int = 0

    @property
    def blog_slots(self) -> int:
        """B — VIEW 블로그 + 인플루언서 + 블로그 통합 합."""
        return sum(self.section_counts.get(s, 0) for s in BLOG_SLOT_SECTIONS)

    @property
    def spam_cards(self) -> int:
        """D — 광고 + 플레이스 + 쇼핑 + 위젯 합."""
        return sum(self.section_counts.get(s, 0) for s in SPAM_SECTIONS)


class DifficultyGrade(StrEnum):
    """블로그 진입 난이도 4단계.

    - MISSING: SERP 짧거나 블로그 슬롯 부재 → 노출 자체 불가
    - HIGH: 슬롯 좁음 + 도배 다수 → 매우 어려움
    - MEDIUM: 그 외 (슬롯 3~4 또는 도배 적음) → 보통
    - LOW: 슬롯 5+ → 노출 유리
    """

    MISSING = "missing"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SovValueGrade(StrEnum):
    """SOV 점유 가치 4단계 — 검색량 × 경쟁강도로 산출.

    노출 난이도(DifficultyGrade)와 별개의 보조 지표. SERP 진입 가능성과
    SOV 점유로 얻는 실효 가치를 분리해 의사결정에 활용.

    - LOW_VALUE: 검색량 자체가 적어 SOV 점유 효용 작음
    - MODERATE: 적정 검색량, 통상적인 SOV 가치
    - HIGH_VALUE: 검색량 충분 + 경쟁 합리적, SOV 점유 가치 큼 (우선 작업)
    - OVERHEATED: 검색량 매우 큼 + 경쟁 과열, 슬롯 다수지만 인플루언서·광고에 밀림
    - UNKNOWN: 검색량 데이터 미수신 (네이버 API 미설정·실패)
    """

    LOW_VALUE = "low_value"
    MODERATE = "moderate"
    HIGH_VALUE = "high_value"
    OVERHEATED = "overheated"
    UNKNOWN = "unknown"


class SearchVolume(BaseModel):
    """네이버 검색광고 API 의 월간 검색량 — `naver_ad_client.get_search_volume` 반환값.

    한 자릿수 검색량은 네이버 응답이 `< 10` 같은 문자열로 오므로 `monthly_pc_qc/monthly_mobile_qc`
    는 정수 0~N. 응답이 비숫자면 0 으로 정규화.
    """

    monthly_pc: int = 0
    monthly_mobile: int = 0
    competition_idx: str | None = None  # "낮음" / "중간" / "높음" 또는 미수신 시 None

    @property
    def monthly_total(self) -> int:
        return self.monthly_pc + self.monthly_mobile


class KeywordDifficulty(BaseModel):
    """단일 키워드 난이도 분석 결과 — `scorer.score_difficulty` 의 반환값."""

    keyword: str
    score: float
    grade: DifficultyGrade
    composition: SerpComposition
    search_volume: SearchVolume | None = None
    sov_grade: SovValueGrade = SovValueGrade.UNKNOWN
    checked_at: datetime | None = None


class SerpFetchError(Exception):
    """SERP HTML fetch 실패."""
