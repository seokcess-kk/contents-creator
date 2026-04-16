"""Crawler 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [1][2] 의 입출력 데이터 구조.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

MIN_COLLECTED_PAGES = 7

SerpSource = Literal["integrated", "blog_tab"]


class SerpResult(BaseModel):
    """네이버 블로그 검색 결과 1건.

    `source` 필드는 어느 SERP 트랙에서 수집됐는지 기록한다:
    - `integrated`: `where=blog` 통합검색의 블로그 섹션 (상위 노출 본체)
    - `blog_tab`: `ssc=tab.blog.all` 블로그 전용 탭 (통합검색이 표본 부족할 때 보충)

    패턴 카드까지 전파되어 교차 분석이 출처를 구분해 다룰 수 있게 한다.
    """

    rank: int = Field(ge=1)
    url: HttpUrl
    title: str
    snippet: str = ""
    source: SerpSource = "integrated"


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
