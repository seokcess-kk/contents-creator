"""키워드 배치 운영 Pydantic 모델. SPEC-BATCH.md §5 참조."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 상태 머신 (Phase 1 단순). Phase 2 부터 analyzing/ready_to_generate/generating 활성.
BatchStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
ItemStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "needs_review",
    "failed",
    "skipped",
    # Phase 2 점진 활성:
    "analyzing",
    "ready_to_generate",
    "generating",
    # Phase 2 PR3 — 발행 준비 상태 (succeeded 의미 분리).
    # generate/pipeline 의 compliance_passed=True 시 자동 마킹 + 검수 승인 시 needs_review 에서 전환.
    "ready_to_publish",
]
Operation = Literal["analyze", "generate", "pipeline"]
Mode = Literal["now", "overnight", "auto"]
ClusterRole = Literal["primary", "member"]
ReviewStatus = Literal["pending", "approved", "rejected", "needs_fix"]


class KeywordBatch(BaseModel):
    """CSV 업로드 단위 메타. SPEC-BATCH.md §4 keyword_batches 매핑."""

    id: str | None = None
    name: str | None = None
    mode: Mode = "now"
    status: BatchStatus = "queued"
    total_count: int = Field(ge=0)
    succeeded_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    needs_review_count: int = Field(default=0, ge=0)
    # Phase 2 PR3 — 발행 준비 카운터. DB 컬럼 미반영, count_items_by_status 가 매번 재집계.
    ready_to_publish_count: int = Field(default=0, ge=0)
    estimated_cost_usd: float = 0
    # Phase 2 사전 필터 임계값
    min_search_volume: int | None = None
    max_difficulty: str | None = None
    cluster_dedupe: bool = True
    # Phase 4 자동 발행 (opt-in)
    auto_publish_enabled: bool = False
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class KeywordBatchItem(BaseModel):
    """배치의 키워드 단위 row + 진행 상태."""

    id: str | None = None
    batch_id: str

    # 입력 (CSV)
    keyword: str = Field(min_length=1)
    operation: Operation = "analyze"
    mode: Mode = "now"
    priority: int = Field(default=5, ge=1, le=9)
    cluster_id: str | None = None
    cluster_role: ClusterRole = "member"
    intent: str | None = None
    region: str | None = None
    brand_id: str | None = None
    target_url: str | None = None
    memo: str | None = None

    # 실행 메타
    status: ItemStatus = "queued"
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=2, ge=0)
    job_id: str | None = None  # Phase 1 link 키 (FK 회수 보강 전)
    error: str | None = None
    estimated_cost_usd: float = 0

    # 분석 결과 (Phase 2, nullable)
    search_volume: int | None = None
    difficulty_grade: str | None = None

    # 생성 결과 (nullable, Phase 2 보강)
    pattern_card_id: str | None = None
    generated_content_id: str | None = None
    quality_score: float | None = None
    compliance_passed: bool | None = None
    # Phase B14 — 위반된 의료법 카테고리 리스트 (검수 큐 tooltip). DB jsonb 컬럼.
    compliance_violations: list[str] = Field(default_factory=list)

    # 검수 (Phase 2)
    review_status: ReviewStatus = "pending"
    reviewer: str | None = None
    reviewed_at: datetime | None = None

    # 발행 (Phase 4)
    publication_id: str | None = None
    published_at: datetime | None = None

    # 시점
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class BatchEnqueueResult(BaseModel):
    """CSV upload 결과 — created/skipped/failed 분류."""

    batch_id: str
    total: int = Field(ge=0)
    created: int = Field(ge=0)
    skipped: list[dict[str, str]] = Field(default_factory=list)  # {row, reason, keyword}
    failed: list[dict[str, str]] = Field(default_factory=list)


class CsvParseError(Exception):
    """CSV 파싱·검증 실패."""


class NotSupportedYetError(Exception):
    """Phase 1 에서 지원 안 하는 모드 (overnight/auto). API 가 400 으로 변환."""
