"""의료광고법 위반 규칙 엔진.

8개 위반 카테고리 + 정규식 패턴 매칭.
1차 방어(규칙 기반 스캔)의 핵심 모듈.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 금지 표현 파일 경로
_PROHIBITED_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude"
    / "skills"
    / "medical-compliance"
    / "references"
    / "prohibited-expressions.md"
)


@dataclass
class ProhibitedPattern:
    """금지 표현 패턴."""

    pattern: re.Pattern[str]
    category: str
    severity: str  # CRITICAL / WARNING
    suggestion: str = ""
    law_reference: str = "의료법 제56조"


# === 8개 위반 카테고리 ===

CATEGORIES = {
    "과대광고": "치료 효과를 보장하거나 과장",
    "비교광고": "다른 의료기관과 비교하거나 최상급 표현",
    "체험기오용": "특정 환자 사례를 일반화",
    "미인증시술": "식약처 미인증 의료기기·시술",
    "가격오인": "할인율·이벤트로 가격 오인 유도",
    "전후사진": "시술 전후 사진 부적절 사용",
    "자격과장": "의료진 자격·경력 과장",
    "보장표현": "결과를 보장하는 절대적 표현",
}


def _build_patterns() -> list[ProhibitedPattern]:
    """금지 표현 패턴 목록을 구성한다."""
    patterns: list[ProhibitedPattern] = []

    # 과대광고 (CRITICAL)
    for expr in [
        r"100\s*%\s*완치",
        r"확실한\s*효과",
        r"반드시\s*좋아",
        r"놀라운\s*결과",
        r"획기적인\s*치료",
        r"완벽한\s*시술",
        r"기적의\s*치료",
        r"탁월한\s*효과",
    ]:
        patterns.append(
            ProhibitedPattern(
                pattern=re.compile(expr, re.IGNORECASE),
                category="과대광고",
                severity="CRITICAL",
                suggestion="개인차가 있을 수 있으며, 전문의 상담을 권장합니다",
                law_reference="의료법 제56조 제2항 제1호",
            )
        )

    # 과대광고 - 패턴 매칭
    patterns.append(
        ProhibitedPattern(
            pattern=re.compile(r"\d+\s*%\s*(완치|치료|개선|효과)"),
            category="과대광고",
            severity="CRITICAL",
            suggestion="구체적 수치를 사용한 효과 보장 표현을 제거하세요",
        )
    )
    patterns.append(
        ProhibitedPattern(
            pattern=re.compile(r"(반드시|무조건|확실히)\s*(좋아|나아|개선|완치|효과)"),
            category="과대광고",
            severity="CRITICAL",
            suggestion="절대적 표현 대신 '최선을 다하겠습니다'로 대체하세요",
        )
    )

    # 비교광고 (CRITICAL)
    for expr in ["최고의", "유일한", "가장\\s*많은", "국내\\s*1위", "독보적인"]:
        patterns.append(
            ProhibitedPattern(
                pattern=re.compile(expr, re.IGNORECASE),
                category="비교광고",
                severity="CRITICAL",
                suggestion="'풍부한 경험', '다양한 사례'로 대체하세요",
                law_reference="의료법 제56조 제2항 제2호",
            )
        )
    patterns.append(
        ProhibitedPattern(
            pattern=re.compile(r"(최고|최상|최첨단|세계적|국내\s*유일)\s*(기술|시술|치료|장비)"),
            category="비교광고",
            severity="CRITICAL",
        )
    )

    # 보장 표현 (CRITICAL)
    for expr in ["무조건", "걱정\\s*없는", "안전\\s*보장", "부작용\\s*없는", "통증\\s*제로"]:
        patterns.append(
            ProhibitedPattern(
                pattern=re.compile(expr, re.IGNORECASE),
                category="보장표현",
                severity="CRITICAL",
                suggestion="절대적 보장 표현을 제거하세요",
                law_reference="의료법 제56조 제2항 제1호",
            )
        )

    # 가격 오인 (WARNING)
    patterns.append(
        ProhibitedPattern(
            pattern=re.compile(r"\d+\s*%\s*할인"),
            category="가격오인",
            severity="WARNING",
            suggestion="근거 없는 할인율 표시를 제거하세요",
        )
    )
    for expr in ["무료\\s*시술", "특가\\s*이벤트", "파격\\s*할인"]:
        patterns.append(
            ProhibitedPattern(
                pattern=re.compile(expr, re.IGNORECASE),
                category="가격오인",
                severity="WARNING",
            )
        )

    return patterns


# 모듈 레벨 캐시
_PATTERNS: list[ProhibitedPattern] | None = None


def get_patterns() -> list[ProhibitedPattern]:
    """금지 표현 패턴 목록을 반환한다 (캐시)."""
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = _build_patterns()
    return _PATTERNS


@dataclass
class RuleScanResult:
    """규칙 기반 스캔 결과."""

    violations: list[dict[str, str]] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.violations)


def scan_text(text: str, source: str = "text") -> RuleScanResult:
    """텍스트에서 금지 표현을 규칙 기반으로 스캔한다.

    Args:
        text: 검사할 텍스트
        source: 출처 식별자 (예: "seo_text", "title")

    Returns:
        RuleScanResult
    """
    result = RuleScanResult()
    lines = text.split("\n")

    for pattern_obj in get_patterns():
        for line_no, line in enumerate(lines, start=1):
            for match in pattern_obj.pattern.finditer(line):
                result.violations.append(
                    {
                        "category": pattern_obj.category,
                        "severity": pattern_obj.severity,
                        "location": f"{source}:L{line_no}",
                        "original": match.group(),
                        "suggestion": pattern_obj.suggestion,
                        "law_reference": pattern_obj.law_reference,
                    }
                )

    return result


# Disclaimer 템플릿
DISCLAIMER_TEMPLATE = (
    "본 콘텐츠는 건강 정보 제공을 목적으로 작성되었으며, "
    "의학적 진단이나 치료를 대체할 수 없습니다. "
    "증상이 있는 경우 반드시 전문의와 상담하시기 바랍니다."
)


def check_disclaimer(text: str) -> bool:
    """Disclaimer가 텍스트에 포함되어 있는지 확인한다."""
    key_phrases = ["건강 정보 제공", "의학적 진단", "전문의와 상담"]
    return all(phrase in text for phrase in key_phrases)
