"""Compliance 도메인 모델 — ComplianceReport, Violation, ChangelogEntry.

SPEC-SEO-TEXT.md §3 [8] 검증 결과 구조.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Violation(BaseModel):
    """단일 의료법 위반 항목."""

    category: str = Field(description="ViolationCategory enum 값")
    text_snippet: str = Field(description="위반이 감지된 텍스트 발췌")
    section_index: int | None = Field(
        default=None, description="위반이 발생한 섹션 인덱스 (본문 위반 시)"
    )
    severity: Literal["low", "medium", "high"] = Field(description="위반 심각도")
    reason: str = Field(description="위반 사유 설명")


class ChangelogEntry(BaseModel):
    """수정 이력 항목."""

    section: int | None = Field(default=None, description="수정된 섹션 인덱스")
    before: str = Field(description="수정 전 텍스트")
    after: str = Field(description="수정 후 텍스트")
    rule: str = Field(description="적용된 규칙 ID")
    reason: str = Field(description="수정 사유")


class ComplianceReport(BaseModel):
    """의료법 검증 최종 리포트.

    검증 실패를 raise 가 아닌 `passed=False` 로 처리한다.
    """

    passed: bool = Field(description="최종 통과 여부")
    iterations: int = Field(default=0, description="검증-수정 반복 횟수")
    violations: list[Violation] = Field(default_factory=list, description="잔존 위반 목록")
    changelog: list[ChangelogEntry] = Field(default_factory=list, description="수정 이력")
    final_text: str = Field(default="", description="최종 텍스트")
