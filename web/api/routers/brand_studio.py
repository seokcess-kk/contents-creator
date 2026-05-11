"""브랜드 스튜디오 API 라우터 — Phase 4.1·4.2·후속 백엔드.

SPEC-BRAND-CARD §14 UX 의 백엔드 진입점. 17 라우트 + X-API-Key 일괄 인증.

흐름:
1. GET /brands → 브랜드 목록
2. POST /brands → 신규 브랜드 등록 (slug UNIQUE)
3. GET /brands/{id}/sources → 메시지 소스 목록
4. POST /brands/{id}/sources → 파일 업로드 (multipart) → source_parser → DB 저장
5. POST /brands/{id}/campaign-inputs → 캠페인 입력 저장 (키워드 + 표현강도 + 제외문구 등)
6. POST /brands/{id}/plans → orchestrator.generate_card_plan 호출 (LLM 동기, 1~10s)
7. GET /plans/{group_id} → 기획안 묶음 조회
8. POST /plans/{plan_id}/approve | /reject → 상태 전이
   PATCH /plans/{plan_id} → blocks 수정 (draft/reviewed 만, 자동 reviewed 전이)
9. POST /plans/{group_id}/render → JobManager 통합 비동기 렌더
10. GET /cards/{group_id} → 결과 보관함 (8 항목)
11. GET /cards/{group_id}/files/{filename} → 렌더된 PNG 다운로드 (path traversal 방어)
12. GET /brands/{id}/media-assets → 미디어 자산 목록 (실사 사진 라이브러리)
13. POST /brands/{id}/media-assets → 이미지 업로드 (multipart, Pillow 검증)
14. GET /media-assets/{id} → 자산 메타 단건
15. DELETE /media-assets/{id} → hard delete (plan.image_asset_id dangling UI graceful)
16. GET /media-assets/{id}/file → 이미지 파일 (img src 미리보기·다운로드)

도메인 격리: 본 라우터는 `application/brand_card_orchestrator` 와 `domain/brand_card/storage`
만 호출한다. domain 함수를 직접 호출하지 않는다 (오케스트레이션 일관성).
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from application import brand_card_orchestrator as orch
from application.brand_card_orchestrator import PlanEditNotAllowedError
from config.settings import settings
from domain.brand_card import source_parser, storage, storage_signed
from domain.brand_card.model import (
    BrandCardError,
    BrandCardPlan,
    BrandMediaAsset,
    BrandMessageSource,
    BrandProfile,
    CardBlock,
    CardCampaignInput,
    StatusTransitionError,
)
from domain.brand_card.storage import BrandSlugConflictError
from domain.brand_card.storage_signed import StorageSignedError
from web.api.auth import require_api_key
from web.api.schemas import JobSubmitResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/brand-studio",
    tags=["brand-studio"],
    dependencies=[Depends(require_api_key)],
)

_ASSET_ROOT = Path("output") / "brand_assets"


# ── 요청/응답 스키마 ─────────────────────────────────────────


class CampaignInputRequest(BaseModel):
    """카드 생성 입력 (SPEC §14 카드 생성 화면 9 필드 중 첨부 파일 제외 8 필드)."""

    keyword: str
    goal: str | None = None
    expression_level: str = "balanced"
    required_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    brief_text: str | None = None
    attached_source_ids: list[str] = Field(default_factory=list)
    reference_image_paths: list[str] = Field(default_factory=list)


class GeneratePlansRequest(BaseModel):
    """카드 기획안 생성 요청."""

    keyword: str
    expression_level: str = "balanced"
    strategy_count: int = 3
    allow_reuse_override: bool = False


class RenderRequest(BaseModel):
    """렌더 시작 요청 — JobManager 비동기."""

    brand_name: str | None = None
    brand_url: str | None = None


class CardArchiveItem(BaseModel):
    """결과 보관함 1행 — SPEC §14 결과 화면 8 항목."""

    plan_id: str | None
    template_id: str
    strategy: str
    expression_level: str
    status: str
    headline: str
    blocks: list[dict[str, Any]]
    compliance_report: dict[str, Any]
    recommended_position: str
    reuse_group_id: str | None
    png_paths: list[str] = Field(default_factory=list)


class CardArchiveResponse(BaseModel):
    """묶음 헤더 + N 카드."""

    reuse_group_id: str
    items: list[CardArchiveItem]


# ── 1-2. brands ─────────────────────────────────────────────


@router.get("/brands")
def list_brands() -> list[BrandProfile]:
    return storage.list_brands()


class BrandRegisterRequest(BaseModel):
    """신규 브랜드 등록 입력 — slug 는 UNIQUE."""

    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    homepage_url: str = Field(min_length=1)
    locale: str = Field(default="ko-KR", max_length=16)


@router.post("/brands", status_code=201)
def register_brand(req: BrandRegisterRequest) -> BrandProfile:
    """신규 브랜드 등록. slug 중복 시 409, 형식 위반 시 422 (Pydantic)."""
    if storage.get_brand_by_slug(req.slug) is not None:
        raise HTTPException(status_code=409, detail=f"slug 중복: {req.slug!r}")
    profile = BrandProfile(
        name=req.name,
        slug=req.slug,
        homepage_url=req.homepage_url,
        locale=req.locale,
    )
    try:
        return storage.insert_brand(profile)
    except BrandSlugConflictError as exc:
        # 동시성 race — get_brand_by_slug 이후 다른 요청이 먼저 INSERT
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ── 2-3. brand sources ──────────────────────────────────────


@router.get("/brands/{brand_id}/sources")
def list_sources(brand_id: str) -> list[BrandMessageSource]:
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return storage.list_message_sources(brand_id)


@router.post("/brands/{brand_id}/sources", status_code=201)
async def upload_source(
    brand_id: str,
    file: UploadFile = File(...),  # noqa: B008
    source_type: str = Form("brand_common"),
) -> BrandMessageSource:
    """[DEPRECATED] multipart 업로드 → source_parser → DB 저장.

    Vercel 함수 페이로드 4.5MB 한계로 큰 파일은 실패한다. 신규 흐름은
    `/sources/init` + Supabase Storage PUT + `/sources/confirm`. 본 엔드포인트는
    CLI/기존 클라이언트 호환을 위해 유지하되, 호출 시 deprecation 경고를 남긴다.

    저장 경로: output/brand_assets/{brand_id}/sources/{sha256}{suffix}
    """
    logger.warning(
        "brand_sources.multipart_upload_deprecated brand_id=%s — use /sources/init+confirm",
        brand_id,
    )
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")

    file_name = file.filename or "upload.bin"
    safe_name = _sanitize_filename(file_name)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    digest = hashlib.sha256(raw).hexdigest()
    suffix = Path(safe_name).suffix.lower()
    save_dir = _ASSET_ROOT / brand_id / "sources"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{digest}{suffix}"
    save_path.write_bytes(raw)

    try:
        text = source_parser.parse_source_file(save_path)
    except source_parser.UnsupportedSourceError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except source_parser.SourceParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = BrandMessageSource(
        brand_id=brand_id,
        source_type=source_type,
        file_name=safe_name,
        file_path=str(save_path),
        file_sha256=digest,
        file_size_bytes=len(raw),
        content_text=text,
    )
    return storage.insert_message_source(record)


# ── 2-3b. brand sources presigned upload (Vercel 4.5MB 우회) ──


_VALID_SOURCE_TYPES = {"brand_common", "campaign", "keyword_specific", "reference"}


class SourceUploadInitRequest(BaseModel):
    """프론트가 업로드 의도를 알리고 signed PUT URL 을 발급받는 요청."""

    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    source_type: str = Field(default="brand_common")


class SourceUploadInitResponse(BaseModel):
    """signed PUT URL + storage_path. 브라우저는 upload_url 로 PUT, 이후
    confirm 호출 시 storage_path 를 그대로 echo 한다.
    """

    upload_url: str
    upload_token: str | None
    storage_path: str
    expires_at: str


class SourceUploadConfirmRequest(BaseModel):
    """업로드 완료 후 백엔드에 다운로드 + 파싱 + DB INSERT 를 트리거.

    storage_path 는 init 에서 발급한 패턴과 정확히 일치해야 한다 (path traversal
    방어). sha256 은 확정 단계에서 다운로드 본문과 재검증해 변조를 차단한다.
    """

    storage_path: str = Field(min_length=1)
    source_type: str = Field(default="brand_common")
    file_name: str = Field(min_length=1, max_length=255)
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


@router.post("/brands/{brand_id}/sources/init", status_code=201)
def init_source_upload(brand_id: str, req: SourceUploadInitRequest) -> SourceUploadInitResponse:
    """[1/2] signed PUT URL 발급. 5분 TTL. 검증 후 브라우저가 직접 PUT 한다."""
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    _validate_source_type(req.source_type)

    if req.file_size > settings.brand_sources_max_bytes:
        max_mb = settings.brand_sources_max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"파일이 너무 큽니다. 최대 {max_mb}MB",
        )

    safe_name = _sanitize_filename(req.file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in settings.brand_sources_allowed_suffixes:
        raise HTTPException(
            status_code=415,
            detail=(
                f"지원되지 않는 형식: {suffix!r} "
                f"(허용: {list(settings.brand_sources_allowed_suffixes)})"
            ),
        )

    try:
        signed = storage_signed.create_upload_url(brand_id, req.sha256, suffix)
    except StorageSignedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SourceUploadInitResponse(
        upload_url=signed.upload_url,
        upload_token=signed.upload_token,
        storage_path=signed.storage_path,
        expires_at=signed.expires_at.isoformat(),
    )


@router.post("/brands/{brand_id}/sources/confirm", status_code=201)
def confirm_source_upload(brand_id: str, req: SourceUploadConfirmRequest) -> BrandMessageSource:
    """[2/2] 업로드 완료 알림 → Storage 다운로드 + 파싱 + DB INSERT."""
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    _validate_source_type(req.source_type)

    safe_name = _sanitize_filename(req.file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in settings.brand_sources_allowed_suffixes:
        raise HTTPException(status_code=415, detail=f"지원되지 않는 형식: {suffix!r}")

    expected_path = storage_signed.build_storage_path(brand_id, req.sha256, suffix)
    if req.storage_path != expected_path:
        raise HTTPException(
            status_code=400, detail="storage_path 가 init 발급 패턴과 일치하지 않습니다"
        )

    try:
        raw = storage_signed.download_object(req.storage_path)
    except StorageSignedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != req.sha256:
        # 변조 감지 — 스토리지에서 객체 제거 후 거부
        storage_signed.remove_object(req.storage_path)
        raise HTTPException(status_code=422, detail="sha256 불일치 (변조 또는 중간 손상)")

    try:
        text = source_parser.parse_source_bytes(suffix, raw)
    except source_parser.UnsupportedSourceError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except source_parser.SourceParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = BrandMessageSource(
        brand_id=brand_id,
        source_type=req.source_type,
        file_name=safe_name,
        storage_path=req.storage_path,
        file_sha256=req.sha256,
        file_size_bytes=len(raw),
        content_text=text,
    )
    return storage.insert_message_source(record)


def _validate_source_type(source_type: str) -> None:
    if source_type not in _VALID_SOURCE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"source_type 는 {sorted(_VALID_SOURCE_TYPES)} 중 하나여야 합니다",
        )


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str) -> Response:
    """2026-05-11 — source hard delete. DB + Supabase Storage 객체 모두 정리.

    media-asset 삭제와 동일 패턴. 디스크 파일 정리는 best-effort — DB 행만
    제거되면 운영상 정합성은 깨지지 않는다 (frontend 가 더 이상 노출 안 함).
    plan.attached_source_ids 가 dangling 될 수 있으나 asset_merge 가
    `get_message_sources_by_ids` 호출 시 자동 누락 처리.
    """
    source = storage.get_message_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    storage.delete_message_source(source_id)
    if source.storage_path:
        storage_signed.remove_object(source.storage_path)
    if source.file_path:
        try:
            Path(source.file_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("source.disk_unlink_failed path=%s", source.file_path)
    return Response(status_code=204)


# ── 4. campaign-inputs ──────────────────────────────────────


@router.post("/brands/{brand_id}/campaign-inputs", status_code=201)
def save_campaign_input(brand_id: str, req: CampaignInputRequest) -> CardCampaignInput:
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    record = CardCampaignInput(
        brand_id=brand_id,
        keyword=req.keyword,
        goal=req.goal,
        expression_level=req.expression_level,
        required_phrases=list(req.required_phrases),
        forbidden_phrases=list(req.forbidden_phrases),
        brief_text=req.brief_text,
        attached_source_ids=list(req.attached_source_ids),
        reference_image_paths=list(req.reference_image_paths),
    )
    return storage.insert_campaign_input(record)


# ── 5. POST /plans (generate) ───────────────────────────────


@router.post("/brands/{brand_id}/plans", status_code=202)
def generate_plans(brand_id: str, req: GeneratePlansRequest) -> JobSubmitResponse:
    """[B5] LLM 비동기 호출. JobManager 경유.

    2026-05-11 fix — strategy_count × (plan LLM + compliance LLM) 동기 처리가
    30~60s 에 달해 Vercel rewrites proxy timeout (502) 을 일으키던 문제를
    background 처리로 회피. 즉시 job_id 반환 후 GET /api/jobs/{job_id} 로
    polling. 완료 시 result.reuse_group_id 로 검토 화면 이동.
    """
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    if not 1 <= req.strategy_count <= 4:
        raise HTTPException(
            status_code=400, detail=f"strategy_count 는 1~4: {req.strategy_count}"
        )

    from web.api.main import job_manager

    job = job_manager.submit_brand_card_plan_generate(
        {
            "brand_id": brand_id,
            "keyword": req.keyword,
            "expression_level": req.expression_level,
            "strategy_count": req.strategy_count,
            "allow_reuse_override": req.allow_reuse_override,
        },
    )
    return JobSubmitResponse(job_id=job.id)


# ── 6. GET /plans/{group_id} ────────────────────────────────


@router.get("/plans/{group_id}")
def get_plans(group_id: str) -> list[BrandCardPlan]:
    plans = storage.list_cards_by_reuse_group(group_id)
    if not plans:
        raise HTTPException(status_code=404, detail="No plans for reuse_group")
    return plans


@router.get("/brands/{brand_id}/plan-groups")
def list_plan_groups(brand_id: str) -> dict[str, Any]:
    """2026-05-11 — 브랜드 상세 페이지의 기획안 묶음 진입점.

    brand_id 의 모든 plan 을 reuse_group_id 별 묶음 메타로 집계해 반환.
    그룹마다 keyword / 최근 생성 시각 / plan 수 / status 분포 포함.
    클라이언트가 그룹 카드를 클릭하면 /plans/{group_id} 검토 페이지로 이동.
    """
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    groups = storage.list_plan_groups_for_brand(brand_id)
    return {"brand_id": brand_id, "count": len(groups), "items": groups}


# ── 7. approve / reject / edit ──────────────────────────────


@router.post("/plans/{plan_id}/approve")
def approve(plan_id: str) -> BrandCardPlan:
    return _transition(plan_id, "approve")


@router.post("/plans/{plan_id}/reject")
def reject(plan_id: str) -> BrandCardPlan:
    return _transition(plan_id, "reject")


class PlanEditRequest(BaseModel):
    """plan blocks 부분 수정 — 문구/사진/AI prompt.

    blocks 배열 통째 교체. status: draft/reviewed 만 허용 (그 외 409).
    draft → 자동 reviewed 전이.
    """

    blocks: list[CardBlock]


@router.patch("/plans/{plan_id}")
def edit_plan(plan_id: str, req: PlanEditRequest) -> BrandCardPlan:
    """plan blocks 수정 — draft/reviewed 만 허용. 미존재 → 404, 잘못된 status → 409."""
    if not req.blocks:
        raise HTTPException(status_code=422, detail="blocks 배열은 비어있을 수 없습니다")
    try:
        result = orch.edit_plan(plan_id, blocks=req.blocks)
    except PlanEditNotAllowedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


def _transition(plan_id: str, action: str) -> BrandCardPlan:
    fn = orch.approve_plan if action == "approve" else orch.reject_plan
    try:
        result = fn(plan_id)
    except StatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


# ── 8. POST /plans/{group_id}/render — JobManager 비동기 ───


@router.post("/plans/{group_id}/render", status_code=202)
def submit_render(group_id: str, req: RenderRequest) -> JobSubmitResponse:
    plans = storage.list_cards_by_reuse_group(group_id)
    if not plans:
        raise HTTPException(status_code=404, detail="No plans for reuse_group")
    approved = [p for p in plans if p.status == "approved"]
    if not approved:
        raise HTTPException(
            status_code=409,
            detail="No approved plans — call approve first",
        )

    from web.api.main import job_manager

    job = job_manager.submit_brand_card_render(
        {
            "reuse_group_id": group_id,
            "brand_name": req.brand_name,
            "brand_url": req.brand_url,
            "output_root": str(_resolve_output_root()),
        },
    )
    return JobSubmitResponse(job_id=job.id)


def _resolve_output_root() -> Path:
    """settings.output_dir 가 있으면 그 하위, 없으면 기본 output/brand_cards."""
    base = getattr(settings, "output_dir", None)
    return Path(base) / "brand_cards" if base else Path("output") / "brand_cards"


# ── 9. GET /cards/{group_id} — 결과 보관함 ──────────────────


@router.get("/cards/{group_id}")
def list_cards(group_id: str) -> CardArchiveResponse:
    """8 항목 표시: SPEC §14 결과 화면.

    렌더 완료 여부와 무관하게 plan 메시지·compliance_report 는 항상 표시.
    PNG 가 디스크에 있으면 png_paths 채움.
    """
    plans = storage.list_cards_by_reuse_group(group_id)
    if not plans:
        raise HTTPException(status_code=404, detail="No cards for reuse_group")

    base = _resolve_output_root() / group_id / "cards"
    items = [_plan_to_archive_item(p, base) for p in plans]
    return CardArchiveResponse(reuse_group_id=group_id, items=items)


def _plan_to_archive_item(plan: BrandCardPlan, cards_dir: Path) -> CardArchiveItem:
    headline = plan.blocks[0].headline if plan.blocks else ""
    recommended = plan.blocks[0].recommended_position if plan.blocks else ""
    compliance = plan.source_summary.get("compliance_report", {}) if plan.source_summary else {}
    blocks_payload = [
        {
            "card_type": b.card_type,
            "headline": b.headline,
            "subcopy": b.subcopy,
            "bullets": list(b.bullets),
            "image_asset_id": b.image_asset_id,
            "ai_image_prompt": b.ai_image_prompt,
            "recommended_position": b.recommended_position,
        }
        for b in plan.blocks
    ]
    pngs: list[str] = []
    if cards_dir.exists():
        pngs = sorted(
            str(p) for p in cards_dir.glob(f"card-{plan.template_id}-{plan.strategy}-*.png")
        )
    return CardArchiveItem(
        plan_id=plan.id,
        template_id=plan.template_id,
        strategy=plan.strategy,
        expression_level=plan.expression_level,
        status=plan.status,
        headline=headline,
        blocks=blocks_payload,
        compliance_report=compliance,
        recommended_position=recommended,
        reuse_group_id=plan.reuse_group_id,
        png_paths=pngs,
    )


# ── 10. GET /cards/{group_id}/files/{filename} — PNG 다운로드 ──


@router.get("/cards/{group_id}/files/{filename}")
def download_card_png(group_id: str, filename: str) -> FileResponse:
    """렌더된 PNG 파일 다운로드. path traversal 방어 + 404.

    저장 위치는 `_resolve_output_root() / group_id / "cards" / filename`.
    `cards/` 디렉터리 외부 접근은 group_id·filename 검증으로 차단한다.
    """
    if not _is_safe_path_segment(group_id) or not _is_safe_path_segment(filename):
        raise HTTPException(status_code=400, detail="Invalid path segment")
    cards_dir = _resolve_output_root() / group_id / "cards"
    target = cards_dir / filename
    try:
        resolved = target.resolve()
        cards_root = cards_dir.resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc
    if not str(resolved).startswith(str(cards_root)):
        raise HTTPException(status_code=400, detail="Path escape detected")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(resolved),
        media_type="image/png",
        filename=filename,
    )


def _is_safe_path_segment(segment: str) -> bool:
    """`..` / 슬래시 / 백슬래시 / 빈 문자열 차단. 한 경로 컴포넌트만 허용."""
    if not segment or segment in (".", ".."):
        return False
    if "/" in segment or "\\" in segment or "\x00" in segment:
        return False
    return Path(segment).name == segment


# ── 12-16. media-assets (미디어 자산 라이브러리) ───────────


_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@router.get("/brands/{brand_id}/media-assets")
def list_media_assets(brand_id: str) -> list[BrandMediaAsset]:
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return storage.list_media_assets(brand_id)


@router.post("/brands/{brand_id}/media-assets", status_code=201)
async def upload_media_asset(
    brand_id: str,
    file: UploadFile = File(...),  # noqa: B008
    asset_type: str = Form("other"),
    title: str | None = Form(None),
    description: str | None = Form(None),
) -> BrandMediaAsset:
    """[DEPRECATED] 이미지 multipart 업로드 → Pillow 검증 → 로컬 디스크.

    Vercel 함수 페이로드 4.5MB 한계로 큰 이미지는 실패. 신규 흐름은
    `/media-assets/init` + Supabase Storage PUT + `/media-assets/confirm`.
    CLI/기존 클라이언트 호환을 위해 유지하되 호출 시 deprecation 경고.
    """
    logger.warning(
        "media_asset.multipart_upload_deprecated brand_id=%s — use /media-assets/init+confirm",
        brand_id,
    )
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")

    file_name = file.filename or "upload.bin"
    safe_name = _sanitize_filename(file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"지원되지 않는 이미지 형식: {suffix!r} (허용: jpg/jpeg/png/webp)",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    width, height = _validate_and_size(raw)

    digest = hashlib.sha256(raw).hexdigest()
    save_dir = _ASSET_ROOT / brand_id / "media"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{digest}{suffix}"
    save_path.write_bytes(raw)

    record = BrandMediaAsset(
        brand_id=brand_id,
        type=asset_type,
        file_path=str(save_path),
        file_sha256=digest,
        file_size_bytes=len(raw),
        title=title,
        description=description,
        orientation=_orientation_label(width, height),
        width=width,
        height=height,
    )
    return storage.insert_media_asset(record)


# ── 12b. media-assets presigned upload (Vercel 4.5MB 우회) ──


_VALID_ASSET_TYPES = {"doctor", "facility", "equipment", "cert", "other"}


class MediaUploadInitRequest(BaseModel):
    """미디어 자산 업로드 init — 이미지 메타만 전송."""

    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    asset_type: str = Field(default="other")


class MediaUploadInitResponse(BaseModel):
    upload_url: str
    upload_token: str | None
    storage_path: str
    expires_at: str


class MediaUploadConfirmRequest(BaseModel):
    """업로드 완료 알림 → Storage download → Pillow 검증 → INSERT."""

    storage_path: str = Field(min_length=1)
    asset_type: str = Field(default="other")
    file_name: str = Field(min_length=1, max_length=255)
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    title: str | None = None
    description: str | None = None


@router.post("/brands/{brand_id}/media-assets/init", status_code=201)
def init_media_upload(brand_id: str, req: MediaUploadInitRequest) -> MediaUploadInitResponse:
    """[1/2] 이미지용 signed PUT URL 발급. brand-media 버킷."""
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    _validate_asset_type(req.asset_type)

    if req.file_size > settings.brand_media_max_bytes:
        max_mb = settings.brand_media_max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"이미지가 너무 큽니다. 최대 {max_mb}MB")

    safe_name = _sanitize_filename(req.file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in settings.brand_media_allowed_suffixes:
        raise HTTPException(
            status_code=415,
            detail=(
                f"지원되지 않는 이미지 형식: {suffix!r} "
                f"(허용: {list(settings.brand_media_allowed_suffixes)})"
            ),
        )

    try:
        signed = storage_signed.create_upload_url(
            brand_id,
            req.sha256,
            suffix,
            bucket=settings.brand_media_bucket,
            prefix="media",
        )
    except StorageSignedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return MediaUploadInitResponse(
        upload_url=signed.upload_url,
        upload_token=signed.upload_token,
        storage_path=signed.storage_path,
        expires_at=signed.expires_at.isoformat(),
    )


@router.post("/brands/{brand_id}/media-assets/confirm", status_code=201)
def confirm_media_upload(brand_id: str, req: MediaUploadConfirmRequest) -> BrandMediaAsset:
    """[2/2] download → sha256 재검증 → Pillow 검증 → INSERT."""
    if storage.get_brand(brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    _validate_asset_type(req.asset_type)

    safe_name = _sanitize_filename(req.file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in settings.brand_media_allowed_suffixes:
        raise HTTPException(status_code=415, detail=f"지원되지 않는 이미지 형식: {suffix!r}")

    expected_path = storage_signed.build_storage_path(brand_id, req.sha256, suffix, prefix="media")
    if req.storage_path != expected_path:
        raise HTTPException(
            status_code=400, detail="storage_path 가 init 발급 패턴과 일치하지 않습니다"
        )

    try:
        raw = storage_signed.download_object(req.storage_path, bucket=settings.brand_media_bucket)
    except StorageSignedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != req.sha256:
        storage_signed.remove_object(req.storage_path, bucket=settings.brand_media_bucket)
        raise HTTPException(status_code=422, detail="sha256 불일치 (변조 또는 중간 손상)")

    width, height = _validate_and_size(raw)

    record = BrandMediaAsset(
        brand_id=brand_id,
        type=req.asset_type,
        storage_path=req.storage_path,
        file_sha256=req.sha256,
        file_size_bytes=len(raw),
        title=req.title,
        description=req.description,
        orientation=_orientation_label(width, height),
        width=width,
        height=height,
    )
    return storage.insert_media_asset(record)


def _validate_asset_type(asset_type: str) -> None:
    if asset_type not in _VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"asset_type 는 {sorted(_VALID_ASSET_TYPES)} 중 하나여야 합니다",
        )


@router.get("/media-assets/{asset_id}")
def get_media_asset(asset_id: str) -> BrandMediaAsset:
    asset = storage.get_media_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/media-assets/{asset_id}", status_code=204)
def delete_media_asset(asset_id: str) -> Response:
    """Hard delete. 디스크 파일 / Supabase 객체 모두 best-effort 삭제. 미존재 → 404."""
    asset = storage.get_media_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    storage.delete_media_asset(asset_id)
    if asset.storage_path:
        # presigned 업로드 자산 — Supabase Storage 에서 객체 제거
        storage_signed.remove_object(asset.storage_path, bucket=settings.brand_media_bucket)
    if asset.file_path:
        try:
            Path(asset.file_path).unlink(missing_ok=True)
        except OSError:
            # 디스크 삭제 실패는 데이터 정합성에 영향 없음 (DB 행은 이미 사라짐)
            logger.warning("media_asset.disk_unlink_failed path=%s", asset.file_path)
    return Response(status_code=204)


@router.get("/media-assets/{asset_id}/file")
def download_media_asset(asset_id: str) -> Response:
    """이미지 파일 응답 — img src 또는 다운로드.

    storage_path 가 있으면 Supabase signed URL 로 302 redirect (브라우저가 자동
    follow). 로컬 file_path 만 있으면 FileResponse.
    """
    asset = storage.get_media_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.storage_path:
        try:
            url = storage_signed.create_download_url(
                asset.storage_path, bucket=settings.brand_media_bucket
            )
        except StorageSignedError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse(url=url, status_code=302)

    if asset.file_path:
        path = Path(asset.file_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Asset file missing on disk")
        suffix = path.suffix.lower().lstrip(".")
        media_type = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }.get(suffix, "application/octet-stream")
        return FileResponse(path=str(path), media_type=media_type, filename=path.name)

    raise HTTPException(status_code=404, detail="Asset has no file or storage path")


def _validate_and_size(raw: bytes) -> tuple[int, int]:
    """Pillow 로 이미지 디코드 + 크기 추출. 디코드 실패 시 422."""
    from io import BytesIO

    try:
        from PIL import Image, UnidentifiedImageError

        with Image.open(BytesIO(raw)) as img:
            img.verify()
        with Image.open(BytesIO(raw)) as img:
            return int(img.width), int(img.height)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=422,
            detail="이미지 디코드 실패 (손상된 파일이거나 지원되지 않는 형식)",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — Pillow 다양한 예외
        raise HTTPException(status_code=422, detail=f"이미지 검증 실패: {exc}") from exc


def _orientation_label(width: int, height: int) -> str:
    """가로/세로/정사각 라벨 — 카드 templates 가 적합한 자산 선택용."""
    if width > height * 1.1:
        return "landscape"
    if height > width * 1.1:
        return "portrait"
    return "square"


# ── 헬퍼 ────────────────────────────────────────────────────


# 2026-05-11 — 한글 등 유니코드 파일명 보존. 저장은 sha256 기반이라 file_name
# 은 DB text 표시용. path traversal 방지를 위해 경로 분리자(/, \, NUL)·제어
# 문자만 제거. 기존 regex `[^A-Za-z0-9._-]` 는 한글까지 _ 로 치환해 미리보기
# 깨짐 유발 → ASCII whitelist 대신 blacklist 로 전환.
_UNSAFE_FILENAME_CHARS = re.compile(r"[\x00-\x1f\x7f/\\]")
_MAX_FILENAME_LEN = 255


def _sanitize_filename(name: str) -> str:
    """경로 분리자·제어 문자 제거. 표시용 이름 (저장은 sha256 기반).

    유니코드 문자(한글/일본어/중국어/이모지)는 그대로 보존. Path(name).name
    이 디렉토리 부분 잘라내고, 추가로 백슬래시·NUL·DEL·C0 control 만 _ 로
    치환. 결과가 비면 "upload.bin" 폴백. 길이는 DB / OS 안전 마진 255 자로 컷.
    """
    base = Path(name).name
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", base).strip()
    if cleaned in ("", ".", ".."):
        return "upload.bin"
    return cleaned[:_MAX_FILENAME_LEN]
