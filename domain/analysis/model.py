"""분석 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectionInfo(BaseModel):
    """섹션 구조 정보."""

    total_chars: int = 0
    total_paragraphs: int = 0
    subtitle_count: int = 0
    subtitles: list[str] = Field(default_factory=list)
    section_ratio: str = ""  # "도입20-본론60-결론20"
    image_count: int = 0
    image_positions: list[int] = Field(default_factory=list)  # 문단 번호
    cta_positions: list[int] = Field(default_factory=list)
    cta_texts: list[str] = Field(default_factory=list)
    naver_elements: dict[str, int] = Field(
        default_factory=lambda: {"map": 0, "divider": 0, "blockquote": 0}
    )


class TitlePattern(BaseModel):
    """제목 패턴."""

    type: str  # 질문형/숫자형/감정형/방법론형/리스트형
    count: int = 0
    examples: list[str] = Field(default_factory=list)
    weight: float = 0.0


class HookPattern(BaseModel):
    """도입부 훅 패턴."""

    type: str  # 공감형/통계형/질문형/스토리형/시즌형
    count: int = 0
    examples: list[str] = Field(default_factory=list)


class L1Analysis(BaseModel):
    """L1 구조 분석 결과 (코드 기반, LLM 불필요)."""

    post_count: int = 0
    avg_char_count: float = 0.0
    avg_paragraph_count: float = 0.0
    avg_subtitle_count: float = 0.0
    section_pattern: str = ""
    image_positions: list[float] = Field(default_factory=list)  # 평균 위치 비율
    avg_image_count: float = 0.0
    cta_patterns: list[str] = Field(default_factory=list)
    naver_elements: dict[str, float] = Field(default_factory=dict)
    per_post: list[SectionInfo] = Field(default_factory=list)


class L2Analysis(BaseModel):
    """L2 카피/메시지 분석 결과 (LLM 기반)."""

    title_patterns: list[TitlePattern] = Field(default_factory=list)
    hook_patterns: list[HookPattern] = Field(default_factory=list)
    keyword_placement: dict[str, list[str]] = Field(default_factory=dict)
    tone_distribution: dict[str, int] = Field(default_factory=dict)
    persuasion_structures: list[str] = Field(default_factory=list)
    related_keywords: list[str] = Field(default_factory=list)
    lsi_keywords: list[str] = Field(default_factory=list)


class VisualAnalysis(BaseModel):
    """비주얼 분석 결과 (DOM + VLM)."""

    dominant_palette: list[str] = Field(default_factory=list)  # hex 색상
    background_colors: list[str] = Field(default_factory=list)
    font_colors: list[str] = Field(default_factory=list)
    mood: str = ""  # 따뜻한/차가운/전문적/밝은/차분한
    layout_pattern: str = ""
    image_type_distribution: dict[str, float] = Field(default_factory=dict)
    avg_image_count: float = 0.0
    industry_trend: str = ""


class TextAnalysisResult(BaseModel):
    """텍스트 분석 통합 결과."""

    keyword: str
    post_count: int = 0
    l1: L1Analysis = Field(default_factory=L1Analysis)
    l2: L2Analysis = Field(default_factory=L2Analysis)


class PatternCard(BaseModel):
    """패턴 카드. 키워드별 상위글 분석 결과의 정형화 데이터."""

    id: str = ""
    keyword: str = ""

    text_pattern: dict = Field(default_factory=dict)
    # char_range, subtitle_count, title_formulas, hook_types,
    # persuasion_structure, required_keywords, related_keywords, section_order

    visual_pattern: dict = Field(default_factory=dict)
    # color_palette, layout_pattern, image_types, image_count_range, mood

    constraints: dict = Field(default_factory=lambda: {"skeleton": [], "free": []})

    confidence: str = "high"  # high / low
    source_post_count: int = 0
