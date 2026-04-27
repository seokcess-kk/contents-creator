"""Ranking 도메인 Pydantic 모델.

SPEC-RANKING.md §3, §4 참조. publications + ranking_snapshots 시계열.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Publication(BaseModel):
    """네이버 블로그 URL 등록 단위.

    동일 url 재등록은 storage 레이어에서 멱등 처리(기존 row 반환).
    slug 는 본 프로젝트로 발행한 글이면 output/{slug}/ 매칭용으로 채우고,
    외부 URL 추적이면 None.

    url 은 nullable — draft 상태(재발행 임시 등)에서 None.
    visibility_status / workflow_status 는 직교 2축 상태 머신.
    """

    id: str | None = None  # Supabase 가 채워서 반환
    job_id: str | None = None
    keyword: str
    slug: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None

    # 상태 머신 — 직교 2축
    visibility_status: str = "not_measured"
    workflow_status: str = "active"

    # 운영 메타
    held_until: datetime | None = None
    held_reason: str | None = None
    parent_publication_id: str | None = None
    priority_score: float | None = None
    republishing_started_at: datetime | None = None


class RankingSnapshot(BaseModel):
    """SERP 측정 시점 1건. position=None 이면 미노출 (어느 섹션에서도 미발견).

    section: 매칭된 섹션명 (인플루언서/VIEW/인기글/뉴스/카페 등).
    position: 그 섹션 내 순위 (1부터). NULL = 미노출.
    append-only. update/delete 정책 없음.
    """

    id: str | None = None
    publication_id: str
    section: str | None = None
    position: int | None = Field(default=None, ge=1)
    total_results: int | None = Field(default=None, ge=0)
    captured_at: datetime | None = None
    serp_html_path: str | None = None


class RankingTimeline(BaseModel):
    """publication + 그에 속한 snapshot 시계열 묶음 (조회용)."""

    publication: Publication
    snapshots: list[RankingSnapshot]


class RankingCheckSummary(BaseModel):
    """check_all_active_rankings 결과 요약 (스케줄러·CLI 용)."""

    checked_count: int = Field(ge=0)
    found_count: int = Field(ge=0)  # position 이 NOT NULL 인 건수
    errors_count: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)


class CalendarCell(BaseModel):
    """캘린더 1셀 — 한 publication 의 한 KST 일자 측정 결과."""

    section: str | None = None
    position: int | None = None


class CalendarRow(BaseModel):
    """월별 캘린더 1행 — publication 1건의 KST 일자별 최신 순위·섹션.

    days 키는 `YYYY-MM-DD` (KST), 값은 CalendarCell.
    측정 없는 날짜는 키 미존재.
    """

    publication: Publication
    days: dict[str, CalendarCell] = Field(default_factory=dict)


class RankingCalendar(BaseModel):
    """월별 캘린더 응답.

    month: `YYYY-MM` (KST 기준).
    rows: 등록된 publication 별 row.
    """

    month: str
    rows: list[CalendarRow]


class RankingDuplicateUrlError(Exception):
    """publications.url unique 제약 위반. orchestrator 에서 멱등 변환."""


class RankingMatchError(Exception):
    """SERP fetch/parse 실패 또는 매칭 자체 실패 (URL 정규식 미스)."""


class Top10Snapshot(BaseModel):
    """매 SERP 측정마다 추출되는 Top10 콘텐츠 1건.

    카니발라이제이션 감지·SOV 측정·경쟁 변화 분석의 기반 데이터.
    rank 는 1-based, section 은 serp_parser 가 분류한 섹션명.
    blog_id 는 작성자 식별자 (url_match._author_key 결과).
    """

    id: str | None = None
    keyword: str
    captured_at: datetime | None = None
    rank: int = Field(ge=1)
    url: str
    section: str | None = None
    blog_id: str | None = None
    is_ours: bool = False
