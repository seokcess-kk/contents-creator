"""의료법 검증 — 규칙 기반 1차 + LLM 2차.

rules.py 만 참조한다. 금지 표현을 이 파일에 정의하지 않는다.
SPEC-SEO-TEXT.md §3 [8], CLAUDE.md "의료광고법 — 타협 없음" 참조.
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from domain.common.anthropic_client import build_client, messages_create_with_retry
from domain.common.image_prompt_validator import (
    InvalidImagePromptError,
    validate_prompt,
)
from domain.common.usage import ApiUsage, record_usage
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


def check_image_prompts(
    prompts: list[Any],
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
) -> list[Violation]:
    """image_prompts 배열의 compliance 위반을 반환한다.

    검증 범위:
    - `prompt` (영어): `validate_prompt` (image-specific) + rules.py 한국어 금지어
      (일반적으로 영어 prompt 에는 한국어 금지어가 없지만 LLM 이 섞어 쓸 가능성 방어)
    - `alt_text` (한국어): `validate_prompt` 의 검증 대상 아님. rules.py 패턴을 적용하면
      alt_text 의 일상적 한국어 표현(예: "저희 병원 모습") 에 오탐이 발생해 정상
      이미지가 drop 되므로 **미적용**. 대신 본문·outline 단계에서 동일 규칙이 이미
      적용됨.

    Args:
        prompts: `ImagePromptItem` 또는 호환 dict 리스트.
        policy: compliance 정책.
    """
    violations: list[Violation] = []
    compiled_patterns = get_all_patterns(policy)
    for p in prompts:
        seq = _get_attr(p, "sequence", 0)
        prompt_text = _get_attr(p, "prompt", "")

        try:
            validate_prompt(prompt_text)
        except InvalidImagePromptError as exc:
            violations.append(
                Violation(
                    category=ViolationCategory.BEFORE_AFTER.value,
                    text_snippet=prompt_text,
                    section_index=seq,
                    severity="high",
                    reason=f"이미지 prompt 위반: {exc}",
                ),
            )

        for category, pattern in compiled_patterns:
            match = pattern.search(prompt_text)
            if match is None:
                continue
            violations.append(
                Violation(
                    category=category.value,
                    text_snippet=prompt_text[: match.end() + 30],
                    section_index=seq,
                    severity="high",
                    reason=f"이미지 prompt 에 금지 표현 감지: '{match.group()}'",
                ),
            )
    return violations


def _get_attr(obj: Any, name: str, default: Any) -> Any:
    """Pydantic 모델 / dict 공용 접근."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


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
    """Sonnet 4.6 으로 암시적 위반을 감지한다.

    System prompt 에 정책별 규칙 설명을 두고 cache_control 로 캐시.
    compliance iteration (최대 3회) 반복 호출 시 1회 write + 2회 read.
    """
    client = build_client()

    rules_desc = _build_rules_description(policy)
    # 규칙 설명은 policy 에만 의존 — 캐시 대상. keyword 는 user 메시지로 분리.
    system_text = (
        "너는 한국 의료광고법 검증 전문가다.\n"
        "아래 텍스트에서 의료광고법 위반 표현을 찾아 보고한다.\n"
        "regex 로 잡기 어려운 암시적 표현, 문맥 의존적 위반, "
        "교묘한 보장 뉘앙스에 집중한다.\n\n"
        "위반이 없으면 빈 리스트를 보고한다.\n\n"
        f"[검증 카테고리]\n{rules_desc}"
    )

    user_content = f"[검증 대상 텍스트]\n{text}"
    if keyword is not None:
        user_content = (
            f"[SEO 키워드 컨텍스트]\n"
            f'이 콘텐츠의 타겟 SEO 키워드는 "{keyword}"이다.\n'
            f"키워드가 본문에 자연스럽게 사용되는 것은 위반이 아니다.\n"
            f"키워드 자체가 특정 업체를 지칭하는 것처럼 보여도, "
            f"SEO 목적의 정보성 콘텐츠에서 키워드를 사용하는 것은 "
            f"first_person_promotion에 해당하지 않는다.\n"
            f'단, "저희 {keyword}", "우리 {keyword}" 등 '
            f"1인칭과 결합한 경우는 여전히 위반이다.\n\n"
            f"{user_content}"
        )

    response = messages_create_with_retry(
        client,
        model=settings.model_sonnet,
        max_tokens=4096,
        tools=[_VIOLATION_TOOL],
        tool_choice={"type": "tool", "name": "report_violations"},
        messages=[{"role": "user", "content": user_content}],
        system=[
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
    )

    record_usage(
        ApiUsage(
            provider="anthropic",
            model=settings.model_sonnet,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
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
                if not isinstance(v, dict):
                    logger.warning("LLM returned non-dict violation: %s", type(v))
                    continue
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
