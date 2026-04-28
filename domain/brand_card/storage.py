"""브랜드 카드 도메인 Supabase CRUD.

3 테이블 — brand_message_sources / card_campaign_inputs / brand_cards.

기존 brand_cards 컬럼(angle/png_meta/compliance_passed/compliance_iterations) 은
deprecate. 신규 컬럼(strategy/expression_level/status/source_summary/
compliance_report/reuse_group_id) 만 read/write.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from config.supabase import get_client
from domain.brand_card.model import (
    BrandCardPlan,
    BrandMessageSource,
    CardBlock,
    CardCampaignInput,
)

logger = logging.getLogger(__name__)

_SOURCES_TABLE = "brand_message_sources"
_INPUTS_TABLE = "card_campaign_inputs"
_CARDS_TABLE = "brand_cards"


# ── brand_message_sources ───────────────────────────────────


def insert_message_source(source: BrandMessageSource) -> BrandMessageSource:
    """브랜드 메시지 파일 1건 저장. id 는 DB 가 채움."""
    client = get_client()
    payload = _source_to_payload(source)
    result = client.table(_SOURCES_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("brand_message_sources insert: no row returned")
    return _row_to_source(cast("dict[str, Any]", rows[0]))


def list_message_sources(brand_id: str, limit: int = 100) -> list[BrandMessageSource]:
    """브랜드 메시지 소스 (created_at desc)."""
    client = get_client()
    result = (
        client.table(_SOURCES_TABLE)
        .select("*")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_source(cast("dict[str, Any]", r)) for r in (result.data or [])]


def get_message_sources_by_ids(ids: list[str]) -> list[BrandMessageSource]:
    """attached_source_ids 로 참조된 소스 일괄 조회."""
    if not ids:
        return []
    client = get_client()
    result = client.table(_SOURCES_TABLE).select("*").in_("id", ids).execute()
    return [_row_to_source(cast("dict[str, Any]", r)) for r in (result.data or [])]


# ── card_campaign_inputs ────────────────────────────────────


def insert_campaign_input(ci: CardCampaignInput) -> CardCampaignInput:
    """캠페인 입력 1건 저장."""
    client = get_client()
    payload = _input_to_payload(ci)
    result = client.table(_INPUTS_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("card_campaign_inputs insert: no row returned")
    return _row_to_input(cast("dict[str, Any]", rows[0]))


def get_latest_campaign_input(brand_id: str, keyword: str) -> CardCampaignInput | None:
    """가장 최근 입력 1건 (없으면 None)."""
    client = get_client()
    result = (
        client.table(_INPUTS_TABLE)
        .select("*")
        .eq("brand_id", brand_id)
        .eq("keyword", keyword)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return _row_to_input(cast("dict[str, Any]", rows[0]))


# ── brand_cards (plan + rendered) ───────────────────────────


def insert_card_plan(plan: BrandCardPlan) -> BrandCardPlan:
    """카드 기획안 저장. status=draft 로 자동 초기화 (모델 default)."""
    client = get_client()
    payload = _plan_to_payload(plan)
    result = client.table(_CARDS_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("brand_cards insert: no row returned")
    return _row_to_plan(cast("dict[str, Any]", rows[0]))


def get_card_plan(plan_id: str) -> BrandCardPlan | None:
    client = get_client()
    result = client.table(_CARDS_TABLE).select("*").eq("id", plan_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_plan(cast("dict[str, Any]", rows[0]))


def update_card_status(
    card_id: str,
    status: str,
    *,
    compliance_report: dict[str, Any] | None = None,
) -> BrandCardPlan | None:
    """status 전이 + 선택적 compliance_report 업데이트."""
    client = get_client()
    payload: dict[str, Any] = {"status": status}
    if compliance_report is not None:
        payload["compliance_report"] = compliance_report
    result = client.table(_CARDS_TABLE).update(payload).eq("id", card_id).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_plan(cast("dict[str, Any]", rows[0]))


def list_recent_cards_for_brand(
    brand_id: str,
    *,
    days: int = 30,
    limit: int = 200,
) -> list[BrandCardPlan]:
    """reuse_guard 용 — 최근 N일 brand 카드 (created_at desc)."""
    from datetime import UTC, timedelta

    client = get_client()
    cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()
    result = (
        client.table(_CARDS_TABLE)
        .select("*")
        .eq("brand_id", brand_id)
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_plan(cast("dict[str, Any]", r)) for r in (result.data or [])]


def list_cards_by_reuse_group(reuse_group_id: str) -> list[BrandCardPlan]:
    """한 묶음(reuse_group_id) 의 모든 카드 — 보관함 표시용."""
    client = get_client()
    result = (
        client.table(_CARDS_TABLE)
        .select("*")
        .eq("reuse_group_id", reuse_group_id)
        .order("variant_idx")
        .execute()
    )
    return [_row_to_plan(cast("dict[str, Any]", r)) for r in (result.data or [])]


# ── 직렬화 헬퍼 ─────────────────────────────────────────────


def _source_to_payload(s: BrandMessageSource) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "brand_id": s.brand_id,
        "source_type": s.source_type,
        "content_summary": s.content_summary,
    }
    if s.file_name is not None:
        payload["file_name"] = s.file_name
    if s.file_path is not None:
        payload["file_path"] = s.file_path
    if s.content_text is not None:
        payload["content_text"] = s.content_text
    return payload


def _row_to_source(row: dict[str, Any]) -> BrandMessageSource:
    return BrandMessageSource(
        id=row.get("id"),
        brand_id=row["brand_id"],
        source_type=row["source_type"],
        file_name=row.get("file_name"),
        file_path=row.get("file_path"),
        content_text=row.get("content_text"),
        content_summary=row.get("content_summary") or {},
        created_at=_parse_dt(row.get("created_at")),
    )


def _input_to_payload(ci: CardCampaignInput) -> dict[str, Any]:
    return {
        "brand_id": ci.brand_id,
        "keyword": ci.keyword,
        "goal": ci.goal,
        "expression_level": ci.expression_level,
        "required_phrases": list(ci.required_phrases),
        "forbidden_phrases": list(ci.forbidden_phrases),
        "brief_text": ci.brief_text,
        "attached_source_ids": list(ci.attached_source_ids),
        "reference_image_paths": list(ci.reference_image_paths),
    }


def _row_to_input(row: dict[str, Any]) -> CardCampaignInput:
    return CardCampaignInput(
        id=row.get("id"),
        brand_id=row["brand_id"],
        keyword=row["keyword"],
        goal=row.get("goal"),
        expression_level=row.get("expression_level") or "balanced",
        required_phrases=list(row.get("required_phrases") or []),
        forbidden_phrases=list(row.get("forbidden_phrases") or []),
        brief_text=row.get("brief_text"),
        attached_source_ids=list(row.get("attached_source_ids") or []),
        reference_image_paths=list(row.get("reference_image_paths") or []),
        created_at=_parse_dt(row.get("created_at")),
    )


def _plan_to_payload(p: BrandCardPlan) -> dict[str, Any]:
    """BrandCardPlan → brand_cards row.

    blocks 는 source_summary 안에 직렬화 (별도 컬럼 미존재). variant_idx 는
    plan 단계에선 0 default — render 시 RenderedBrandCard 가 1-based 부여.
    """
    return {
        "brand_id": p.brand_id,
        "brand_asset_version": 1,  # P1 단일 자산 버전 가정. 추후 다중 버전 시 갱신
        "keyword": p.keyword,
        "variant_idx": 0,  # plan 단계 기본. render 시 갱신
        "template_id": p.template_id,
        "angle": p.angle,  # deprecate 컬럼 — 호환성 유지
        "png_path": "",  # plan 단계는 render 전 — 빈 문자열
        "strategy": p.strategy,
        "expression_level": p.expression_level,
        "status": p.status,
        "source_summary": {
            **p.source_summary,
            "blocks": [_block_to_dict(b) for b in p.blocks],
            "required_phrases_used": p.required_phrases_used,
            "forbidden_phrases_avoided": p.forbidden_phrases_avoided,
        },
        "compliance_report": {},
        "reuse_group_id": p.reuse_group_id,
    }


def _row_to_plan(row: dict[str, Any]) -> BrandCardPlan:
    summary = row.get("source_summary") or {}
    blocks = [_dict_to_block(b) for b in summary.get("blocks", [])]
    return BrandCardPlan(
        id=row.get("id"),
        brand_id=row["brand_id"],
        keyword=row["keyword"],
        strategy=row.get("strategy") or "trust_first",
        expression_level=row.get("expression_level") or "balanced",
        template_id=row["template_id"],
        angle=row.get("angle") or "",
        blocks=blocks,
        required_phrases_used=list(summary.get("required_phrases_used") or []),
        forbidden_phrases_avoided=list(summary.get("forbidden_phrases_avoided") or []),
        source_summary={
            k: v
            for k, v in summary.items()
            if k not in ("blocks", "required_phrases_used", "forbidden_phrases_avoided")
        },
        reuse_group_id=row.get("reuse_group_id"),
        status=row.get("status") or "draft",
        created_at=_parse_dt(row.get("created_at")),
    )


def _block_to_dict(b: CardBlock) -> dict[str, Any]:
    return {
        "card_type": b.card_type,
        "headline": b.headline,
        "subcopy": b.subcopy,
        "bullets": list(b.bullets),
        "image_asset_id": b.image_asset_id,
        "ai_image_prompt": b.ai_image_prompt,
        "recommended_position": b.recommended_position,
    }


def _dict_to_block(d: dict[str, Any]) -> CardBlock:
    return CardBlock(
        card_type=d["card_type"],
        headline=d["headline"],
        subcopy=d.get("subcopy"),
        bullets=list(d.get("bullets") or []),
        image_asset_id=d.get("image_asset_id"),
        ai_image_prompt=d.get("ai_image_prompt"),
        recommended_position=d["recommended_position"],
    )


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


# RenderedBrandCard 저장은 Phase 2 renderer 단계에서 추가.
# 현재는 plan(status=draft) → status=approved → render 시 별도 함수로.
