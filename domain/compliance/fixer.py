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

핵심 원칙:
1. 위반 표현을 제거하되, 수정 과정에서 새로운 위반 표현을 절대 만들지 마세요.
2. 아래 표현은 수정문에서도 사용 금지입니다:
   - 만족/경험 일반화: "많은 분들이 ~", "~를 경험하고 계십니다", "~변화를 경험", "~를 느끼는 경우"
   - 결과 단정: "~될 것입니다", "~효과를 보실 수 있습니다"
   - 과대 수식어: "근본적인", "최적의", "성공적인", "정확히", "완벽한", "특별한"
   - 체험기 형식: 치료 과정이나 변화를 시간순으로 서술하는 모든 표현
   - 비교 우위: "~중에서도 ~이 특별한 이유", "다른 곳과 달리"
3. 안전한 대체 표현을 사용하세요:
   - "도움이 될 수 있습니다", "개인차가 있을 수 있습니다"
   - "적합한", "체계적인", "개선에 도움을 줄 수 있습니다"
4. 위반 문장을 깔끔하게 고칠 수 없으면, 통째로 삭제하세요. 어색한 대체보다 삭제가 낫습니다.
5. 수정 후 전체 텍스트를 다시 읽고, 새 위반이 없는지 자체 검토하세요.

원문의 의미와 톤을 최대한 유지하면서 위반만 제거합니다.

구조 보존 (절대 삭제/변경 금지):
- # 제목, ## 소제목, ### 소소제목 (마크다운 헤딩)
- <!-- SECTION:... --> 디렉티브
- [이미지: ...] 플레이스홀더
- > 인용문 형식
- **볼드** 강조

위반 표현만 수정하고, 위 구조 요소는 반드시 그대로 유지하세요.
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

        # CRITICAL 0건이면 WARNING만으로는 수정하지 않음 (구조 파괴 방지)
        critical_count = current_report.stats.get("critical", 0)
        if critical_count == 0:
            logger.info("CRITICAL 0건, WARNING만 잔존 → 수정 스킵")
            current_report.verdict = "fix"
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
