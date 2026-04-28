"""brand_card 다양화 — 차단/경고 룰 + 사용자 override (D5).

좋은 다양화 (plan_generator 추구) vs 나쁜 다양화 (본 모듈 차단):
- 좋은: 고객 고민 다름 / 브랜드 강점 다름 / 사진 다름 / 위치 다름 / 전환 목적 다름
- 나쁜: 색만 / 문장 순서만 / 말투만

룰 (SPEC §5):
- 30일 윈도우 동일 headline 재사용 → 차단 (override 가능)
- 같은 의료진 사진 연속 3 키워드 초과 → 경고
- 같은 template_id 5회 연속 → 경고
- 같은 strategy 과도 반복 → 경고
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from domain.brand_card.model import BrandCardPlan, ReuseGuardError

logger = logging.getLogger(__name__)

_HEADLINE_BLOCK_DAYS = 30
_SAME_PHOTO_WARN_THRESHOLD = 3  # 연속 키워드 초과 시 경고
_SAME_TEMPLATE_WARN_THRESHOLD = 5  # 연속 회차 초과 시 경고
_SAME_STRATEGY_WARN_THRESHOLD = 5  # 연속 회차 초과 시 경고


@dataclass(frozen=True)
class ReuseCheckResult:
    """plan_generator 가 후보를 점수 매길 때 참조."""

    blocked_headlines: set[str] = field(default_factory=set)
    warning_template_id: str | None = None  # 5회 연속이면 다른 템플릿 추천
    warning_strategy: str | None = None
    warning_overused_photo_ids: set[str] = field(default_factory=set)

    @property
    def has_warnings(self) -> bool:
        return (
            self.warning_template_id is not None
            or self.warning_strategy is not None
            or bool(self.warning_overused_photo_ids)
        )


def check_reuse(
    *,
    candidate_headlines: list[str],
    recent_plans: list[BrandCardPlan],
    now: datetime | None = None,
    allow_override: bool = False,
) -> ReuseCheckResult:
    """후보 headline 들을 최근 30일 plans 와 대조.

    Args:
        candidate_headlines: 신규 plan 의 후보 headline 목록.
        recent_plans: storage.list_recent_cards_for_brand(days=30) 결과.
        now: 테스트 주입용 현재 시각.
        allow_override: True 시 차단 룰을 경고로 약화 (사용자가 명시 승인).

    Returns: 차단·경고 분리된 결과. plan_generator 가 후보 점수에 반영.

    Raises:
        ReuseGuardError: candidate_headlines 가 모두 차단되어 변형 불가능
            (allow_override=False 인 경우만).
    """
    _ = now  # 향후 윈도우 세분화에 사용 — 현재는 recent_plans 가 이미 필터됨
    blocked = _find_blocked_headlines(candidate_headlines, recent_plans)
    template_warning = _find_overused_template(recent_plans)
    strategy_warning = _find_overused_strategy(recent_plans)
    photo_warnings = _find_overused_photos(recent_plans)

    if blocked and not allow_override and len(blocked) == len(candidate_headlines):
        raise ReuseGuardError(
            f"모든 후보 headline 이 최근 {_HEADLINE_BLOCK_DAYS}일 내 사용됨. "
            "다른 변형을 생성하거나 사용자 override 승인 필요."
        )

    return ReuseCheckResult(
        blocked_headlines=blocked if not allow_override else set(),
        warning_template_id=template_warning,
        warning_strategy=strategy_warning,
        warning_overused_photo_ids=photo_warnings,
    )


def _find_blocked_headlines(
    candidates: list[str],
    recent: list[BrandCardPlan],
) -> set[str]:
    """30일 윈도우 내 사용된 headline 과 일치하는 후보 추출."""
    used: set[str] = set()
    for plan in recent:
        for block in plan.blocks:
            used.add(block.headline.strip())
    return {h.strip() for h in candidates if h.strip() in used}


def _find_overused_template(recent: list[BrandCardPlan]) -> str | None:
    """가장 최근 N개 plan 의 template_id 가 모두 같으면 경고 반환."""
    if len(recent) < _SAME_TEMPLATE_WARN_THRESHOLD:
        return None
    last_n = recent[:_SAME_TEMPLATE_WARN_THRESHOLD]
    template_ids = {p.template_id for p in last_n}
    if len(template_ids) == 1:
        return last_n[0].template_id
    return None


def _find_overused_strategy(recent: list[BrandCardPlan]) -> str | None:
    """가장 최근 N개 plan 의 strategy 가 모두 같으면 경고."""
    if len(recent) < _SAME_STRATEGY_WARN_THRESHOLD:
        return None
    last_n = recent[:_SAME_STRATEGY_WARN_THRESHOLD]
    strategies = {p.strategy for p in last_n}
    if len(strategies) == 1:
        return last_n[0].strategy
    return None


def _find_overused_photos(recent: list[BrandCardPlan]) -> set[str]:
    """연속 N 키워드 초과 사용된 image_asset_id 추출.

    같은 키워드 내 여러 variant 는 1 카운트로 취급. 연속 키워드 = 시간순.
    """
    if len(recent) < _SAME_PHOTO_WARN_THRESHOLD:
        return set()
    # 키워드별 그룹핑 (created_at desc 가정 — recent 가 desc 순)
    by_keyword: list[set[str]] = []
    last_kw: str | None = None
    for plan in recent:
        photo_ids = {b.image_asset_id for b in plan.blocks if b.image_asset_id}
        if plan.keyword != last_kw:
            by_keyword.append(set())
            last_kw = plan.keyword
        by_keyword[-1] |= photo_ids
    if len(by_keyword) < _SAME_PHOTO_WARN_THRESHOLD:
        return set()
    # 가장 최근 N 키워드에서 모두 등장한 photo_id
    recent_n = by_keyword[:_SAME_PHOTO_WARN_THRESHOLD]
    overused: set[str] = set(recent_n[0])
    for group in recent_n[1:]:
        overused &= group
    return overused
