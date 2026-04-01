"""의료법 검증기. 1차(규칙) + 2차(LLM 판단) 검증을 수행한다."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from domain.common import llm_client
from domain.compliance.model import ComplianceReport, Violation
from domain.compliance.rules import (
    DISCLAIMER_TEMPLATE,
    check_disclaimer,
    scan_text,
)

logger = logging.getLogger(__name__)

LLM_CHECK_SYSTEM = """\
당신은 대한민국 의료광고법(의료법 제56조) 전문 검토관입니다.
텍스트에서 의료광고법 위반 가능성이 있는 표현을 찾아주세요.
규칙 기반으로 잡히지 않는 우회 표현, 문맥상 위반을 판단합니다.

8개 위반 카테고리:
과대광고, 비교광고, 체험기오용, 미인증시술, 가격오인, 전후사진, 자격과장, 보장표현

반드시 JSON만 반환하세요.
"""

LLM_CHECK_PROMPT = """\
아래 텍스트를 의료광고법 기준으로 검토하세요.
규칙 기반으로 이미 발견된 위반은 제외하고, 추가로 문맥상 위반되는 표현만 찾아주세요.

[이미 발견된 위반]
{existing_violations}

[검토 대상 텍스트]
{text}

추가 위반이 있으면 아래 JSON 형태로 반환하세요. 없으면 빈 배열 반환:
[
  {{
    "category": "카테고리명",
    "severity": "CRITICAL/WARNING/INFO",
    "location": "위치 설명",
    "original": "위반 원문",
    "suggestion": "수정 제안",
    "law_reference": "법적 근거"
  }}
]
"""


def check_compliance(
    text: str,
    *,
    source: str = "seo_text",
    use_llm: bool = True,
    review_round: int = 1,
) -> ComplianceReport:
    """텍스트의 의료광고법 준수 여부를 검증한다.

    1차 방어: 규칙 기반 정규식 매칭
    2차 방어: LLM 문맥 판단 (선택)

    Args:
        text: 검증할 텍스트
        source: 출처 식별자
        use_llm: LLM 2차 검증 사용 여부
        review_round: 검증 라운드 (1~3)

    Returns:
        ComplianceReport
    """
    violations: list[Violation] = []

    # 1차 방어: 규칙 기반 스캔
    rule_result = scan_text(text, source=source)
    for v in rule_result.violations:
        violations.append(Violation(**v))

    logger.info("1차 방어(규칙): %d건 발견", rule_result.count)

    # 2차 방어: LLM 문맥 판단
    if use_llm:
        llm_violations = _llm_check(text, violations)
        violations.extend(llm_violations)
        logger.info("2차 방어(LLM): %d건 추가 발견", len(llm_violations))

    # 통계 계산
    stats = {"critical": 0, "warning": 0, "info": 0}
    for v in violations:
        key = v.severity.lower()
        if key in stats:
            stats[key] += 1

    # Disclaimer 확인
    has_disclaimer = check_disclaimer(text)

    # 보고서 생성
    report = ComplianceReport(
        violations=violations,
        stats=stats,
        disclaimer_check=has_disclaimer,
        review_round=review_round,
        reviewed_at=datetime.now(tz=UTC).isoformat(),
    )
    report.verdict = report.compute_verdict()

    if not has_disclaimer:
        logger.warning("Disclaimer가 포함되어 있지 않습니다.")

    logger.info(
        "검증 완료: verdict=%s (CRITICAL:%d, WARNING:%d, INFO:%d)",
        report.verdict,
        stats["critical"],
        stats["warning"],
        stats["info"],
    )
    return report


def _llm_check(text: str, existing: list[Violation]) -> list[Violation]:
    """LLM으로 문맥 기반 추가 위반을 탐지한다."""
    existing_str = "\n".join(f"- [{v.category}] {v.original}" for v in existing) or "(없음)"

    prompt = LLM_CHECK_PROMPT.format(
        existing_violations=existing_str,
        text=text[:5000],  # 컨텍스트 제한
    )

    try:
        response = llm_client.chat_json(
            prompt,
            system=LLM_CHECK_SYSTEM,
            max_tokens=2048,
        )
        data = json.loads(response)
        if not isinstance(data, list):
            return []

        return [
            Violation(
                category=item.get("category", "기타"),
                severity=item.get("severity", "WARNING"),
                location=item.get("location", ""),
                original=item.get("original", ""),
                suggestion=item.get("suggestion", ""),
                law_reference=item.get("law_reference", ""),
            )
            for item in data
        ]
    except Exception as e:
        logger.error("LLM 검증 실패: %s (규칙 기반 결과만 사용)", e)
        return []


def get_disclaimer() -> str:
    """Disclaimer 텍스트를 반환한다."""
    return DISCLAIMER_TEMPLATE
