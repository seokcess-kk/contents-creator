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
    BrandMediaAsset,
    BrandMessageSource,
    BrandProfile,
    CardBlock,
    CardCampaignInput,
)

logger = logging.getLogger(__name__)

_SOURCES_TABLE = "brand_message_sources"
_INPUTS_TABLE = "card_campaign_inputs"
_CARDS_TABLE = "brand_cards"
_PROFILES_TABLE = "brand_profiles"
_MEDIA_TABLE = "brand_media_assets"


# ── brand_profiles ──────────────────────────────────────────


def list_brands(*, limit: int = 100) -> list[BrandProfile]:
    """등록된 모든 브랜드 (created_at desc)."""
    client = get_client()
    result = (
        client.table(_PROFILES_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_profile(cast("dict[str, Any]", r)) for r in (result.data or [])]


def get_brand(brand_id: str) -> BrandProfile | None:
    client = get_client()
    result = client.table(_PROFILES_TABLE).select("*").eq("id", brand_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_profile(cast("dict[str, Any]", rows[0]))


def get_brand_by_slug(slug: str) -> BrandProfile | None:
    """slug 로 브랜드 조회 — UNIQUE 제약 사전 확인용."""
    client = get_client()
    result = client.table(_PROFILES_TABLE).select("*").eq("slug", slug).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_profile(cast("dict[str, Any]", rows[0]))


def insert_brand(profile: BrandProfile) -> BrandProfile:
    """신규 브랜드 등록. id 는 DB 가 채움. slug UNIQUE 충돌은 BrandSlugConflictError."""
    client = get_client()
    payload: dict[str, Any] = {
        "name": profile.name,
        "slug": profile.slug,
        "homepage_url": profile.homepage_url,
        "locale": profile.locale,
        "current_asset_version": profile.current_asset_version,
    }
    try:
        result = client.table(_PROFILES_TABLE).insert(payload).execute()
    except Exception as exc:  # noqa: BLE001 — Supabase 예외 형태가 모듈 버전마다 상이
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            raise BrandSlugConflictError(f"slug 중복: {profile.slug!r}") from exc
        raise
    rows = result.data or []
    if not rows:
        raise RuntimeError("brand_profiles insert: no row returned")
    return _row_to_profile(cast("dict[str, Any]", rows[0]))


class BrandSlugConflictError(Exception):
    """brand_profiles.slug UNIQUE 충돌."""


# ── brand_media_assets ──────────────────────────────────────


def list_media_assets(brand_id: str, *, limit: int = 200) -> list[BrandMediaAsset]:
    client = get_client()
    result = (
        client.table(_MEDIA_TABLE)
        .select("*")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_media(cast("dict[str, Any]", r)) for r in (result.data or [])]


def get_media_asset(asset_id: str) -> BrandMediaAsset | None:
    client = get_client()
    result = client.table(_MEDIA_TABLE).select("*").eq("id", asset_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_media(cast("dict[str, Any]", rows[0]))


def insert_media_asset(asset: BrandMediaAsset) -> BrandMediaAsset:
    client = get_client()
    payload: dict[str, Any] = {
        "brand_id": asset.brand_id,
        "type": asset.type,
        "file_sha256": asset.file_sha256,
        "title": asset.title,
        "description": asset.description,
        "orientation": asset.orientation,
        "width": asset.width,
        "height": asset.height,
        "tags": list(asset.tags),
    }
    if asset.file_path is not None:
        payload["file_path"] = asset.file_path
    if asset.storage_path is not None:
        payload["storage_path"] = asset.storage_path
    if asset.file_size_bytes is not None:
        payload["file_size_bytes"] = asset.file_size_bytes
    result = client.table(_MEDIA_TABLE).insert(payload).execute()
    rows = result.data or []
    if not rows:
        raise RuntimeError("brand_media_assets insert: no row returned")
    return _row_to_media(cast("dict[str, Any]", rows[0]))


def delete_media_asset(asset_id: str) -> bool:
    """미디어 자산 hard delete. 행이 삭제되면 True, 미존재면 False.

    plan.image_asset_id 가 dangling 되면 UI 가 graceful 처리 (자산 미존재 시
    `(deleted)` 표시). cascade 정책 결정 사항: Hard delete + UI graceful.
    """
    client = get_client()
    result = client.table(_MEDIA_TABLE).delete().eq("id", asset_id).execute()
    return bool(result.data)


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


def get_message_source(source_id: str) -> BrandMessageSource | None:
    """단건 조회 — 라우터의 존재/소속 검증용."""
    client = get_client()
    result = client.table(_SOURCES_TABLE).select("*").eq("id", source_id).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return _row_to_source(cast("dict[str, Any]", rows[0]))


def delete_message_source(source_id: str) -> bool:
    """소스 hard delete. 행이 삭제되면 True, 미존재면 False.

    Supabase Storage 객체 / 디스크 파일 정리는 호출자 책임 (라우터가
    storage_signed.remove_object 추가 호출). DB 와 storage 의 정합성은
    best-effort — DB 삭제 성공이 storage 삭제 실패보다 우선이라 orphan
    storage 객체가 잠시 남을 수 있으나, sha256 + brand_id 기반 storage_path
    가 멱등이라 재업로드 시 덮어쓰기 가능.
    """
    client = get_client()
    result = client.table(_SOURCES_TABLE).delete().eq("id", source_id).execute()
    return bool(result.data)


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


def update_card_blocks(
    card_id: str,
    blocks: list[CardBlock],
    *,
    new_status: str | None = None,
) -> BrandCardPlan | None:
    """카드 blocks 부분 수정 (문구·image_asset_id·ai_image_prompt 등).

    blocks 는 `source_summary["blocks"]` 안에 jsonb 로 저장되어 있어 기존
    summary 를 보존하며 blocks 만 교체. new_status 가 주어지면 함께 업데이트
    (예: draft → reviewed 전이).
    """
    current = get_card_plan(card_id)
    if current is None:
        return None
    new_summary = {
        **current.source_summary,
        "blocks": [_block_to_dict(b) for b in blocks],
        "required_phrases_used": current.required_phrases_used,
        "forbidden_phrases_avoided": current.forbidden_phrases_avoided,
    }
    payload: dict[str, Any] = {"source_summary": new_summary}
    if new_status is not None:
        payload["status"] = new_status
    client = get_client()
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


def list_plan_groups_for_brand(brand_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """브랜드 상세 페이지용 — reuse_group_id 별 묶음 메타.

    2026-05-11 — 카드 기획안 묶음 진입점을 브랜드 상세 페이지에서 회복하기
    위한 데이터 소스. brand_id 의 모든 plan 을 가져온 뒤 reuse_group_id 로
    묶어 [{reuse_group_id, keyword, latest_created_at, plan_count,
    status_counts: {draft: N, approved: N, ...}}, ...] 로 반환. created_at
    desc 정렬 (최근 묶음이 위).
    """
    client = get_client()
    result = (
        client.table(_CARDS_TABLE)
        .select("reuse_group_id, keyword, status, created_at")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit * 10)  # 묶음당 plan 평균 3개 가정, 충분한 raw row 확보
        .execute()
    )
    rows = cast("list[dict[str, Any]]", result.data or [])

    groups: dict[str, dict[str, Any]] = {}
    for r in rows:
        gid = r.get("reuse_group_id")
        if not gid:
            continue
        existing = groups.get(gid)
        if existing is None:
            groups[gid] = {
                "reuse_group_id": gid,
                "keyword": r.get("keyword") or "",
                "latest_created_at": r.get("created_at"),
                "plan_count": 1,
                "status_counts": {r.get("status") or "draft": 1},
            }
            continue
        existing["plan_count"] += 1
        st = r.get("status") or "draft"
        existing["status_counts"][st] = existing["status_counts"].get(st, 0) + 1
        # 최신 created_at 유지 (raw 가 desc 라 첫 등장이 최신)
    # 정렬: latest_created_at desc
    ordered = sorted(
        groups.values(),
        key=lambda g: g.get("latest_created_at") or "",
        reverse=True,
    )
    return ordered[:limit]


# ── 직렬화 헬퍼 ─────────────────────────────────────────────


def _row_to_profile(row: dict[str, Any]) -> BrandProfile:
    return BrandProfile(
        id=row.get("id"),
        name=row["name"],
        slug=row["slug"],
        homepage_url=row["homepage_url"],
        locale=row.get("locale") or "ko-KR",
        current_asset_version=row.get("current_asset_version") or 1,
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


def _row_to_media(row: dict[str, Any]) -> BrandMediaAsset:
    return BrandMediaAsset(
        id=row.get("id"),
        brand_id=row["brand_id"],
        type=row["type"],
        file_path=row.get("file_path"),
        storage_path=row.get("storage_path"),
        file_sha256=row["file_sha256"],
        file_size_bytes=row.get("file_size_bytes"),
        title=row.get("title"),
        description=row.get("description"),
        orientation=row.get("orientation"),
        width=row.get("width"),
        height=row.get("height"),
        tags=list(row.get("tags") or []),
        created_at=_parse_dt(row.get("created_at")),
    )


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
    if s.storage_path is not None:
        payload["storage_path"] = s.storage_path
    if s.file_sha256 is not None:
        payload["file_sha256"] = s.file_sha256
    if s.file_size_bytes is not None:
        payload["file_size_bytes"] = s.file_size_bytes
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
        storage_path=row.get("storage_path"),
        file_sha256=row.get("file_sha256"),
        file_size_bytes=row.get("file_size_bytes"),
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
