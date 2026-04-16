"""Composer 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md [10] 네이버 호환 출력 조립 결과 타입.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssembledContent(BaseModel):
    """조립된 SEO 원고 결과.

    intro + body_sections 프로그래매틱 concat 결과.
    """

    title: str
    content_md: str = Field(description="마크다운 원고 전체 텍스트")


class NaverHtmlDocument(BaseModel):
    """네이버 호환 HTML 변환 결과."""

    html: str = Field(description="<!DOCTYPE html> 래핑된 전체 HTML")
    warnings: list[str] = Field(
        default_factory=list,
        description="변환 중 발생한 경고 (중첩 리스트 평탄화 등)",
    )


class OutlineMarkdown(BaseModel):
    """outline.json -> outline.md 변환 결과."""

    content: str = Field(description="사람 검토용 마크다운 텍스트")
