"""Generation 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [6][7] 의 출력 타입.
Outline (아웃라인 + 도입부), BodyResult (본문 섹션) 정의.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    """아웃라인 내 섹션 1개."""

    index: int = Field(ge=1)
    role: str
    subtitle: str
    summary: str = ""
    target_chars: int = Field(default=0, ge=0)
    dia_markers: list[str] = Field(default_factory=list)
    is_intro: bool = False


class ImagePromptItem(BaseModel):
    """[6] 에서 생성하는 AI 이미지 prompt 1건.

    Gemini Image 모델에 전달할 영어 prompt + 메타데이터.
    """

    sequence: int = Field(ge=1)
    position: str  # "after_intro", "section_N_end", "before_conclusion"
    prompt: str  # 영어 Gemini prompt
    alt_text: str  # 한국어 alt
    image_type: str  # "photo", "illustration", "infographic", "diagram"
    rationale: str


class KeywordPlan(BaseModel):
    """키워드 배치 계획."""

    main_keyword_target_count: int = Field(ge=0)
    subtitle_inclusion_target: float = Field(ge=0.0, le=1.0)


class Outline(BaseModel):
    """[6] 아웃라인 + 도입부 확정 출력.

    도입부 200~300자 확정본을 포함하며 [7] 에서 재생성하지 않는다 (톤 락).
    """

    title: str
    title_pattern: str
    target_chars: int = Field(ge=0)
    suggested_tags: list[str] = Field(default_factory=list)
    image_prompts: list[ImagePromptItem] = Field(default_factory=list)
    intro: str  # 200~300자 확정본
    sections: list[OutlineSection] = Field(default_factory=list)
    keyword_plan: KeywordPlan


class BodySection(BaseModel):
    """[7] 본문 섹션 1개."""

    index: int = Field(ge=1)
    subtitle: str
    content_md: str


class BodyResult(BaseModel):
    """[7] 본문 생성 결과. 2번째 섹션부터."""

    body_sections: list[BodySection] = Field(default_factory=list)
