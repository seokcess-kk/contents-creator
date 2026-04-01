"""조합 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RenderedImage(BaseModel):
    """렌더링된 이미지."""

    image_type: str  # header / cta / ai
    source_html: str = ""
    output_path: str = ""
    success: bool = True
    error: str = ""


class ComposedOutput(BaseModel):
    """최종 조합 출력."""

    keyword: str = ""
    output_dir: str = ""
    final_html_path: str = ""
    paste_ready_path: str = ""
    images: list[RenderedImage] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
