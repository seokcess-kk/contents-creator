"""생성 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field

# 브랜드 이미지 카드 타입 (5종 기본 + disclaimer)
BRAND_CARD_TYPES = (
    "greeting",  # 인사/소개
    "empathy",  # 고민 공감
    "service",  # 서비스 소개
    "trust",  # 신뢰/실적
    "cta",  # 연락처/행동유도
)


class CardContent(BaseModel):
    """단일 브랜드 카드의 LLM 생성 콘텐츠."""

    card_type: str
    title: str = ""
    subtitle: str = ""
    body_text: str = ""
    items: list[str] = Field(default_factory=list)
    badge_text: str = ""


class CardLayoutSet(BaseModel):
    """카드 타입별 레이아웃 변이명."""

    greeting: str = ""
    empathy: str = ""
    service: str = ""
    trust: str = ""
    cta: str = ""


class VariationConfig(BaseModel):
    """7개 층위 변이 조합."""

    structure: str = ""
    intro: str = ""
    subtitle_style: str = ""
    expression_tone: str = ""
    image_placement: str = ""
    card_layouts: CardLayoutSet = Field(default_factory=CardLayoutSet)
    newsletter_theme: str = ""


class DesignCard(BaseModel):
    """디자인 카드 (HTML → PNG 렌더링 대상)."""

    card_type: str
    html: str = ""
    title: str = ""
    subtitle: str = ""
    color_primary: str = "#333333"
    color_background: str = "#ffffff"
    color_accent: str = "#4a90d9"


class GeneratedImage(BaseModel):
    """AI 생성 이미지."""

    prompt: str = ""
    image_bytes: bytes = b""
    success: bool = True
    error: str = ""


class GeneratedContent(BaseModel):
    """생성된 콘텐츠 (브랜드 이미지 + SEO 원고 분리)."""

    id: str = ""
    pattern_card_id: str = ""
    client_profile_id: str = ""
    keyword: str = ""

    seo_text: str = ""  # SEO 원고 (카드 마커 없음, 순수 텍스트)
    title: str = ""
    variation_config: VariationConfig = Field(default_factory=VariationConfig)
    brand_cards: list[DesignCard] = Field(default_factory=list)  # 브랜드 이미지 카드
    generated_images: list[GeneratedImage] = Field(default_factory=list)  # SEO용 AI 이미지

    compliance_status: str = "pending"  # pending / pass / fix / reject
