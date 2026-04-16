"""Analysis 도메인 Pydantic 모델.

SPEC-SEO-TEXT.md §3 [3][4a][4b] 의 각 추출 결과 타입.
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


# ── [4a] 의미 분석 모델 ──

SectionRole = Literal[
    "도입/공감",
    "정보제공",
    "원인분석",
    "방법제시",
    "비교분석",
    "사례/후기",
    "전문가의견",
    "FAQ",
    "요약",
    "검색유도",
    "기타",
]

SECTION_ROLES: list[str] = list(SectionRole.__args__)  # type: ignore[attr-defined]

DepthLevel = Literal["표면적", "중간", "전문적"]
TitlePattern = Literal["질문형", "숫자형", "감정형", "방법론형"]
HookType = Literal["공감형", "통계형", "질문형", "스토리형"]


class SectionSemantic(BaseModel):
    """[4a] 섹션 하나의 의미 분석."""

    section: int = Field(ge=1)
    role: SectionRole
    summary: str
    depth: DepthLevel


class TargetReader(BaseModel):
    """타겟 독자 프로필 (SPEC §3 [4a] + [5] 공통)."""

    concerns: list[str] = Field(default_factory=list)
    search_intent: str = ""
    expertise_level: str = ""


class SemanticAnalysis(BaseModel):
    """[4a] 단일 블로그의 의미적 구조 분석 결과."""

    url: HttpUrl
    semantic_structure: list[SectionSemantic] = Field(default_factory=list)
    title_pattern: TitlePattern
    hook_type: HookType
    target_reader: TargetReader
    depth_assessment: str = ""


# ── [4b] 소구 포인트 모델 ──

PromotionalLevel = Literal["low", "medium", "high"]
SubjectType = Literal["업체 주체", "정보 주체", "혼재"]


class AppealPoint(BaseModel):
    """[4b] 소구 포인트 1건."""

    point: str
    section: int = Field(ge=1)
    promotional_level: PromotionalLevel


class AppealAnalysis(BaseModel):
    """[4b] 단일 블로그의 소구 포인트 + 홍보성 레벨 분석 결과."""

    url: HttpUrl
    appeal_points: list[AppealPoint] = Field(default_factory=list)
    subject_type: SubjectType
    overall_promotional_level: PromotionalLevel
