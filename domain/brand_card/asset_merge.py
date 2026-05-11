"""브랜드 자산 + 캠페인 입력 병합 — SPEC §6 입력 우선순위 5단계.

LLM 프롬프트에 주입할 통합 컨텍스트를 만든다. plan_generator 가 호출.

우선순위 (높음 → 낮음):
1. 사용자가 직접 입력한 메시지 (`brief_text`)
2. 카드 생성 시 첨부한 파일 (`attached_source_ids`)
3. 브랜드 공통 자산 (`brand_message_sources` source_type=brand_common)
4. 홈페이지/기존 문서 추출 정보 (campaign/keyword_specific/reference)
5. LLM 보완 생성

본 모듈은 1~4 만 구성. 5는 plan_generator 가 LLM 호출 시 자동.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from domain.brand_card.model import (
    BrandMediaAsset,
    BrandMessageSource,
    CardCampaignInput,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MergedAssets:
    """LLM 프롬프트에 주입할 통합 메시지 자산.

    각 우선순위별 텍스트 청크를 명시적으로 분리해 plan_generator 가
    프롬프트에 우선순위 헤더와 함께 삽입한다.
    """

    user_brief: str = ""  # 우선순위 1
    attached_files: list[str] = field(default_factory=list)  # 우선순위 2
    brand_common: list[str] = field(default_factory=list)  # 우선순위 3
    other_references: list[str] = field(default_factory=list)  # 우선순위 4
    required_phrases: list[str] = field(default_factory=list)
    forbidden_phrases: list[str] = field(default_factory=list)
    # 2026-05-11 — 브랜드 미디어 라이브러리 자산 목록. plan_generator 가 LLM
    # 에게 image_asset_id 를 어떤 값으로 채워야 할지 컨텍스트로 전달.
    # 누락 시 LLM 이 환각 ID 를 만들어 renderer 매칭 실패 (image placeholder).
    media_assets: list[BrandMediaAsset] = field(default_factory=list)


def merge_assets(
    *,
    campaign_input: CardCampaignInput | None,
    attached_sources: list[BrandMessageSource],
    brand_sources: list[BrandMessageSource],
    media_assets: list[BrandMediaAsset] | None = None,
) -> MergedAssets:
    """SPEC §6 우선순위로 자산 병합.

    Args:
        campaign_input: 키워드별 캠페인 입력 (선택). brief_text + required/forbidden.
        attached_sources: campaign_input.attached_source_ids 로 fetch 한 소스.
        brand_sources: 브랜드 전체 메시지 소스 목록 (storage.list_message_sources).
        media_assets: 브랜드 미디어 자산 목록 (선택, 신규). LLM 이 image_asset_id
            를 채울 때 참조할 정답 enum.

    Returns: 우선순위별 텍스트가 분리된 MergedAssets.
    """
    user_brief = (campaign_input.brief_text or "").strip() if campaign_input else ""
    required = list(campaign_input.required_phrases) if campaign_input else []
    forbidden = list(campaign_input.forbidden_phrases) if campaign_input else []

    attached_texts = [_source_text(s) for s in attached_sources]
    attached_texts = [t for t in attached_texts if t]  # 빈 텍스트 제외

    brand_common, other_refs = _partition_by_source_type(brand_sources, attached_sources)

    return MergedAssets(
        user_brief=user_brief,
        attached_files=attached_texts,
        brand_common=brand_common,
        other_references=other_refs,
        required_phrases=required,
        forbidden_phrases=forbidden,
        media_assets=list(media_assets) if media_assets else [],
    )


def _partition_by_source_type(
    brand_sources: list[BrandMessageSource],
    attached_sources: list[BrandMessageSource],
) -> tuple[list[str], list[str]]:
    """brand_common 우선 / 그 외 (campaign/keyword_specific/reference) 분리.

    attached_sources 는 우선순위 2 로 별도 처리되므로 본 분리에서 제외.
    """
    attached_ids = {s.id for s in attached_sources if s.id}
    brand_common: list[str] = []
    other: list[str] = []
    for src in brand_sources:
        if src.id in attached_ids:
            continue  # 이미 attached_files 로 노출됨
        text = _source_text(src)
        if not text:
            continue
        if src.source_type == "brand_common":
            brand_common.append(text)
        else:
            other.append(text)
    return brand_common, other


def _source_text(src: BrandMessageSource) -> str:
    """source 의 content_text 와 file_name 을 합쳐 LLM 컨텍스트로 사용 가능한 형태로."""
    body = (src.content_text or "").strip()
    if not body:
        return ""
    label = src.file_name or src.source_type
    return f"[{label}]\n{body}"
