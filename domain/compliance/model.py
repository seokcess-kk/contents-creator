"""의료법 컴플라이언스 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Violation(BaseModel):
    """개별 위반 항목."""

    category: str  # 8개 카테고리 중 하나
    severity: str  # CRITICAL / WARNING / INFO
    location: str = ""  # 파일:라인 또는 섹션명
    original: str = ""  # 위반 원문
    suggestion: str = ""  # 수정 제안
    law_reference: str = ""  # 법적 근거


class ComplianceReport(BaseModel):
    """의료법 검증 보고서."""

    id: str = ""
    content_id: str = ""
    verdict: str = "pending"  # pass / fix / reject
    violations: list[Violation] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=lambda: {"critical": 0, "warning": 0, "info": 0})
    disclaimer_check: bool = False
    review_round: int = 1
    reviewed_at: str = ""

    def has_critical(self) -> bool:
        return self.stats.get("critical", 0) > 0

    def compute_verdict(self) -> str:
        """위반 통계를 기반으로 판정을 계산한다."""
        if self.stats.get("critical", 0) > 0:
            return "fix"
        if self.stats.get("warning", 0) > 0:
            return "fix"
        return "pass"
