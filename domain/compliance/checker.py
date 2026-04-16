"""의료법 검증 — 규칙 기반 1차 + LLM 2차.

rules.py 만 참조한다. 금지 표현을 이 파일에 정의하지 않는다.
SPEC-SEO-TEXT.md §3 [8], CLAUDE.md "의료광고법 — 타협 없음" 참조.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from config.settings import require, settings
from domain.compliance.model import Violation
from domain.compliance.rules import (
    CompliancePolicy,
    ViolationCategory,
    get_all_patterns,
    get_rules,
)

logger = logging.getLogger(__name__)

MAX_FIX_ITERATIONS = 2

# ── LLM tool_use 스키마 ──

_VIOLATION_TOOL: dict[str, Any] = {
    "name": "report_violations",
    "description": "의료광고법 위반 항목을 보고한다.",
    "input_schema": {
        "type": "object",
        "required": ["violations"],
        "properties": {
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "category",
                        "text_snippet",
                        "severity",
                        "reason",
                    ],
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [c.value for c in ViolationCategory],
                        },
                        "text_snippet": {"type": "string"},
                        "section_index": {"type": "integer"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    },
}


# ── 공개 API ──


def check_compliance(
    text: str,
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
    keyword: str | None = None,
) -> list[Violation]:
    """텍스트의 의료법 위반을 감지한다.

    2단계 검증:
    1. 규칙 기반 1차 스크리닝 (regex)
    2. LLM 2차 검증 (Sonnet 4.6, tool_use)

    두 결과를 병합·중복 제거하여 반환한다.

    Args:
        text: 검증 대상 텍스트.
        policy: 컴플라이언스 정책.
        keyword: 타겟 SEO 키워드. LLM 이 키워드 사용을 위반으로 오인하지 않도록 컨텍스트 제공.
    """
    regex_violations = _check_regex(text, policy)
    llm_violations = _check_llm(text, policy, keyword=keyword)
    return _merge_violations(regex_violations, llm_violations)


# ── 규칙 기반 1차 ──


def _check_regex(
    text: str,
    policy: CompliancePolicy,
) -> list[Violation]:
    """regex 패턴으로 명확한 위반을 즉시 감지한다."""
    violations: list[Violation] = []
    compiled_patterns = get_all_patterns(policy)

    for category, pattern in compiled_patterns:
        for match in pattern.finditer(text):
            snippet = _extract_snippet(text, match.start(), match.end())
            violations.append(
                Violation(
                    category=category.value,
                    text_snippet=snippet,
                    severity="high",
                    reason=f"규칙 기반 감지: '{match.group()}' 패턴 매칭",
                ),
            )

    return violations


def _extract_snippet(text: str, start: int, end: int) -> str:
    """매칭 위치 주변 50자를 포함한 발췌를 추출한다."""
    ctx_start = max(0, start - 50)
    ctx_end = min(len(text), end + 50)
    return text[ctx_start:ctx_end]


# ── LLM 2차 검증 ──


def _check_llm(
    text: str,
    policy: CompliancePolicy,
    keyword: str | None = None,
) -> list[Violation]:
    """Sonnet 4.6 으로 암시적 위반을 감지한다."""
    api_key = require("anthropic_api_key")
    client = anthropic.Anthropic(api_key=api_key)

    rules_desc = _build_rules_description(policy)

    keyword_context = ""
    if keyword is not None:
        keyword_context = (
            f"\n\n[SEO 키워드 컨텍스트]\n"
            f'이 콘텐츠의 타겟 SEO 키워드는 "{keyword}"이다.\n'
            f"키워드가 본문에 자연스럽게 사용되는 것은 위반이 아니다.\n"
            f"키워드 자체가 특정 업체를 지칭하는 것처럼 보여도, "
            f"SEO 목적의 정보성 콘텐츠에서 키워드를 사용하는 것은 "
            f"first_person_promotion에 해당하지 않는다.\n"
            f'단, "저희 {keyword}", "우리 {keyword}" 등 '
            f"1인칭과 결합한 경우는 여전히 위반이다."
        )

    system_prompt = (
        "너는 한국 의료광고법 검증 전문가다.\n"
        "아래 텍스트에서 의료광고법 위반 표현을 찾아 보고한다.\n"
        "regex 로 잡기 어려운 암시적 표현, 문맥 의존적 위반, "
        "교묘한 보장 뉘앙스에 집중한다.\n\n"
        "위반이 없으면 빈 리스트를 보고한다.\n\n"
        f"[검증 카테고리]\n{rules_desc}"
        f"{keyword_context}"
    )

    response = client.messages.create(  # type: ignore[call-overload]
        model=settings.model_sonnet,
        max_tokens=4096,
        tools=[_VIOLATION_TOOL],
        tool_choice={"type": "tool", "name": "report_violations"},
        messages=[
            {"role": "user", "content": f"[검증 대상 텍스트]\n{text}"},
        ],
        system=system_prompt,
    )

    return _parse_llm_violations(response)


def _build_rules_description(policy: CompliancePolicy) -> str:
    """LLM 프롬프트에 주입할 규칙 설명을 조립한다."""
    lines: list[str] = []
    for rule in get_rules(policy):
        examples = ", ".join(f'"{p}"' for p in rule.patterns[:3])
        alts = ", ".join(rule.safe_alternatives[:2])
        lines.append(
            f"- [{rule.category.value}] {rule.description}\n"
            f"  예시 패턴: {examples}\n"
            f"  안전 대체: {alts}"
        )
    return "\n".join(lines)


def _parse_llm_violations(
    response: Any,
) -> list[Violation]:
    """LLM tool_use 응답에서 Violation 리스트를 파싱한다."""
    violations: list[Violation] = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "report_violations":
            raw_violations = block.input.get("violations", [])
            for v in raw_violations:
                violations.append(
                    Violation(
                        category=v.get("category", ""),
                        text_snippet=v.get("text_snippet", ""),
                        section_index=v.get("section_index"),
                        severity=v.get("severity", "medium"),
                        reason=v.get("reason", ""),
                    ),
                )
    return violations


# ── 중복 제거 ──


def _merge_violations(
    regex_results: list[Violation],
    llm_results: list[Violation],
) -> list[Violation]:
    """regex 와 LLM 결과를 병합하고 중복을 제거한다.

    동일 카테고리 + 유사 snippet 이면 regex 결과를 우선한다.
    """
    merged: list[Violation] = list(regex_results)
    seen_snippets: set[str] = set()
    for v in regex_results:
        seen_snippets.add(v.text_snippet[:30])

    for v in llm_results:
        snippet_key = v.text_snippet[:30]
        if snippet_key not in seen_snippets:
            merged.append(v)
            seen_snippets.add(snippet_key)

    return merged
