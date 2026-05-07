"""Blog channel Pydantic 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BlogChannel(BaseModel):
    """blog_channels 1행 — 운영자가 보유한 네이버 블로그 채널 1개.

    name 은 운영자가 부르는 별칭 (UI 셀렉트 라벨). blog_id 는 네이버 블로그
    URL 의 식별자 (e.g., `https://blog.naver.com/myblog123` 의 `myblog123`).
    homepage_url 은 blog_id 로부터 도출되지만 명시 저장한다 — 다른 채널
    유형 (티스토리 등) 확장 대비.
    """

    id: str | None = None  # Supabase 가 채워서 반환
    name: str = Field(min_length=1, max_length=100)
    blog_id: str = Field(min_length=1, max_length=100)
    homepage_url: str
    memo: str | None = None
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BlogChannelDuplicateError(Exception):
    """name 또는 blog_id 가 이미 존재하는 경우. storage 레이어가 raise."""


__all__ = ["BlogChannel", "BlogChannelDuplicateError"]
