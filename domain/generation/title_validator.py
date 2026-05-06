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

import logging
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from domain.generation.model import Outline

logger = logging.getLogger(__name__)

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


# Polish P4: kiwipiepy 형태소 매칭 — 모듈 단위 singleton 캐시 (worker 당 1회 시동).
# Cold start 측정 (Step 4.0): import 0.09s + Kiwi() 0.74s + first analyze 1.21s ≈ 2.04s.
# 두 번째 호출부터는 0.000s.
_kiwi_instance: object | None = None
_kiwi_unavailable: bool = False  # ImportError 후 재시도 안 함


def _get_kiwi() -> object | None:
    """Kiwi 인스턴스 lazy 생성. ImportError 시 None 반환 (fallback path)."""
    global _kiwi_instance, _kiwi_unavailable
    if _kiwi_unavailable:
        return None
    if _kiwi_instance is not None:
        return _kiwi_instance
    try:
        from kiwipiepy import Kiwi  # type: ignore[import-not-found]

        _kiwi_instance = Kiwi()
        return _kiwi_instance
    except ImportError:
        _kiwi_unavailable = True
        logger.warning(
            "kiwipiepy unavailable — title morpheme matching disabled, falling back to exact"
        )
        return None


def _extract_nouns(kiwi: object, text: str) -> set[str]:
    """Kiwi 로 명사 set 추출 (NN* 태그)."""
    result = kiwi.analyze(text)  # type: ignore[attr-defined]
    if not result or not result[0]:
        return set()
    tokens = result[0][0]
    return {t.form for t in tokens if t.tag.startswith("NN")}


def _normalize_morpheme(text: str, keyword: str, *, threshold: float = 0.7) -> bool:
    """text 안에 keyword 의 명사 set 이 threshold (default 0.7) 이상 포함되면 True.

    분모 = keyword 명사 set 크기 (recall 기준).
    "다이어트한의원" vs "다이어트 한의원 추천" → 매칭 (keyword 명사 모두 포함).

    kiwipiepy 가 "한의원" 을 컨텍스트에 따라 ["한의원"] 또는 ["의원"] 으로 분리하는
    모호성을 회피하기 위해, keyword 명사가 **title 원문에 substring 으로 존재** 하는지
    검사 (set 교집합 대신). 이 방식이 형태소 분리 결과 의존성을 제거하고 더 강건.

    kiwipiepy 미사용 시 False (degrade).
    """
    if not text or not keyword:
        return False
    kiwi = _get_kiwi()
    if kiwi is None:
        return False
    keyword_nouns = _extract_nouns(kiwi, keyword)
    if not keyword_nouns:
        return False
    title_lower = text.lower()
    matched = sum(1 for noun in keyword_nouns if noun.lower() in title_lower)
    recall = matched / len(keyword_nouns)
    return recall >= threshold


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
