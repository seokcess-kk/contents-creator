"""크롤러 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel


class NaverSearchResult(BaseModel):
    """네이버 검색 API 응답의 개별 항목."""

    title: str
    link: str
    description: str
    blogger_name: str = ""
    blogger_link: str = ""
    post_date: str = ""  # yyyymmdd


class PostData(BaseModel):
    """크롤링된 블로그 포스트 데이터."""

    rank: int
    url: str
    title: str = ""
    raw_html: str = ""
    text_content: str = ""
    screenshot_path: str = ""
    post_date: str = ""
    success: bool = True
    error: str = ""


class CrawlResult(BaseModel):
    """키워드 크롤링 전체 결과."""

    keyword: str
    top_n: int
    posts: list[PostData] = []
    total_success: int = 0
    total_failed: int = 0
    workspace_path: str = ""


class PageData(BaseModel):
    """일반 웹페이지 크롤링 결과 (프로필 추출용)."""

    url: str
    title: str = ""
    raw_html: str = ""
    text_content: str = ""
    success: bool = True
    error: str = ""
