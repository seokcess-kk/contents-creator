"""Image Generation 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [9] 기반. [6] outline 에서 생성된 image_prompt 와
Gemini 생성 결과를 구조화한다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImagePrompt(BaseModel):
    """[6] outline 에서 생성된 이미지 prompt 1건."""

    sequence: int = Field(description="1부터 시작하는 순번")
    position: str = Field(
        description="after_intro / section_N_end / before_conclusion 등 위치 힌트"
    )
    prompt: str = Field(description="Gemini 에 전달할 영어 prompt 전문")
    alt_text: str = Field(description="한국어 alt 텍스트 (네이버 에디터 alt 입력란용)")
    image_type: str = Field(description="photo / illustration / infographic / diagram")
    aspect_ratio: str = Field(
        default="1:1", description="이미지 종횡비 (1:1, 3:4, 4:3, 9:16, 16:9)"
    )
    rationale: str = Field(description="1줄 위치·소재 결정 근거")


class GeneratedImage(BaseModel):
    """생성 성공한 이미지 1건."""

    sequence: int
    path: str = Field(description="상대 경로 images/image_{sequence}.png")
    prompt_hash: str = Field(description="SHA256 hex digest")
    alt_text: str


class SkippedImage(BaseModel):
    """생성 스킵된 이미지 1건."""

    sequence: int
    reason: str = Field(
        description="compliance_failed / api_error / budget_exceeded / prompt_safety_failed"
    )


class ImageGenerationResult(BaseModel):
    """[9] 전체 이미지 생성 결과."""

    generated: list[GeneratedImage] = Field(default_factory=list)
    skipped: list[SkippedImage] = Field(default_factory=list)
