"""브랜드 카드 도메인 Pydantic 모델.

SPEC-BRAND-CARD.md v2.1 §11 (모델) + §9 (스키마) 구현.
신규 brand_cards 컬럼(strategy/expression_level/status/source_summary/
compliance_report/reuse_group_id) 과 1:1 매핑.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ── 열거형 ─────────────────────────────────────────────


class CardStrategy(StrEnum):
    """다양화 전략 — §5 P1 4종."""

    TRUST_FIRST = "trust_first"
    EMPATHY_FIRST = "empathy_first"
    PROCESS_FIRST = "process_first"
    LOCAL_FIRST = "local_first"


class ExpressionLevel(StrEnum):
    """표현 강도 — §7 3단계."""

    SAFE = "safe"
    BALANCED = "balanced"
    HOOKING = "hooking"


class BrandCardStatus(StrEnum):
    """카드 라이프사이클 — §9 status 전이도."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CardType(StrEnum):
    """P1 카드 6종 — §4."""

    HERO = "hero"
    PROBLEM = "problem"
    SOLUTION = "solution"
    DIFFERENTIATOR = "differentiator"
    PROCESS = "process"
    TRUST_CLOSING = "trust_closing"


class MessageSourceType(StrEnum):
    """brand_message_sources.source_type — §9. forbidden_phrases 는 제거 (M5).

    card_campaign_inputs.forbidden_phrases 가 단일 출처.
    """

    BRAND_COMMON = "brand_common"
    CAMPAIGN = "campaign"
    KEYWORD_SPECIFIC = "keyword_specific"
    REFERENCE = "reference"


# ── 기본 모델 ─────────────────────────────────────────


class BrandProfile(BaseModel):
    """brand_profiles 1행 — 브랜드 기본 정보."""

    id: str | None = None
    name: str
    slug: str
    homepage_url: str
    locale: str = "ko-KR"
    current_asset_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BrandMediaAsset(BaseModel):
    """brand_media_assets 1행 — 실사 사진 라이브러리."""

    id: str | None = None
    brand_id: str
    type: str  # doctor | facility | equipment | cert | other
    file_path: str
    file_sha256: str
    title: str | None = None
    description: str | None = None
    orientation: str | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class BrandMessageSource(BaseModel):
    """브랜드 메시지 파일 1건 (txt/docx/pdf/html 추출 후 보관)."""

    id: str | None = None
    brand_id: str
    source_type: str  # MessageSourceType 값
    file_name: str | None = None
    file_path: str | None = None
    content_text: str | None = None
    content_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class CardCampaignInput(BaseModel):
    """키워드별 카드 생성 시 입력 — §6 카드 생성 입력."""

    id: str | None = None
    brand_id: str
    keyword: str
    goal: str | None = None
    expression_level: str = "balanced"  # ExpressionLevel
    required_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    brief_text: str | None = None
    attached_source_ids: list[str] = Field(default_factory=list)
    reference_image_paths: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


# ── 카드 기획안 모델 (LLM tool_use 출력) ─────────────────


class CardBlock(BaseModel):
    """카드 1장의 콘텐츠 블록 — §11 CardBlock.

    image_asset_id: brand_media_assets 참조 (실사 사진).
    ai_image_prompt: AI 생성 이미지용 프롬프트 (배경/일러스트 등).
    둘 중 하나만 채워야 한다 — 의료진/시설/장비는 항상 image_asset_id.
    """

    card_type: str  # CardType 값
    headline: str
    subcopy: str | None = None
    bullets: list[str] = Field(default_factory=list)
    image_asset_id: str | None = None
    ai_image_prompt: str | None = None
    recommended_position: str  # after_intro | after_problem | mid | before_closing


class BrandCardPlan(BaseModel):
    """카드 기획안 — [B5] generate_card_plan 출력.

    사용자 승인 게이트 ([B6]) 전까지 status=draft 로 저장.
    렌더 비용(Gemini/Playwright) 발생 X.
    """

    id: str | None = None
    brand_id: str
    keyword: str
    strategy: str  # CardStrategy
    expression_level: str  # ExpressionLevel
    template_id: str
    angle: str
    blocks: list[CardBlock]
    required_phrases_used: list[str] = Field(default_factory=list)
    forbidden_phrases_avoided: list[str] = Field(default_factory=list)
    source_summary: dict[str, Any] = Field(default_factory=dict)
    reuse_group_id: str | None = None
    status: str = "draft"  # BrandCardStatus
    created_at: datetime | None = None


# ── 렌더 결과 모델 (Playwright 출력) ────────────────────


class RenderedBrandCard(BaseModel):
    """렌더 완료된 카드 1건 — [B11] render_card_set 결과."""

    id: str | None = None
    brand_id: str
    keyword: str
    strategy: str  # CardStrategy
    expression_level: str  # ExpressionLevel
    template_id: str
    variant_idx: int = Field(ge=1)
    png_path: Path
    width_px: int = Field(ge=1)
    height_px: int = Field(ge=1)
    compliance_report: dict[str, Any] = Field(default_factory=dict)
    reuse_group_id: str | None = None
    status: str = "published"  # BrandCardStatus
    created_at: datetime | None = None


class RenderedCardSet(BaseModel):
    """한 번의 render_card_set 결과 묶음 — reuse_group_id 로 묶인 N개 카드."""

    reuse_group_id: str
    brand_id: str
    keyword: str
    cards: list[RenderedBrandCard]
    manifest_path: Path  # cards-manifest.json


# ── 예외 ──────────────────────────────────────────────


class BrandCardError(Exception):
    """브랜드 카드 도메인 베이스 예외."""


class TextOverflowError(BrandCardError):
    """렌더 시 텍스트 overflow 검출 — §13 M6 메커니즘."""


class ReuseGuardError(BrandCardError):
    """30일 윈도우 헤드라인 재사용 등 차단 룰 위반.

    사용자 override 옵션이 있을 때는 catch 후 무시 가능.
    """


class StatusTransitionError(BrandCardError):
    """허용되지 않은 status 전이 시도 — SPEC §9.3 위반."""


# ── 상태 전이도 (SPEC §9.3) ─────────────────────────────

_VALID_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    BrandCardStatus.DRAFT.value: frozenset(
        {
            BrandCardStatus.REVIEWED.value,
            BrandCardStatus.APPROVED.value,
            BrandCardStatus.REJECTED.value,
        },
    ),
    BrandCardStatus.REVIEWED.value: frozenset(
        {
            BrandCardStatus.APPROVED.value,
            BrandCardStatus.REJECTED.value,
        },
    ),
    BrandCardStatus.APPROVED.value: frozenset(
        {
            BrandCardStatus.PUBLISHED.value,
            BrandCardStatus.REJECTED.value,
        },
    ),
    BrandCardStatus.PUBLISHED.value: frozenset({BrandCardStatus.ARCHIVED.value}),
    BrandCardStatus.REJECTED.value: frozenset(),
    BrandCardStatus.ARCHIVED.value: frozenset(),
}


def assert_status_transition(current: str, target: str) -> None:
    """SPEC §9.3 전이도 검증. 위반 시 StatusTransitionError.

    동일 상태 전이는 idempotent 로 허용 (재호출 안전).
    """
    if current == target:
        return
    allowed = _VALID_STATUS_TRANSITIONS.get(current)
    if allowed is None:
        raise StatusTransitionError(
            f"알 수 없는 현재 status: {current!r}",
        )
    if target not in allowed:
        raise StatusTransitionError(
            f"허용되지 않은 전이: {current!r} → {target!r}. "
            f"허용된 다음 상태: {sorted(allowed) or '(종결 상태)'}",
        )
