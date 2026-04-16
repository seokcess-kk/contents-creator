"""생성 원고 자동 품질 검증.

패턴 카드의 분석 범위와 생성 원고의 실측값을 비교하여
범위 이탈 항목을 경고로 보고한다. 파이프라인을 중단하지 않는다.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from domain.analysis.pattern_card import PatternCard

logger = logging.getLogger(__name__)


class QualityIssue(BaseModel):
    """품질 검증 단일 항목."""

    metric: str
    expected: str
    actual: str
    severity: str = "warning"  # warning | info


class QualityReport(BaseModel):
    """생성 원고 품질 검증 결과."""

    issues: list[QualityIssue] = Field(default_factory=list)
    passed: bool = True


def check_quality(
    content_md: str,
    pattern_card: PatternCard,
) -> QualityReport:
    """생성 원고가 패턴 카드 분석 범위 내인지 검증한다."""
    issues: list[QualityIssue] = []
    stats = pattern_card.stats

    text_only = re.sub(r"[#!\[\]()>*_\-]", "", content_md)
    total_chars = len(text_only.replace(" ", "").replace("\n", ""))

    _check_chars(total_chars, stats.chars.min, stats.chars.max, issues)
    _check_keyword_density(content_md, pattern_card.keyword, stats.keyword_density.avg, issues)
    _check_subtitle_count(content_md, stats.subtitles.avg, issues)

    passed = all(i.severity != "warning" for i in issues)
    report = QualityReport(issues=issues, passed=passed)

    for issue in issues:
        logger.warning(
            "quality.%s expected=%s actual=%s",
            issue.metric,
            issue.expected,
            issue.actual,
        )
    return report


def _check_chars(
    actual: int,
    min_chars: float,
    max_chars: float,
    issues: list[QualityIssue],
) -> None:
    """글자수 범위 검증 (±20% 허용)."""
    lower = min_chars * 0.8
    upper = max_chars * 1.2
    if actual < lower or actual > upper:
        issues.append(
            QualityIssue(
                metric="total_chars",
                expected=f"{min_chars:.0f}~{max_chars:.0f}",
                actual=str(actual),
            )
        )


def _check_keyword_density(
    content: str,
    keyword: str,
    target_density: float,
    issues: list[QualityIssue],
) -> None:
    """키워드 밀도 검증 (목표의 50~200% 범위)."""
    if target_density <= 0:
        return
    kw_count = content.count(keyword)
    if " " in keyword:
        kw_count = max(kw_count, content.replace(" ", "").count(keyword.replace(" ", "")))
    actual_density = kw_count / max(len(content), 1)

    if actual_density < target_density * 0.5 or actual_density > target_density * 2.0:
        issues.append(
            QualityIssue(
                metric="keyword_density",
                expected=f"{target_density:.4f}",
                actual=f"{actual_density:.4f}",
                severity="info" if actual_density > 0 else "warning",
            )
        )


def _check_subtitle_count(
    content: str,
    target_avg: float,
    issues: list[QualityIssue],
) -> None:
    """소제목 수 검증. 상위글 평균이 0이면 스킵."""
    if target_avg <= 0:
        return
    actual = content.count("## ")
    if abs(actual - target_avg) > max(target_avg, 3):
        issues.append(
            QualityIssue(
                metric="subtitle_count",
                expected=f"avg {target_avg:.1f}",
                actual=str(actual),
                severity="info",
            )
        )
