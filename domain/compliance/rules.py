"""의료광고법 위반 카테고리 + 정규식 규칙 — 단일 출처.

이 파일 외부에서 금지 표현 regex 를 정의하면 안 된다.
checker.py, fixer.py, prompt_builder.py 는 이 파일만 참조한다.

SPEC-SEO-TEXT.md §3 [8], SPEC-BRAND-CARD.md §7 참조.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

# ── 위반 카테고리 (SEO_STRICT: 8개) ──


class ViolationCategory(StrEnum):
    """의료광고법 8개 위반 카테고리."""

    ABSOLUTE_GUARANTEE = "absolute_guarantee"
    UNIQUE_SUPERLATIVE = "unique_superlative"
    DIRECT_COMPARISON = "direct_comparison"
    BEFORE_AFTER = "before_after"
    CURE_PROMISE = "cure_promise"
    PATIENT_TESTIMONIAL = "patient_testimonial"
    UNVERIFIED_CREDENTIAL = "unverified_credential"
    FIRST_PERSON_PROMOTION = "first_person_promotion"


# ── 컴플라이언스 정책 프로필 ──


class CompliancePolicy(StrEnum):
    """SEO 트랙(8개 전부) vs 브랜드 카드(법적 risk 만)."""

    SEO_STRICT = "seo_strict"
    BRAND_LENIENT = "brand_lenient"


# ── 규칙 정의 ──


@dataclass(frozen=True)
class Rule:
    """단일 위반 규칙."""

    category: ViolationCategory
    description: str
    patterns: list[str] = field(default_factory=list)
    safe_alternatives: list[str] = field(default_factory=list)


# ── SEO_STRICT 8개 규칙 ──

_ABSOLUTE_GUARANTEE = Rule(
    category=ViolationCategory.ABSOLUTE_GUARANTEE,
    description="효과 보장 표현 금지 (의료법 시행령 §23)",
    patterns=[
        r"100\s*%",
        r"완벽한\s*효과",
        r"반드시",
        r"보장",
        r"확실한\s*효과",
        r"틀림없",
    ],
    safe_alternatives=[
        "기대됩니다",
        "도움이 될 수 있습니다",
        "개인차가 있을 수 있습니다",
    ],
)

_UNIQUE_SUPERLATIVE = Rule(
    category=ViolationCategory.UNIQUE_SUPERLATIVE,
    description="비교/우위 표현 금지 (의료법 §56)",
    patterns=[
        r"최고",
        r"유일",
        r"1등",
        r"최상",
        r"최초",
        r"가장\s*좋은",
        r"독보적",
    ],
    safe_alternatives=["차별화된", "전문적인"],
)

_DIRECT_COMPARISON = Rule(
    category=ViolationCategory.DIRECT_COMPARISON,
    description="타 의료기관 직접 비교 금지 (§56)",
    patterns=[
        r".{1,10}병원보다",
        r"타\s*병원과\s*달리",
        r"다른\s*곳은",
        r"여타",
        r"타\s*의료기관",
    ],
    safe_alternatives=["비교 없이 자신의 강점만 서술"],
)

_BEFORE_AFTER = Rule(
    category=ViolationCategory.BEFORE_AFTER,
    description="전후 비교 표현 제한 (§56)",
    patterns=[
        r"시술\s*전후",
        r"[Bb]efore\s*/?\s*[Aa]fter",
        r"비포\s*애프터",
        r"전후\s*사진",
        r"완전히\s*달라",
    ],
    safe_alternatives=["변화", "개선", "관리 후 모습"],
)

_CURE_PROMISE = Rule(
    category=ViolationCategory.CURE_PROMISE,
    description="치료 효과 확정 표현 금지 (§56)",
    patterns=[
        r"완치",
        r"재발\s*없",
        r"평생\s*효과",
        r"영구적",
        r"근본\s*치료",
        r"확실히\s*낫",
    ],
    safe_alternatives=[
        "장기적 관리",
        "지속적 효과 기대",
        "개선이 기대됩니다",
    ],
)

_PATIENT_TESTIMONIAL = Rule(
    category=ViolationCategory.PATIENT_TESTIMONIAL,
    description="후기 내 특정 효과 수치 인용 제한 (§56)",
    patterns=[
        r"\d+\s*kg\s*빠졌",
        r"\d+\s*cm\s*줄었",
        r"완전\s*나았",
        r"효과\s*봤어요",
        r"후기\s*:.*효과",
    ],
    safe_alternatives=["일반화된 만족 표현"],
)

_UNVERIFIED_CREDENTIAL = Rule(
    category=ViolationCategory.UNVERIFIED_CREDENTIAL,
    description="미검증 인증/수상 표시 금지 (§56)",
    patterns=[
        r"세계\s*1위",
        r"[Bb]est\s*[Dd]octor",
        r"세계\s*최초",
        r"수상\s*경력",
        r"인증.*1위",
    ],
    safe_alternatives=["검증 가능한 자격만 기재"],
)

_FIRST_PERSON_PROMOTION = Rule(
    category=ViolationCategory.FIRST_PERSON_PROMOTION,
    description="1인칭 홍보/CTA 표현 금지",
    patterns=[
        r"저희\s*병원",
        r"우리\s*한의원",
        r"당사",
        r"저희가",
        r"예약하세요",
        r"전화주세요",
        r"상담\s*받으세요",
        r"방문해\s*주세요",
    ],
    safe_alternatives=["3인칭 서술"],
)


# ── 프로필별 규칙 매핑 ──

RULES: dict[CompliancePolicy, list[Rule]] = {
    CompliancePolicy.SEO_STRICT: [
        _ABSOLUTE_GUARANTEE,
        _UNIQUE_SUPERLATIVE,
        _DIRECT_COMPARISON,
        _BEFORE_AFTER,
        _CURE_PROMISE,
        _PATIENT_TESTIMONIAL,
        _UNVERIFIED_CREDENTIAL,
        _FIRST_PERSON_PROMOTION,
    ],
    CompliancePolicy.BRAND_LENIENT: [
        _ABSOLUTE_GUARANTEE,
        _UNIQUE_SUPERLATIVE,
        _DIRECT_COMPARISON,
        _BEFORE_AFTER,
        _CURE_PROMISE,
        _PATIENT_TESTIMONIAL,
        _UNVERIFIED_CREDENTIAL,
        # first_person_promotion 제외 — 브랜드 카드는 1인칭/CTA 허용
    ],
}


# ── 헬퍼 함수 ──


def get_rules(
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
) -> list[Rule]:
    """지정 정책의 규칙 목록을 반환한다."""
    return RULES[policy]


def get_all_patterns(
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
) -> list[tuple[ViolationCategory, re.Pattern[str]]]:
    """모든 규칙의 컴파일된 regex 목록을 반환한다.

    Returns:
        (카테고리, 컴파일된 패턴) 튜플 리스트.
    """
    result: list[tuple[ViolationCategory, re.Pattern[str]]] = []
    for rule in get_rules(policy):
        for pat_str in rule.patterns:
            compiled = re.compile(pat_str, re.IGNORECASE)
            result.append((rule.category, compiled))
    return result


def get_safe_alternatives(
    category: ViolationCategory,
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
) -> list[str]:
    """특정 카테고리의 안전 대체 표현을 반환한다."""
    for rule in get_rules(policy):
        if rule.category == category:
            return rule.safe_alternatives
    return []


def build_pre_generation_injection(
    policy: CompliancePolicy = CompliancePolicy.SEO_STRICT,
) -> str:
    """[6][7] 프롬프트에 주입할 의료법 사전 규칙 텍스트를 생성한다."""
    lines: list[str] = []
    for rule in get_rules(policy):
        examples = ", ".join(f'"{p}"' for p in rule.patterns[:3])
        lines.append(f"- {rule.description} (예: {examples})")
    return "\n".join(lines)


# ── post-edit-lint.sh 훅이 참조하는 FORBIDDEN_LITERALS ──
# rules.py 외부에서 금지 표현이 하드코딩되지 않도록 린트한다.

FORBIDDEN_LITERALS: list[str] = []
for _rule in RULES[CompliancePolicy.SEO_STRICT]:
    for _pat in _rule.patterns:
        # regex 메타문자를 제거해 순수 문자열만 추출한다.
        # 복잡한 패턴(예: .{1,10}병원보다)은 린트 대상에서 제외.
        cleaned = re.sub(r"[\\.*+?\[\]{}()|^$]", "", _pat)
        cleaned = cleaned.replace(r"\s", " ").strip()
        if len(cleaned) >= 2 and cleaned.isascii() is False:
            FORBIDDEN_LITERALS.append(cleaned)
