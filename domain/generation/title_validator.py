"""HTML title 검증. 길이, 키워드 반복, 스팸/장식, 의료법 4종.

SPEC-SEO-TEXT.md §3 [6] + docs/naver-seo-guide.md §2.2 / §4.
Layer 1 품질 강제 (outline_validator) 의 자매 검증 모듈.

핵심 원칙:
    "제목은 고치되 intro 톤 락은 절대 흔들지 않는다."
    title quality gate 이지 LLM fixer 가 아니다. 위반은 outline 통째 1회 재생성 +
    재생성된 outline 의 intro 만 코드 덮어쓰기 (LLM 호출 추가 0회).

검증 분기:
    - 길이 / 키워드 반복 / 스팸 → 항상 hard fail (severity=error, 재생성 트리거)
    - 의료법 (compliance) → strict 토글 (default false → warning, true → error)

스팸/장식 패턴은 본 모듈 자체 상수로 보유. compliance/rules.py 단일 출처 원칙은
"의료법 카테고리" 에 한정 — 일반 SEO 품질 규칙은 검증기 자체 보유 가능.

DI 원칙: 의료법 패턴은 application 레이어 (stage_runner) 가 compliance.rules 에서
build 후 주입한다 (prompt_builder 와 동일 패턴). domain/generation 이 domain/compliance
를 직접 import 하면 파이프라인 DAG 역방향 위반 (architecture-check.sh 차단).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from domain.generation.model import Outline

# 의료법 패턴 타입: (카테고리 enum, 컴파일된 regex). enum 의 .value 만 사용해
# compliance import 없이 issue 메시지 생성 가능.
CompliancePatterns = list[tuple[object, "re.Pattern[str]"]]

# ── 길이 임계값 (CLAUDE.md "임계값/매직 넘버는 상수 모듈로 승격") ──
_TITLE_HARD_MIN = 20
_TITLE_RECOMMEND_MIN = 25
_TITLE_RECOMMEND_MAX = 35
_TITLE_HARD_MAX = 40

# ── 스팸/장식 표현 (도메인 독립 SEO 품질 규칙, compliance/rules.py 와 분리) ──
_TITLE_SPAM_LITERALS: tuple[str, ...] = (
    "필독",
    "초강추",
    "대박",
    "진짜",
    "핫이슈",
    "클릭",
    "긴급",
    "충격",
    "주목",
)

_TITLE_SPAM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"!{3,}"),  # 느낌표 3회 이상
    re.compile(r"\?{2,}"),  # 물음표 2회 이상
    re.compile(r"~{2,}"),  # 물결 2회 이상
    re.compile(r"[★☆♥♡✨⭐️🔥💯]"),  # 장식 특수문자/이모지 일부
)


@dataclass
class TitleIssue:
    """제목 검증 이슈 1건. severity=error 만 재생성 트리거."""

    field: str
    expected: str
    actual: str
    severity: Literal["error", "warning"] = "error"


class TitleValidationReport(BaseModel):
    """제목 검증 결과. error 1건이라도 있으면 passed=False."""

    passed: bool
    issues: list[dict[str, str]] = Field(default_factory=list)


def validate_title(
    outline: Outline,
    primary_keyword: str | None,
    *,
    compliance_patterns: CompliancePatterns | None = None,
    strict_compliance: bool = False,
) -> TitleValidationReport:
    """제목 4종 검증 후 보고서 반환.

    Args:
        outline: 검증 대상 (outline.title 만 사용).
        primary_keyword: 키워드 반복 검증의 기준. None/빈 문자열이면 반복 검증 스킵.
        compliance_patterns: application 레이어가 주입하는 (카테고리, 패턴) 리스트.
            None 이면 의료법 검증 스킵 (테스트 / 의료 외 도메인).
        strict_compliance: True 시 의료법 위반을 error 로, False 시 warning 으로 처리.
    """
    title = outline.title
    issues: list[TitleIssue] = []

    length_issue = _check_length(title)
    if length_issue is not None:
        issues.append(length_issue)

    repetition_issue = _check_keyword_repetition(title, primary_keyword)
    if repetition_issue is not None:
        issues.append(repetition_issue)

    issues.extend(_check_spam(title))
    if compliance_patterns is not None:
        issues.extend(_check_compliance(title, compliance_patterns, strict=strict_compliance))

    has_error = any(i.severity == "error" for i in issues)
    return TitleValidationReport(
        passed=not has_error,
        issues=[
            {
                "field": i.field,
                "expected": i.expected,
                "actual": i.actual,
                "severity": i.severity,
            }
            for i in issues
        ],
    )


def _check_length(title: str) -> TitleIssue | None:
    """길이 검증. 20~40 hard / 25~35 권장."""
    length = len(title)
    if length < _TITLE_HARD_MIN or length > _TITLE_HARD_MAX:
        return TitleIssue(
            field="length",
            expected=f"{_TITLE_HARD_MIN}~{_TITLE_HARD_MAX}자",
            actual=f"{length}자",
            severity="error",
        )
    if length < _TITLE_RECOMMEND_MIN or length > _TITLE_RECOMMEND_MAX:
        return TitleIssue(
            field="length",
            expected=f"{_TITLE_RECOMMEND_MIN}~{_TITLE_RECOMMEND_MAX}자 권장",
            actual=f"{length}자",
            severity="warning",
        )
    return None


def _normalize(text: str) -> str:
    """대소문자 lower + 연속 공백 단일화."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _check_keyword_repetition(title: str, primary_keyword: str | None) -> TitleIssue | None:
    """주 키워드 정확 매치 2회 이상 시 hard fail. 빈 키워드면 스킵."""
    if not primary_keyword or not primary_keyword.strip():
        return None
    norm_title = _normalize(title)
    norm_keyword = _normalize(primary_keyword)
    if not norm_keyword:
        return None
    occurrences = norm_title.count(norm_keyword)
    if occurrences >= 2:
        return TitleIssue(
            field="keyword_repetition",
            expected=f"주 키워드 '{primary_keyword}' 1회 이하",
            actual=f"{occurrences}회 등장",
            severity="error",
        )
    return None


