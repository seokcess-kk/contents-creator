"""의료법 자동 수정 — 구절 치환 우선, 문단 재생성 폴백.

rules.py 만 참조한다. 금지 표현을 이 파일에 정의하지 않는다.
SPEC-SEO-TEXT.md §3 [8], CLAUDE.md fixer 동작 방식 참조.

동작 원칙:
1. 기본: 구절 치환 (phrase replacement) — 위반 표현 → 안전 대체어
2. 폴백: 해당 문단만 LLM 재생성 (도입부 제외, M2 톤 락)
3. 전체 본문 재생성 절대 금지
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.common.usage import ApiUsage, record_usage
from domain.compliance.model import ChangelogEntry, Violation
from domain.compliance.rules import (
    CompliancePolicy,
    ViolationCategory,
    get_all_patterns,
    get_safe_alternatives,
)

logger = logging.getLogger(__name__)

# ── LLM tool_use 스키마 ──

_FIX_TOOL: dict[str, Any] = {
    "name": "propose_fix",
    "description": "위반 문단의 수정안을 제안한다.",
    "input_schema": {
        "type": "object",
        "required": ["fixed_text", "change_summary"],
        "properties": {
            "fixed_text": {"type": "string"},
            "change_summary": {"type": "string"},
        },
    },
}


# ── 공개 API ──


def fix_violations(
    text: str,
    violations: list[Violation],
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
    protect_intro: bool = True,
    keyword: str | None = None,
) -> tuple[str, list[ChangelogEntry]]:
    """위반 표현을 수정한다.

    Args:
        text: 원본 텍스트.
        violations: 감지된 위반 목록.
        policy: 컴플라이언스 정책.
        protect_intro: True 면 첫 문단(도입부)은 치환만, 재생성 금지.
        keyword: 타겟 SEO 키워드. 재생성 시 키워드 컨텍스트 제공.

    Returns:
        (수정된 텍스트, 변경 이력 리스트) 튜플.
    """
    changelog: list[ChangelogEntry] = []
    current_text = text

    for violation in violations:
        fixed, entry = _fix_single_violation(
            current_text,
            violation,
            policy,
            protect_intro,
            keyword=keyword,
        )
        if entry is not None:
            current_text = fixed
            changelog.append(entry)

    return current_text, changelog


# ── 내부 헬퍼 ──


def _fix_single_violation(
    text: str,
    violation: Violation,
    policy: CompliancePolicy,
    protect_intro: bool,
    keyword: str | None = None,
) -> tuple[str, ChangelogEntry | None]:
    """단일 위반을 수정한다. 치환 우선, 폴백 재생성."""
    # 1차 시도: 구절 치환
    fixed, entry = _try_phrase_replacement(text, violation, policy)
    if entry is not None:
        return fixed, entry

    # 2차 시도: 문단 재생성 (도입부 보호)
    is_intro = _is_intro_violation(text, violation)
    if is_intro and protect_intro:
        logger.warning(
            "도입부 위반 '%s' 구절 치환 실패. M2 원칙으로 재생성 불가.",
            violation.text_snippet[:30],
        )
        return text, None

    return _try_paragraph_regeneration(text, violation, policy, keyword=keyword)


def _try_phrase_replacement(
    text: str,
    violation: Violation,
    policy: CompliancePolicy,
) -> tuple[str, ChangelogEntry | None]:
    """regex 매칭 위치의 위반 표현을 안전 대체어로 치환한다."""
    category = ViolationCategory(violation.category)
    alternatives = get_safe_alternatives(category, policy)
    if not alternatives:
        return text, None

    patterns = get_all_patterns(policy)
    for cat, pattern in patterns:
        if cat != category:
            continue
        match = pattern.search(text)
        if match is None:
            continue

        before_text = match.group()
        replacement = alternatives[0]
        new_text = text[: match.start()] + replacement + text[match.end() :]

        entry = ChangelogEntry(
            section=violation.section_index,
            before=before_text,
            after=replacement,
            rule=violation.category,
            reason=f"구절 치환: {violation.reason}",
        )
        return new_text, entry

    return text, None


def _build_prohibited_list(policy: CompliancePolicy) -> str:
    """rules.py 의 금지 표현을 LLM 프롬프트용 텍스트로 조립한다."""
    lines: list[str] = []
    for cat, pattern in get_all_patterns(policy):
        lines.append(f"- [{cat.value}] {pattern.pattern}")
    lines.append(
        "- 절대 사용하지 말 것: "
        "'저희', '우리 병원', '우리 한의원', '당사', "
        "'예약하세요', '전화주세요', '상담 받으세요'"
    )
    return "\n".join(lines)


def _try_paragraph_regeneration(
    text: str,
    violation: Violation,
    policy: CompliancePolicy,
    keyword: str | None = None,
) -> tuple[str, ChangelogEntry | None]:
    """위반 문단만 LLM 으로 재생성한다.

    전체 본문 재생성 금지. 해당 문단만 국소 수정.
    """
    paragraph = _find_violation_paragraph(text, violation)
    if paragraph is None:
        return text, None

    alternatives = get_safe_alternatives(ViolationCategory(violation.category), policy)
    alt_text = ", ".join(alternatives) if alternatives else "안전한 표현"
    prohibited = _build_prohibited_list(policy)

    api_key = require("anthropic_api_key")
    client = anthropic.Anthropic(api_key=api_key)

    keyword_context = ""
    if keyword is not None:
        keyword_context = (
            f"\n[SEO 키워드 컨텍스트]\n"
            f'타겟 SEO 키워드: "{keyword}"\n'
            f"키워드는 자연스럽게 유지하되 1인칭과 결합하지 마라.\n"
        )

    system_prompt = (
        "너는 한국 의료 콘텐츠 전문 편집자다.\n"
        "아래 문단에 의료광고법 위반 표현이 있다.\n"
        "동일한 의미를 전달하되 위반을 제거한 문단을 작성하라.\n"
        "톤과 문체를 유지하고, 문단 길이를 비슷하게 맞춰라.\n\n"
        f"[위반 카테고리] {violation.category}\n"
        f"[위반 사유] {violation.reason}\n"
        f"[안전 대체 표현] {alt_text}\n"
        f"\n[금지 표현 목록]\n{prohibited}\n"
        f"{keyword_context}"
    )

    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_sonnet,
        max_tokens=2048,
        tools=[_FIX_TOOL],
        tool_choice={"type": "tool", "name": "propose_fix"},
        messages=[
            {
                "role": "user",
                "content": f"[수정 대상 문단]\n{paragraph}",
            },
        ],
        system=system_prompt,
    )

    record_usage(ApiUsage(
        provider="anthropic", model=settings.model_sonnet,
        input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens,
    ))
    fixed_paragraph = _parse_fix_response(response)
    if fixed_paragraph is None:
        return text, None

    new_text = text.replace(paragraph, fixed_paragraph, 1)
    entry = ChangelogEntry(
        section=violation.section_index,
        before=paragraph,
        after=fixed_paragraph,
        rule=violation.category,
        reason=f"문단 재생성: {violation.reason}",
    )
    return new_text, entry


def _find_violation_paragraph(
    text: str,
    violation: Violation,
) -> str | None:
    """위반 snippet 을 포함하는 문단을 찾는다."""
    # snippet 에서 핵심 부분 추출 (앞뒤 컨텍스트 제거)
    snippet_core = violation.text_snippet.strip()
    if len(snippet_core) > 30:
        # snippet 이 길면 중간 30자만 사용
        mid = len(snippet_core) // 2
        snippet_core = snippet_core[max(0, mid - 15) : mid + 15]

    paragraphs = text.split("\n\n")
    for para in paragraphs:
        if snippet_core in para:
            return para

    # 단일 줄바꿈으로 분리된 문단 시도
    for para in text.split("\n"):
        if snippet_core in para and len(para) > 20:
            return para

    return None


def _is_intro_violation(text: str, violation: Violation) -> bool:
    """위반이 도입부(첫 문단)에 해당하는지 판단한다."""
    if violation.section_index is not None and violation.section_index <= 1:
        return True

    paragraphs = text.split("\n\n")
    if not paragraphs:
        return False

    first_para = paragraphs[0]
    snippet_core = violation.text_snippet.strip()[:30]
    return snippet_core in first_para


def _parse_fix_response(
    response: Any,
) -> str | None:
    """LLM propose_fix 응답에서 수정 텍스트를 추출한다."""
    for block in response.content:
        if block.type == "tool_use" and block.name == "propose_fix":
            result: str | None = block.input.get("fixed_text")
            return result
    return None
