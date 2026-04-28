"""[B7] 브랜드 카드 컴플라이언스 — BRAND_LENIENT 검증 + 자동 수정 wrapper.

domain/compliance.checker / fixer 를 호출해 BrandCardPlan 의 모든 텍스트
필드(angle / headline / subcopy / bullets / ai_image_prompt) 를 검증한다.

핵심 원칙:
- 의료법 10개 카테고리는 항상 BRAND_LENIENT 9개 룰로 검사 (단일 출처는 rules.py).
- expression_level=safe 일 때만 hooking 표현(SPEC §7) 을 추가 경고. 의료법 위반이 아니므로
  rules.py 에 두지 않고 본 모듈에서만 검사하며, 텍스트 자체는 수정하지 않고 changelog 에 기록.
- ai_image_prompt 는 image_prompt_validator 로 별도 검증 후 위반 시 비운다.
- 도메인 격리: SEO 트랙 도메인은 import 하지 않고, domain/compliance 만 참조 (CLAUDE.md 예외).

SPEC-BRAND-CARD §7 (표현 강도) + §8 (BRAND_LENIENT) 구현.
"""

from __future__ import annotations

import logging

from domain.brand_card.model import BrandCardPlan, CardBlock, ExpressionLevel
from domain.common.image_prompt_validator import (
    InvalidImagePromptError,
    validate_prompt,
)
from domain.compliance.checker import check_compliance
from domain.compliance.model import ChangelogEntry, ComplianceReport, Violation
from domain.compliance.rules import (
    CompliancePolicy,
    ViolationCategory,
    get_all_patterns,
    get_safe_alternatives,
)

logger = logging.getLogger(__name__)

MAX_FIX_ITERATIONS = 2

# expression_level=safe 에서만 추가 차단할 hooking 표현 키워드.
# SPEC §7 "hooking 에서 허용" 5종(문제 자극·공감 질문·실패 경험·선택 기준·생활 패턴) 정합.
# 의료법 위반이 아니므로 rules.py 단일 출처 원칙과 무관 — 표현 강도 차등용 보조 검사.
_HOOKING_ONLY_PHRASES: tuple[str, ...] = (
    "실패했다면",
    "오래가지 않",
    "혼자 버티",
    "버티기 어렵",
    "굶는",
    "포기하고",
)

_EXPRESSION_RULE_ID = "expression_level_safe"


def validate_brand_card_plan(
    plan: BrandCardPlan,
    *,
    max_iterations: int = MAX_FIX_ITERATIONS,
) -> tuple[BrandCardPlan, ComplianceReport]:
    """BrandCardPlan 을 BRAND_LENIENT 로 검증·수정한다.

    Args:
        plan: 검증 대상 기획안.
        max_iterations: 검증-수정 반복 횟수 (기본 2).

    Returns:
        (수정된 plan, ComplianceReport) 튜플.
        - 통과 시: report.passed=True, plan 은 안전 대체된 텍스트 반영.
        - max iter 도달 시: report.passed=False, 잔존 위반은 report.violations.
    """
    current_blocks = list(plan.blocks)
    angle = plan.angle
    changelog: list[ChangelogEntry] = []
    final_violations: list[Violation] = []
    iteration = 0

    while iteration < max_iterations:
        joined = _serialize_blocks(current_blocks, angle=angle)
        violations = check_compliance(
            joined,
            policy=CompliancePolicy.BRAND_LENIENT,
            keyword=plan.keyword,
        )
        if not violations:
            final_violations = []
            break

        next_blocks, next_angle, iter_changelog = _apply_phrase_replacement(
            current_blocks,
            angle,
            violations,
        )
        if not iter_changelog:
            final_violations = violations
            break

        current_blocks = next_blocks
        angle = next_angle
        changelog.extend(iter_changelog)
        iteration += 1
        final_violations = violations

    # ai_image_prompt 별도 검증 — 위반 시 None 으로 비운다.
    current_blocks, image_changelog = _validate_image_prompts(current_blocks)
    changelog.extend(image_changelog)

    # expression_level=safe 추가 경고 — 텍스트 수정 없이 changelog 기록만.
    expression_changelog = _check_expression_level_warnings(
        _serialize_blocks(current_blocks, angle=angle),
        plan.expression_level,
    )
    changelog.extend(expression_changelog)

    fixed_plan = plan.model_copy(
        update={"blocks": current_blocks, "angle": angle},
    )
    passed = not final_violations
    report = ComplianceReport(
        passed=passed,
        iterations=iteration,
        violations=final_violations,
        changelog=changelog,
        final_text=_serialize_blocks(current_blocks, angle=angle),
    )
    logger.info(
        "brand_card.compliance plan_id=%s passed=%s iterations=%d violations=%d",
        plan.id,
        passed,
        iteration,
        len(final_violations),
    )
    return fixed_plan, report


