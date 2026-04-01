"""생성 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VariationConfig(BaseModel):
    """5개 층위 변이 조합."""

    structure: str = ""  # 구조 템플릿 이름
    intro: str = ""  # 도입부 스타일
    subtitle_style: str = ""  # 소제목 스타일
    expression_tone: str = ""  # 표현 톤
    image_placement: str = ""  # 이미지 배치 패턴


class DesignCard(BaseModel):
    """디자인 카드 (HTML → PNG 렌더링 대상)."""

    card_type: str  # header / cta
    html: str = ""
    title: str = ""
    subtitle: str = ""
    color_primary: str = "#333333"
    color_background: str = "#ffffff"
    color_accent: str = "#4a90d9"


class GeneratedContent(BaseModel):
    """생성된 콘텐츠."""

    id: str = ""
    pattern_card_id: str = ""
    client_profile_id: str = ""
    keyword: str = ""

    seo_text: str = ""  # 마크다운 블로그 원고
    title: str = ""  # 생성된 제목
    variation_config: VariationConfig = Field(default_factory=VariationConfig)
    design_cards: list[DesignCard] = Field(default_factory=list)
    ai_image_prompts: list[str] = Field(default_factory=list)

    compliance_status: str = "pending"  # pending / pass / fix / reject
