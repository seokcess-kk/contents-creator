"""의료법 위반 자동 수정 + 재검증 루프.

3차 방어: 위반 발견 시 수정안 적용 → 재검증 (최대 3회).
"""

from __future__ import annotations

import logging

from domain.common import llm_client
from domain.compliance.checker import check_compliance
from domain.compliance.model import ComplianceReport

logger = logging.getLogger(__name__)

MAX_FIX_ROUNDS = 5

FIX_SYSTEM = """\
당신은 의료광고법 준수 전문 에디터입니다.
위반 표현을 법적으로 안전한 표현으로 수정하세요.
원문의 의미와 톤을 최대한 유지하면서 위반만 제거합니다.
수정된 전체 텍스트를 반환하세요. JSON이 아닌 일반 텍스트로 반환.
"""

FIX_PROMPT = """\
아래 텍스트에서 의료광고법 위반 표현을 수정해 주세요.

[위반 목록]
{violations}

[원문]
{text}

위반 표현만 수정하고, 나머지는 그대로 유지한 전체 텍스트를 반환하세요.
"""


def fix_and_verify(
    text: str,
    report: ComplianceReport,
    *,
    use_llm_check: bool = True,
) -> tuple[str, ComplianceReport]:
    """위반을 수정하고 재검증한다.

    최대 MAX_FIX_ROUNDS까지 수정→재검증 루프를 반복한다.

    Args:
        text: 원본 텍스트
        report: 초기 검증 보고서
        use_llm_check: 재검증 시 LLM 사용 여부

    Returns:
        (수정된 텍스트, 최종 검증 보고서) 튜플
    """
    current_text = text
    current_report = report

    for round_num in range(2, MAX_FIX_ROUNDS + 1):
        if current_report.verdict == "pass":
            break

        logger.info("수정 라운드 %d 시작 (%d건 위반)", round_num, len(current_report.violations))

        # 수정 시도
        current_text = _apply_fixes(current_text, current_report)

        # 재검증
        current_report = check_compliance(
            current_text,
            use_llm=use_llm_check,
            review_round=round_num,
        )

        if current_report.verdict == "pass":
            logger.info("수정 라운드 %d: PASS", round_num)
            break

        logger.info(
            "수정 라운드 %d: %s (잔여 CRITICAL:%d)",
            round_num,
            current_report.verdict,
            current_report.stats.get("critical", 0),
        )

    if current_report.verdict != "pass" and current_report.review_round >= MAX_FIX_ROUNDS:
        critical_count = current_report.stats.get("critical", 0)
        if critical_count > 0:
            logger.warning("최대 수정 라운드 도달. CRITICAL %d건 잔존 → reject.", critical_count)
            current_report.verdict = "reject"
        else:
            logger.warning("최대 수정 라운드 도달. WARNING만 잔존 → 수동 검토 권장.")
            current_report.verdict = "fix"

    return current_text, current_report


def _apply_fixes(text: str, report: ComplianceReport) -> str:
    """LLM을 사용하여 위반 표현을 수정한다."""
    violations_str = "\n".join(
        f'- [{v.severity}] {v.category}: "{v.original}" → 제안: {v.suggestion}'
        for v in report.violations
    )

    prompt = FIX_PROMPT.format(violations=violations_str, text=text)

    try:
        fixed = llm_client.chat(
            prompt,
            system=FIX_SYSTEM,
            max_tokens=4096,
            temperature=0.3,
        )
        return fixed.strip()
    except Exception as e:
        logger.error("LLM 수정 실패: %s (원문 유지)", e)
        return text
