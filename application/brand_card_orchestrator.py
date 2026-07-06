"""브랜드 카드 application 오케스트레이터.

도메인 격리: domain/brand_card 는 SEO 도메인을 import 하지 않는다.
본 파일이 brand_card 모듈들을 합성해 호출하고, AI 이미지 생성 시
domain/image_generation 을 재사용한다 (D2).

SPEC-BRAND-CARD §15 진입점 2개로 분리 (D3):
- generate_card_plan: [B1]~[B5] — Gemini/Playwright 호출 0, status=draft
- render_card_set: [B7]~[B12] — plan.status=approved 일 때만 진행 (Phase 2.5)
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from domain.brand_card import (
    asset_merge,
    image_prefetch,
    manifest,
    plan_generator,
    renderer,
    reuse_guard,
    storage,
)
from domain.brand_card import (
    compliance as bc_compliance,
)
from domain.brand_card.model import (
    BrandCardError,
    BrandCardPlan,
    BrandCardStatus,
    CardBlock,
    ExpressionLevel,
    RenderedBrandCard,
    RenderedCardSet,
    assert_status_transition,
)
from domain.compliance.model import ComplianceReport

logger = logging.getLogger(__name__)


# 키워드별 추천 전략 매핑 (SPEC §5).
# 키워드 종류에 따라 plan_generator 가 사용할 strategy 우선순위 결정.
_STRATEGY_HINTS: dict[str, list[str]] = {
    "default": ["trust_first", "empathy_first", "process_first", "local_first"],
}


# 전략별 추천 템플릿 (Phase 2 에서 4 템플릿 등록 후 다시 매핑).
_STRATEGY_TEMPLATE: dict[str, str] = {
    "trust_first": "clinic_trust",
    "empathy_first": "diet_empathy",
    "process_first": "process_guide",
    "local_first": "local_info",
}


def generate_card_plan(
    *,
    brand_id: str,
    keyword: str,
    expression_level: str = ExpressionLevel.BALANCED.value,
    strategy_count: int = 3,
    allow_reuse_override: bool = False,
) -> list[BrandCardPlan]:
    """[B1]~[B5] 카드 기획안 생성. status=draft 로 묶음 저장.

    여러 strategy 로 N개 variant 를 한 묶음(reuse_group_id)으로 생성.
    LLM 호출만 발생 (Gemini/Playwright 없음). 사용자 승인 게이트 통과 후
    `render_card_set(reuse_group_id)` 가 [B7]~[B12] 진행.

    Args:
        brand_id: 등록된 브랜드 ID.
        keyword: 카드를 만들 키워드.
        expression_level: safe / balanced / hooking.
        strategy_count: 1~4. SPEC §5 4 전략 중 상위 N개 선택.
        allow_reuse_override: True 시 reuse_guard 차단 룰 약화.

    Returns: 생성된 plan N개 (모두 status=draft, 같은 reuse_group_id).
    """
    if not 1 <= strategy_count <= 4:
        raise ValueError(f"strategy_count 는 1~4: {strategy_count}")

    # 1) 자산 fetch — 캠페인 입력 + 첨부 + 브랜드 공통 + 미디어 라이브러리.
    # 2026-05-11 — media_assets 추가. plan_generator 가 LLM 에게 자산 enum 을
    # 알려서 환각 image_asset_id 생성 차단 (이전엔 모든 카드 이미지가 빈
    # placeholder 로 렌더링되던 버그).
    campaign = storage.get_latest_campaign_input(brand_id, keyword)
    attached_ids = campaign.attached_source_ids if campaign else []
    attached = storage.get_message_sources_by_ids(attached_ids)
    brand_sources = storage.list_message_sources(brand_id)
    media_assets = storage.list_media_assets(brand_id)
    merged = asset_merge.merge_assets(
        campaign_input=campaign,
        attached_sources=attached,
        brand_sources=brand_sources,
        media_assets=media_assets,
    )

    # 2) reuse_guard — 30일 윈도우 + 차단/경고 분리
    recent = storage.list_recent_cards_for_brand(brand_id, days=30)
    # plan_generator 가 LLM 으로 헤드라인을 만드므로 candidate_headlines 는
    # 빈 리스트로 시작 (블락은 LLM 출력 후 사후 검증으로 처리). 현재는 경고만 활용.
    reuse_check = reuse_guard.check_reuse(
        candidate_headlines=[],
        recent_plans=recent,
        allow_override=allow_reuse_override,
    )

    # 3) reuse_group_id 생성 — N variant 묶음
    group_id = str(uuid.uuid4())

    # 4) strategy 우선순위 N개 선택 + plan 생성
    strategies = _select_strategies(keyword, strategy_count)
    plans: list[BrandCardPlan] = []
    for strategy in strategies:
        template_id = _STRATEGY_TEMPLATE.get(strategy, "clinic_trust")
        plan = plan_generator.generate_brand_card_plan(
            brand_id=brand_id,
            keyword=keyword,
            strategy=strategy,
            expression_level=expression_level,
            template_id=template_id,
            merged_assets=merged,
            reuse_check=reuse_check,
            reuse_group_id=group_id,
        )
        # [B7] 컴플라이언스 검증·수정 — plan 저장 전에 적용해 draft 상태부터 안전 텍스트 보장.
        # 위반 fix 실패 시 plan 은 draft 유지 + source_summary 에 위반 표시 (사용자 판단 위임).
        fixed_plan, report = bc_compliance.validate_brand_card_plan(plan)
        fixed_plan = fixed_plan.model_copy(
            update={"source_summary": _merge_compliance_summary(fixed_plan, report)},
        )
        saved = storage.insert_card_plan(fixed_plan)
        plans.append(saved)
        logger.info(
            "brand_card.plan_generated brand=%s keyword=%r strategy=%s "
            "plan_id=%s compliance_passed=%s violations=%d",
            brand_id,
            keyword,
            strategy,
            saved.id,
            report.passed,
            len(report.violations),
        )

    logger.info(
        "brand_card.plans_summary brand=%s keyword=%r count=%d group_id=%s",
        brand_id,
        keyword,
        len(plans),
        group_id,
    )
    return plans


def approve_plan(plan_id: str) -> BrandCardPlan | None:
    """[B6] 사용자 승인 — draft/reviewed → approved.

    승인된 plan 만 render_card_set 으로 진행 가능. 비용 게이트.
    SPEC §9.3 전이도 위반 시 StatusTransitionError.
    """
    return _transition_plan(plan_id, target=BrandCardStatus.APPROVED.value)


def reject_plan(plan_id: str) -> BrandCardPlan | None:
    """사용자 반려 — draft/reviewed/approved → rejected.

    SPEC §9.3 전이도. published/archived/rejected 상태에서는 호출 금지.
    """
    return _transition_plan(plan_id, target=BrandCardStatus.REJECTED.value)


class PlanEditNotAllowedError(BrandCardError):
    """수정 가능한 status 가 아님 — published/rejected/archived 등."""


_EDITABLE_STATUSES = frozenset({BrandCardStatus.DRAFT.value, BrandCardStatus.REVIEWED.value})


def edit_plan(plan_id: str, *, blocks: list[CardBlock]) -> BrandCardPlan | None:
    """카드 blocks 부분 수정 — 문구/사진(image_asset_id)/AI prompt 변경.

    제약:
    - 수정 가능한 status 는 draft / reviewed 만. 그 외(approved/published/
      rejected/archived) 는 PlanEditNotAllowedError.
    - draft 였다면 자동으로 reviewed 로 전이 (사용자 검토 흔적 기록).
    - blocks 배열 통째 교체 — 부분 수정은 호출자가 fetch + merge 후 전달.
    """
    current = storage.get_card_plan(plan_id)
    if current is None:
        return None
    if current.status not in _EDITABLE_STATUSES:
        raise PlanEditNotAllowedError(
            f"수정 가능한 status 가 아닙니다: {current.status} (허용: draft/reviewed)"
        )
    new_status = (
        BrandCardStatus.REVIEWED.value if current.status == BrandCardStatus.DRAFT.value else None
    )
    return storage.update_card_blocks(plan_id, blocks, new_status=new_status)


def _transition_plan(plan_id: str, *, target: str) -> BrandCardPlan | None:
    """현재 status fetch → SPEC §9.3 전이 검증 → storage 업데이트."""
    current = storage.get_card_plan(plan_id)
    if current is None:
        return None
    assert_status_transition(current.status, target)
    return storage.update_card_status(plan_id, status=target)


def render_card_set(
    reuse_group_id: str,
    *,
    output_root: Path | None = None,
    brand_name: str | None = None,
    brand_url: str | None = None,
    media_path_resolver: Any | None = None,
) -> RenderedCardSet:
    """[B7]~[B12] 렌더링 + AI 이미지 prefetch + manifest 저장.

    Args:
        reuse_group_id: generate_card_plan 으로 생성된 묶음 ID.
        output_root: PNG/manifest 저장 루트. 미지정 시 settings.output_dir.
        brand_name: 카드 브랜드 표시명 (없으면 brand_id 사용).
        brand_url: 카드 footer 표시 URL.
        media_path_resolver: image_asset_id → 파일 경로 변환 콜러블 (테스트 주입용).

    Returns: RenderedCardSet — 모든 카드 PNG 경로 + manifest.

    Raises:
        BrandCardError: 묶음 미존재 또는 모든 카드가 status!=approved.
    """
    plans = storage.list_cards_by_reuse_group(reuse_group_id)
    if not plans:
        raise BrandCardError(f"reuse_group_id={reuse_group_id!r} 에 plan 없음")
    approved = [p for p in plans if p.status == "approved"]
    if not approved:
        raise BrandCardError(
            f"reuse_group_id={reuse_group_id!r} 에 status=approved 인 plan 없음. "
            "approve_plan 호출 후 재시도"
        )

    base_dir = (output_root or Path("output") / "brand_cards") / reuse_group_id
    cards_dir = base_dir / "cards"
    images_dir = base_dir / "images"
    work_dir = base_dir / "_work"
    cards_dir.mkdir(parents=True, exist_ok=True)

    # 2026-05-11 — media_path_resolver 미지정 시 Supabase Storage 자동 다운로드
    # resolver 생성. 이전엔 JobManager dispatch 가 resolver 를 안 넘겨 image_asset_id
    # 가 채워져도 항상 None 으로 떨어져 빈 placeholder 로 렌더링되던 버그 차단.
    if media_path_resolver is None:
        media_path_resolver = _make_supabase_media_resolver(work_dir / "media")

    # [B7] 렌더 직전 최종 컴플라이언스 재검증 — 승인 후 텍스트가 안전한지 보증.
    # generate 시 1차 통과했어도, 사용자가 수동으로 텍스트를 수정한 케이스 대비.
    plan_reports: dict[str, ComplianceReport] = {}
    fixed_plans: list[BrandCardPlan] = []
    for plan in approved:
        fixed, report = bc_compliance.validate_brand_card_plan(plan)
        fixed_plans.append(fixed)
        if plan.id:
            plan_reports[plan.id] = report

    # [B8.5] AI 이미지 prefetch — 모든 plan 의 ai_image_prompt 블록 일괄
    image_paths = _prefetch_ai_images(fixed_plans, base_dir=base_dir, images_dir=images_dir)

    rendered: list[RenderedBrandCard] = []
    name = brand_name or fixed_plans[0].brand_id
    for plan in fixed_plans:
        report = plan_reports.get(plan.id or "")
        rendered.extend(
            _render_plan_blocks(
                plan=plan,
                ai_image_paths=image_paths.get(plan.id or "", {}),
                media_resolver=media_path_resolver,
                cards_dir=cards_dir,
                work_dir=work_dir,
                brand_name=name,
                brand_url=brand_url,
                compliance_report=report,
            )
        )

    # [B11] manifest 저장
    manifest_path = manifest.write_manifest(
        output_dir=base_dir,
        brand_id=fixed_plans[0].brand_id,
        keyword=fixed_plans[0].keyword,
        cards=rendered,
        generated_at=datetime.now().astimezone(),
    )

    # plan status 전이: approved → published (compliance_report 함께 저장)
    for plan in fixed_plans:
        if not plan.id:
            continue
        assert_status_transition(plan.status, BrandCardStatus.PUBLISHED.value)
        report = plan_reports.get(plan.id)
        storage.update_card_status(
            plan.id,
            status=BrandCardStatus.PUBLISHED.value,
            compliance_report=_report_to_dict(report) if report else None,
        )

    logger.info(
        "brand_card.render_completed group=%s cards=%d manifest=%s",
        reuse_group_id,
        len(rendered),
        manifest_path,
    )
    return RenderedCardSet(
        reuse_group_id=reuse_group_id,
        brand_id=fixed_plans[0].brand_id,
        keyword=fixed_plans[0].keyword,
        cards=rendered,
        manifest_path=manifest_path,
    )


def _prefetch_ai_images(
    plans: list[BrandCardPlan],
    *,
    base_dir: Path,
    images_dir: Path,
) -> dict[str, dict[int, Path]]:
    """plan 별 ai_image_prompt 블록의 PNG 경로 매핑.

    plan_id → {block_idx: png_path} dict 반환.
    """
    from domain.image_generation import generator as img_gen
    from domain.image_generation.model import ImagePrompt

    out: dict[str, dict[int, Path]] = {}
    for plan in plans:
        plan_id = plan.id or ""
        prompt_pairs = image_prefetch.build_image_prompts(plan.blocks)
        if not prompt_pairs:
            out[plan_id] = {}
            continue
        prompts = [ImagePrompt(**dict(p[1])) for p in prompt_pairs]  # type: ignore[arg-type]
        block_idx_by_seq: dict[int, int] = {}
        for block_idx, prompt_kwargs in prompt_pairs:
            seq_value = prompt_kwargs["sequence"]
            assert isinstance(seq_value, int)
            block_idx_by_seq[seq_value] = block_idx
        result = img_gen.generate_images(
            prompts=prompts,
            output_dir=base_dir,
            cache_dir=Path(settings.image_cache_dir),
            budget=settings.brand_card_image_budget_per_set,
        )
        gen_seqs = [g.sequence for g in result.generated]
        skip_seqs = {s.sequence: s.reason for s in result.skipped}
        prefetch = image_prefetch.map_results_to_blocks(
            block_index_by_seq=block_idx_by_seq,
            images_dir=images_dir,
            generated_seqs=gen_seqs,
            skipped_seqs=skip_seqs,
        )
        out[plan_id] = prefetch.paths
    return out


def _render_plan_blocks(
    *,
    plan: BrandCardPlan,
    ai_image_paths: dict[int, Path],
    media_resolver: Any | None,
    cards_dir: Path,
    work_dir: Path,
    brand_name: str,
    brand_url: str | None,
    compliance_report: ComplianceReport | None = None,
) -> list[RenderedBrandCard]:
    """plan 의 각 block 을 1 PNG 로 렌더 후 RenderedBrandCard 리스트 반환."""
    out: list[RenderedBrandCard] = []
    report_dict = _report_to_dict(compliance_report) if compliance_report else {"passed": True}
    for block_idx, block in enumerate(plan.blocks, start=1):
        image_url = _resolve_image_url(
            block=block,
            block_idx=block_idx - 1,
            ai_image_paths=ai_image_paths,
            media_resolver=media_resolver,
        )
        png_name = f"card-{plan.template_id}-{plan.strategy}-{block_idx:02d}.png"
        png_path = cards_dir / png_name
        ctx = renderer.RenderContext(
            block=block,
            brand_name=brand_name,
            brand_url=brand_url,
            image_url=image_url,
        )
        renderer.render_card_to_png(
            template_id=plan.template_id,
            context=ctx,
            output_path=png_path,
            work_dir=work_dir / f"{plan.id}-{block_idx}",
        )
        out.append(
            RenderedBrandCard(
                brand_id=plan.brand_id,
                keyword=plan.keyword,
                strategy=plan.strategy,
                expression_level=plan.expression_level,
                template_id=plan.template_id,
                variant_idx=block_idx,
                png_path=png_path,
                width_px=1080,
                height_px=1350,
                compliance_report=report_dict,
                reuse_group_id=plan.reuse_group_id,
                status=BrandCardStatus.PUBLISHED.value,
            )
        )
    return out


def _resolve_image_url(
    *,
    block: CardBlock,
    block_idx: int,
    ai_image_paths: dict[int, Path],
    media_resolver: Any | None,
) -> str | None:
    """block 의 이미지 경로 → file:// URL 변환.

    우선순위:
    1. image_asset_id (실사 사진) — media_resolver 로 file path 조회
    2. ai_image_prompt — prefetch 결과
    """
    if block.image_asset_id and media_resolver:
        path = media_resolver(block.image_asset_id)
        if path and Path(path).exists():
            return Path(path).resolve().as_uri()
    ai_path = ai_image_paths.get(block_idx)
    if ai_path and ai_path.exists():
        return ai_path.resolve().as_uri()
    return None


# ── 내부 헬퍼 ─────────────────────────────────────────────────


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _make_supabase_media_resolver(cache_dir: Path):  # type: ignore[no-untyped-def]
    """asset_id → 로컬 file path. Supabase Storage 에서 다운로드 후 temp 저장.

    2026-05-11 — image_asset_id 기반 카드 이미지가 빈 placeholder 로 렌더링되던
    문제 해결. brand_media_assets 의 storage_path 를 download 해 local file 로
    제공. renderer 가 file:// URL 로 chromium 에 로딩.

    cache_dir 안에 sha256 기반 파일명으로 저장 — 같은 asset 두 번 호출 시
    재다운로드 없음. render_card_set 종료 후 work_dir 정리 시 함께 삭제.

    UUID guard — 환각 ID (예: 'clinic_consultation_desk_daegu_v1') 가 들어오면
    Supabase 호출이 PostgreSQL 22P02 (invalid uuid syntax) 로 터지던 사고 차단.
    형식 검증 통과한 ID 만 storage 호출.
    """
    from domain.brand_card.storage_signed import download_object

    cache_dir.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, Path] = {}

    def resolve(asset_id: str) -> Path | None:
        if asset_id in resolved:
            return resolved[asset_id]
        if not _UUID_RE.match(asset_id):
            logger.warning("media_resolver.invalid_uuid id=%s — skip Supabase 호출", asset_id)
            return None
        asset = storage.get_media_asset(asset_id)
        if asset is None:
            logger.warning("media_resolver.asset_not_found id=%s", asset_id)
            return None
        # legacy: file_path 가 있고 실재하면 직접 사용
        if asset.file_path and Path(asset.file_path).exists():
            resolved[asset_id] = Path(asset.file_path)
            return resolved[asset_id]
        if not asset.storage_path:
            logger.warning("media_resolver.no_storage_path id=%s", asset_id)
            return None
        try:
            raw = download_object(
                asset.storage_path,
                bucket=settings.brand_media_bucket,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "media_resolver.download_failed id=%s storage_path=%s",
                asset_id,
                asset.storage_path,
                exc_info=True,
            )
            return None
        suffix = Path(asset.storage_path).suffix or ".png"
        # sha256 prefix 면 충돌 없음. 없으면 asset_id fallback.
        name_seed = asset.file_sha256 or asset_id.replace("/", "_")
        temp_path = cache_dir / f"media-{name_seed}{suffix}"
        temp_path.write_bytes(raw)
        resolved[asset_id] = temp_path
        return temp_path

    return resolve


def _select_strategies(keyword: str, count: int) -> list[str]:
    """키워드 특성에 맞는 strategy 우선순위 N개 선택.

    P1 은 default 순서로 단순 슬라이스. 추후 키워드 분류기로 확장.
    """
    _ = keyword
    return _STRATEGY_HINTS["default"][:count]


def _report_to_dict(report: ComplianceReport) -> dict[str, Any]:
    """ComplianceReport 를 brand_cards.compliance_report jsonb 형태로 직렬화."""
    return report.model_dump(mode="json")


def _merge_compliance_summary(
    plan: BrandCardPlan,
    report: ComplianceReport,
) -> dict[str, Any]:
    """plan.source_summary 에 compliance_report 를 병합 — DB 보존용."""
    summary = dict(plan.source_summary)
    summary["compliance_report"] = _report_to_dict(report)
    return summary
