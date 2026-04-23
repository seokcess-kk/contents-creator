"""생성 원고 자동 품질 검증.

패턴 카드의 분석 범위와 생성 원고의 실측값을 비교하여
범위 이탈 항목을 경고로 보고한다. 파이프라인을 중단하지 않는다.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline
from domain.image_generation.model import ImageGenerationResult

logger = logging.getLogger(__name__)

_IMG_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*image_\d+[^)]*\)", re.IGNORECASE)
_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


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


def check_image_integrity(
    outline: Outline,
    image_result: ImageGenerationResult | None,
    content_md: str,
    content_html: str | None = None,
) -> list[QualityIssue]:
    """이미지 무결성 3자 비교: outline 선언 vs 생성 vs 렌더링.

    compliance가 outline.image_prompts를 줄였을 수 있으므로 declared 는
    post-compliance 시점 outline 기준.

    - declared = outline.image_prompts 길이
    - generated = image_result.generated 길이 (실제 파일 있음)
    - skipped = image_result.skipped 길이 (budget/api_error/compliance)
    - md_markers = content_md의 `[이미지 N: ...]` 마커 수
    - html_imgs = content_html의 `<img>` 태그 수 (제공 시)

    정상 조건:
        declared = generated + skipped
        md_markers = generated
        html_imgs = generated  (html 제공 시)
    """
    issues: list[QualityIssue] = []

    declared = len(outline.image_prompts)
    generated = len(image_result.generated) if image_result else 0
    skipped = len(image_result.skipped) if image_result else 0
    md_markers = len(_IMG_MD_RE.findall(content_md))

    if image_result is not None and declared != generated + skipped:
        issues.append(
            QualityIssue(
                metric="image_accounting",
                expected=f"declared={declared} = generated+skipped",
                actual=f"generated={generated}, skipped={skipped}",
                severity="warning",
            )
        )

    if md_markers != generated:
        issues.append(
            QualityIssue(
                metric="image_md_markers",
                expected=str(generated),
                actual=str(md_markers),
                severity="warning",
            )
        )

    if content_html is not None:
        html_imgs = len(_HTML_IMG_RE.findall(content_html))
        if html_imgs != generated:
            issues.append(
                QualityIssue(
                    metric="image_html_tags",
                    expected=str(generated),
                    actual=str(html_imgs),
                    severity="warning",
                )
            )

    for issue in issues:
        logger.warning(
            "quality.%s expected=%s actual=%s",
            issue.metric,
            issue.expected,
            issue.actual,
        )
    return issues
