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
    """`run_generate_only` 의 반환 타입. [6]~[10] 생성 + 이미지 + 조립 실행."""

    status: StageStatus
    keyword: str
    slug: str
    seo_content_md_path: Path | None = None
    seo_content_html_path: Path | None = None
    outline_md_path: Path | None = None
    images_dir: Path | None = None
    images_generated: int = 0
    images_skipped: int = 0
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


class BrandCardResult(BaseModel):
    """브랜드 카드 트랙 단독 실행 결과. SPEC-BRAND-CARD §15 진입점 [B1]~[B5] 또는 [B7]~[B12].

    `RenderedCardSet` 은 도메인 모델이라 본 application 모델은 status/error/stages 메타만
    추가로 보유하고 도메인 결과는 `manifest_path` 등 경로로 참조한다.
    """

    status: StageStatus
    brand_id: str
    keyword: str
    reuse_group_id: str | None = None
    plan_count: int = 0
    rendered_count: int = 0
    manifest_path: Path | None = None
    cards_dir: Path | None = None
    stages: list[StageResult] = Field(default_factory=list)
    error: str | None = None


class PackageResult(BaseModel):
    """`run_full_package` 의 반환 타입. SEO 트랙 + 브랜드 카드 트랙 합류 결과.

    SPEC-BRAND-CARD §5 합류점 — SEO 파이프라인과 브랜드 카드 트랙을 병렬 실행 후 결과를
    한 묶음으로 보고한다. 둘 중 한쪽이 실패해도 다른 쪽은 가능한 만큼 진행된 결과를 보존.
    """

    status: StageStatus
    keyword: str
    brand_id: str
    slug: str
    seo_result: PipelineResult | None = None
    brand_card_result: BrandCardResult | None = None
    error: str | None = None
