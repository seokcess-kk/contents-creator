"""FastAPI 요청/응답 스키마.

application.models 의 Pydantic 모델을 API 응답에 직접 사용하되,
Path 필드를 문자열로 직렬화하기 위한 래퍼와 요청 바디 모델을 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ── 요청 ──


class PipelineRequest(BaseModel):
    keyword: str
    generate_images: bool = True
    regenerate_images: bool = False
    force_analyze: bool = False
    pattern_card_path: str | None = None


class AnalyzeRequest(BaseModel):
    keyword: str


class GenerateRequest(BaseModel):
    keyword: str | None = None
    pattern_card_path: str | None = None
    generate_images: bool = True
    regenerate_images: bool = False


class ValidateRequest(BaseModel):
    content_path: str


# ── 응답 ──


class JobResponse(BaseModel):
    id: str
    type: str
    keyword: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    params: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: list[dict[str, Any]] = []


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str = "pending"
