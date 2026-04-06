"""생성 도메인 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field

# 브랜디드 카드 타입 정의 (텍스트 흐름 내 3종 + disclaimer)
# pain/cause/solution/trust 내용은 SEO 텍스트에 흡수됨
BRANDED_CARD_TYPES = (
    "intro",
    "transition",
    "cta",
    "disclaimer",
)


class CardContent(BaseModel):
    """단일 브랜디드 카드의 LLM 생성 콘텐츠."""

    card_type: str  # BRANDED_CARD_TYPES 중 하나
    title: str = ""
    subtitle: str = ""
    body_text: str = ""
    items: list[str] = Field(default_factory=list)  # 리스트 항목 (솔루션 단계 등)
    badge_text: str = ""  # 통계 뱃지, 라벨 등


class CardLayoutSet(BaseModel):
    """카드 타입별 레이아웃 변이명."""

    intro: str = ""  # quote_greeting, magazine_header 등
    transition: str = ""  # hashtag_keycopy, big_question 등
    cta: str = ""  # service_grid, single_action 등


class VariationConfig(BaseModel):
    """6개 층위 변이 조합."""

    structure: str = ""  # 구조 템플릿 이름
    intro: str = ""  # 도입부 스타일
    subtitle_style: str = ""  # 소제목 스타일
    expression_tone: str = ""  # 표현 톤
    image_placement: str = ""  # 이미지 배치 패턴
    card_layouts: CardLayoutSet = Field(default_factory=CardLayoutSet)
    newsletter_theme: str = ""  # 뉴스레터 테마 이름


class DesignCard(BaseModel):
    """디자인 카드 (HTML → PNG 렌더링 대상)."""

    card_type: str  # BRANDED_CARD_TYPES 중 하나
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
    """생성된 콘텐츠."""

    id: str = ""
    pattern_card_id: str = ""
    client_profile_id: str = ""
    keyword: str = ""

    seo_text: str = ""  # 마크다운 블로그 원고
    title: str = ""  # 생성된 제목
    variation_config: VariationConfig = Field(default_factory=VariationConfig)
    design_cards: list[DesignCard] = Field(default_factory=list)
    card_positions: dict[str, int] = Field(default_factory=dict)  # 카드 삽입 위치
    ai_image_prompts: list[str] = Field(default_factory=list)
    generated_images: list[GeneratedImage] = Field(default_factory=list)

    compliance_status: str = "pending"  # pending / pass / fix / reject