def _serialize_blocks(blocks: list[CardBlock], *, angle: str) -> str:
    """blocks + angle 의 모든 텍스트 필드를 단일 문자열로 직렬화."""
    parts: list[str] = []
    if angle:
        parts.append(angle)
    for b in blocks:
        parts.append(b.headline)
        if b.subcopy:
            parts.append(b.subcopy)
        parts.extend(b.bullets)
    return "\n\n".join(parts)


def _apply_phrase_replacement(
    blocks: list[CardBlock],
    angle: str,
    violations: list[Violation],
) -> tuple[list[CardBlock], str, list[ChangelogEntry]]:
    """위반 카테고리에 매칭되는 표현을 안전 대체어로 치환.

    각 블록의 headline / subcopy / bullets 와 angle 에 BRAND_LENIENT 규칙
    적용. fixer.py 의 paragraph 재생성은 사용하지 않는다 — 블록 단위 텍스트가
    짧아 통째 재작성이 LLM 비용 대비 의미 적음.
    """
    violated_categories = {
        ViolationCategory(v.category) for v in violations if _is_known_category(v.category)
    }
    if not violated_categories:
        return blocks, angle, []

    patterns = [
        (cat, pattern)
        for cat, pattern in get_all_patterns(CompliancePolicy.BRAND_LENIENT)
        if cat in violated_categories
    ]
    changelog: list[ChangelogEntry] = []

    def fix_text(text: str, section: int | None) -> str:
        result = text
        for cat, pattern in patterns:
            match = pattern.search(result)
            if match is None:
                continue
            alts = get_safe_alternatives(cat, CompliancePolicy.BRAND_LENIENT)
            if not alts:
                continue
            replacement = alts[0]
            before = match.group()
            result = result[: match.start()] + replacement + result[match.end() :]
            changelog.append(
                ChangelogEntry(
                    section=section,
                    before=before,
                    after=replacement,
                    rule=cat.value,
                    reason=f"brand_card phrase replacement (section={section})",
                ),
            )
        return result

    new_angle = fix_text(angle, section=None)
    new_blocks: list[CardBlock] = []
    for idx, b in enumerate(blocks):
        new_blocks.append(
            b.model_copy(
                update={
                    "headline": fix_text(b.headline, section=idx),
                    "subcopy": fix_text(b.subcopy, section=idx) if b.subcopy else None,
                    "bullets": [fix_text(bl, section=idx) for bl in b.bullets],
                },
            ),
        )
    return new_blocks, new_angle, changelog


def _validate_image_prompts(
    blocks: list[CardBlock],
) -> tuple[list[CardBlock], list[ChangelogEntry]]:
    """각 블록의 ai_image_prompt 를 validate. 위반 시 None 으로 비운다."""
    changelog: list[ChangelogEntry] = []
    new_blocks: list[CardBlock] = []
    for idx, b in enumerate(blocks):
        if not b.ai_image_prompt:
            new_blocks.append(b)
            continue
        try:
            validate_prompt(b.ai_image_prompt)
            new_blocks.append(b)
        except InvalidImagePromptError as exc:
            logger.warning(
                "brand_card.image_prompt_violation block=%d card_type=%s: %s",
                idx,
                b.card_type,
                exc,
            )
            changelog.append(
                ChangelogEntry(
                    section=idx,
                    before=b.ai_image_prompt,
                    after="",
                    rule="image_prompt_validation",
                    reason=str(exc),
                ),
            )
            new_blocks.append(b.model_copy(update={"ai_image_prompt": None}))
    return new_blocks, changelog


def _check_expression_level_warnings(
    text: str,
    level: str,
) -> list[ChangelogEntry]:
    """expression_level=safe 일 때만 hooking 표현 발견을 경고로 기록.

    텍스트는 수정하지 않는다 — plan_generator 의 프롬프트 사전 주입이
    1차 방어이고, 본 검사는 누락 발견 시 운영자 가시화용 보조 신호다.
    """
    if level != ExpressionLevel.SAFE.value:
        return []
    out: list[ChangelogEntry] = []
    for phrase in _HOOKING_ONLY_PHRASES:
        if phrase in text:
            out.append(
                ChangelogEntry(
                    section=None,
                    before=phrase,
                    after=phrase,
                    rule=_EXPRESSION_RULE_ID,
                    reason=(
                        f"expression_level=safe 인데 hooking 표현 '{phrase}' 발견 — "
                        "수정 권고 (자동 치환 안 함)"
                    ),
                ),
            )
    return out


def _is_known_category(category: str) -> bool:
    """LLM 이 새로운 카테고리 문자열을 반환할 가능성 방어."""
    try:
        ViolationCategory(category)
    except ValueError:
        return False
    return True
