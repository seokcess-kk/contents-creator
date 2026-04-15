"""Crawler 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [1][2] 의 입출력 데이터 구조.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

MIN_COLLECTED_PAGES = 7


class SerpResult(BaseModel):
    """네이버 블로그 검색 결과 1건."""

    rank: int = Field(ge=1)
    url: HttpUrl
    title: str
    snippet: str = ""


class SerpResults(BaseModel):
    """키워드 1개의 SERP 수집 결과 묶음."""

    keyword: str
    collected_at: datetime
    results: list[SerpResult]


class BlogPage(BaseModel):
    """Web Unlocker 로 수집한 네이버 블로그 본문 1건."""

    idx: int = Field(ge=0)
    rank: int = Field(ge=1)
    url: HttpUrl
    mobile_url: HttpUrl
    html: str
    fetched_at: datetime
    retries: int = Field(ge=0, default=0)


class ScrapeFailure(BaseModel):
    """수집 실패한 URL 의 사유 기록."""

    idx: int
    rank: int
    url: HttpUrl
    reason: str


class ScrapeResult(BaseModel):
    """[2] 본문 수집 스테이지 출력 (성공 + 실패)."""

    successful: list[BlogPage]
    failed: list[ScrapeFailure]


class InsufficientCollectionError(Exception):
    """수집 성공 수가 MIN_COLLECTED_PAGES 미만일 때 발생."""

    def __init__(self, minimum: int, actual: int, stage: str) -> None:
        self.minimum = minimum
        self.actual = actual
        self.stage = stage
        super().__init__(f"{stage}: {actual} pages collected, minimum {minimum} required")