def _check_spam(title: str) -> list[TitleIssue]:
    """스팸/장식 표현 검증. 항상 hard fail."""
    issues: list[TitleIssue] = []
    for literal in _TITLE_SPAM_LITERALS:
        if literal in title:
            issues.append(
                TitleIssue(
                    field="spam",
                    expected="스팸/장식 표현 없음",
                    actual=f"'{literal}' 포함",
                    severity="error",
                )
            )
    for pattern in _TITLE_SPAM_PATTERNS:
        match = pattern.search(title)
        if match:
            issues.append(
                TitleIssue(
                    field="spam",
                    expected="과도한 특수문자/장식 없음",
                    actual=f"'{match.group(0)}' 매치",
                    severity="error",
                )
            )
    return issues


def _check_compliance(
    title: str,
    patterns: CompliancePatterns,
    *,
    strict: bool,
) -> list[TitleIssue]:
    """의료법 금지 표현 검증. strict 토글로 severity 분기.

    patterns 는 application 레이어가 compliance.rules.get_all_patterns() 로 build
    하여 주입한다. domain/generation 이 domain/compliance 를 직접 import 하면
    파이프라인 DAG 역방향 위반.
    """
    severity: Literal["error", "warning"] = "error" if strict else "warning"
    issues: list[TitleIssue] = []
    for category, pattern in patterns:
        match = pattern.search(title)
        if match:
            category_name = getattr(category, "value", str(category))
            issues.append(
                TitleIssue(
                    field="compliance",
                    expected=f"의료법 카테고리 '{category_name}' 위반 없음",
                    actual=f"'{match.group(0)}' 매치",
                    severity=severity,
                )
            )
    return issues
