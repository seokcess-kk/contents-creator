"""Application 레이어 전용 Pydantic 모델.

도메인 모델 (`PatternCard`, `Outline` 등) 은 `domain/*/model.py` 에 있고,
이 파일은 그것들을 '참조'만 한다. 도메인 모델을 여기서 재정의 금지.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    """단일 파이프라인 단계 실행 결과."""

    name: str
    status: StageStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class PipelineResult(BaseModel):
    """`run_pipeline` 의 반환 타입. 전체 8단계 실행 결과."""

    status: StageStatus
    keyword: str
    slug: str
    output_path: Path | None = None
    stages: list[StageResult] = Field(default_factory=list)
    error: str | None = None


class AnalyzeResult(BaseModel):
    """`run_analyze_only` 의 반환 타입. [1]~[5] 분석만 실행."""

    status: StageStatus
    keyword: str
    slug: str
    analyzed_count: int = 0
    pattern_card_path: Path | None = None
    stages: list[StageResult] = Field(default_factory=list)
    error: str | None = None


class GenerateResult(BaseModel):
    """`run_generate_only` 의 반환 타입. [6]~[9] 생성만 실행."""

    status: StageStatus
    keyword: str
    slug: str
    seo_content_md_path: Path | None = None
    seo_content_html_path: Path | None = None
    outline_md_path: Path | None = None
    compliance_passed: bool | None = None
    compliance_iterations: int | None = None
    stages: list[StageResult] = Field(default_factory=list)
    error: str | None = None


class ValidateResult(BaseModel):
    """`run_validate_only` 의 반환 타입. [8] 의료법 검증만 실행."""

    status: StageStatus
    content_path: Path
    passed: bool | None = None
    iterations: int | None = None
    violations_count: int = 0
    error: str | None = None
