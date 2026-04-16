"""Analysis 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [3][4a][4b] 의 각 추출 결과 타입.
Phase 2 에서는 먼저 [3] 물리 분석 (`PhysicalAnalysis`) 만 정의하고,
[4a][4b] 모델은 해당 단계 착수 시 추가한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

# SPEC §3 [3] element_sequence 타입 구분
ElementType = Literal["title", "heading", "paragraph", "image", "list", "quote", "table"]


class ElementSequenceItem(BaseModel):
    """본문의 요소 시퀀스 1건.

    필드는 타입별로 선택적 — title/heading 은 `text` + (heading 일 때) `level`,
    paragraph 는 `chars` + `keyword_count`, image 는 `position` 만 유의미.
    """

    type: ElementType
    text: str | None = None
    chars: int | None = None
    level: int | None = Field(default=None, ge=1, le=6)
    keyword_count: int | None = None
    has_keyword: bool | None = None
    position: int | None = None


class RelatedKeywordStats(BaseModel):
    """연관 키워드 1개의 등장 통계."""

    count: int = Field(ge=0)
    sections: list[int] = Field(default_factory=list)


class KeywordAnalysis(BaseModel):
    """[3] 키워드 배치·밀도 분석."""

    main_keyword: str
    first_appearance_sentence: int = Field(ge=0)  # 0 = 등장 없음
    total_count: int = Field(ge=0)
    density: float = Field(ge=0.0)
    subtitle_keyword_ratio: float = Field(ge=0.0, le=1.0)
    title_keyword_position: Literal["front", "middle", "back", "absent"]
    related_keywords: dict[str, RelatedKeywordStats] = Field(default_factory=dict)


class DiaPlus(BaseModel):
    """DIA+ 요소 7종 감지 결과 (SPEC §3 [3])."""

    tables: int = Field(ge=0)
    lists: int = Field(ge=0)
    blockquotes: int = Field(ge=0)
    bold_count: int = Field(ge=0)
    separators: int = Field(ge=0)
    qa_sections: bool
    statistics_data: bool


class ParagraphStats(BaseModel):
    """문단·문장 통계."""

    avg_paragraph_chars: float = Field(ge=0.0)
    avg_sentence_chars: float = Field(ge=0.0)
    short_paragraph_ratio: float = Field(ge=0.0, le=1.0)


class SectionRatios(BaseModel):
    """도입/본문/결론 글자수 비율. 합은 근사적으로 1.0."""

    intro: float = Field(ge=0.0, le=1.0)
    body: float = Field(ge=0.0, le=1.0)
    conclusion: float = Field(ge=0.0, le=1.0)


class PhysicalAnalysis(BaseModel):
    """[3] 단일 블로그 글의 물리적 구조 추출 결과.

    LLM 불필요. DOM 파싱(BeautifulSoup) + 정규식만으로 도출.
    """

    url: HttpUrl
    title: str
    total_chars: int = Field(ge=0)
    total_paragraphs: int = Field(ge=0)
    subtitle_count: int = Field(ge=0)
    element_sequence: list[ElementSequenceItem] = Field(default_factory=list)
    keyword_analysis: KeywordAnalysis
    dia_plus: DiaPlus
    paragraph_stats: ParagraphStats
    section_ratios: SectionRatios
    tags: list[str] = Field(default_factory=list)
    tag_count: int = Field(ge=0, default=0)
