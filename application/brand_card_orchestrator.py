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
import uuid
from typing import Any

from domain.brand_card import asset_merge, plan_generator, reuse_guard, storage
from domain.brand_card.model import BrandCardPlan, ExpressionLevel

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

    # 1) 자산 fetch — 캠페인 입력 + 첨부 + 브랜드 공통
    campaign = storage.get_latest_campaign_input(brand_id, keyword)
    attached_ids = campaign.attached_source_ids if campaign else []
    attached = storage.get_message_sources_by_ids(attached_ids)
    brand_sources = storage.list_message_sources(brand_id)
    merged = asset_merge.merge_assets(
        campaign_input=campaign,
        attached_sources=attached,
        brand_sources=brand_sources,
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
        saved = storage.insert_card_plan(plan)
        plans.append(saved)
        logger.info(
            "brand_card.plan_generated brand=%s keyword=%r strategy=%s plan_id=%s",
            brand_id,
            keyword,
            strategy,
            saved.id,
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
    """[B6] 사용자 승인 — status=draft → approved.

    승인된 plan 만 render_card_set 으로 진행 가능. 비용 게이트.
    """
    return storage.update_card_status(plan_id, status="approved")


def reject_plan(plan_id: str) -> BrandCardPlan | None:
    """사용자 반려 — status=rejected."""
    return storage.update_card_status(plan_id, status="rejected")


def render_card_set(reuse_group_id: str) -> dict[str, Any]:
    """[B7]~[B12] 렌더링 + 의료법 검증 + PNG 저장.

    Phase 2.5 에서 구현. 현재는 NotImplementedError 로 가시화.
    """
    raise NotImplementedError(
        "render_card_set 는 Phase 2.5 에서 구현 예정. "
        f"reuse_group_id={reuse_group_id} 는 현재 plan(status=approved) 까지만 진행 가능."
    )


# ── 내부 헬퍼 ─────────────────────────────────────────────────


def _select_strategies(keyword: str, count: int) -> list[str]:
    """키워드 특성에 맞는 strategy 우선순위 N개 선택.

    P1 은 default 순서로 단순 슬라이스. 추후 키워드 분류기로 확장.
    """
    _ = keyword
    return _STRATEGY_HINTS["default"][:count]
