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
    """

    id: str | None = None  # Supabase 가 채워서 반환
    job_id: str | None = None
    keyword: str
    slug: str | None = None
    url: str
    published_at: datetime | None = None
    created_at: datetime | None = None


class RankingSnapshot(BaseModel):
    """SERP 측정 시점 1건. position=None 이면 100위 밖 (미발견).

    append-only. update/delete 정책 없음.
    """

    id: str | None = None
    publication_id: str
    position: int | None = Field(default=None, ge=1, le=100)
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


class RankingDuplicateUrlError(Exception):
    """publications.url unique 제약 위반. orchestrator 에서 멱등 변환."""


class RankingMatchError(Exception):
    """SERP fetch/parse 실패 또는 매칭 자체 실패 (URL 정규식 미스)."""
