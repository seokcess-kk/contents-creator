"""FastAPI 요청/응답 스키마.

application.models 의 Pydantic 모델을 API 응답에 직접 사용하되,
Path 필드를 문자열로 직렬화하기 위한 래퍼와 요청 바디 모델을 정의한다.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

# 사용자가 제공하는 파일 경로는 반드시 이 루트 하위여야 한다.
# orchestrator 가 Path.read_text 로 직접 읽으므로, 경로 화이트리스트 없이는
# 인증만 통과하면 프로젝트 밖 임의 파일 (/etc/passwd 등) 을 읽게 된다.
_ALLOWED_PATH_ROOT = Path("output").resolve()


def _validate_under_output(value: str | None) -> str | None:
    """문자열 경로가 output/ 하위인지 검증. 아니면 ValueError."""
    if value is None:
        return None
    if not value.strip():
        raise ValueError("path must not be empty")
    try:
        resolved = Path(value).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"invalid path: {exc}") from exc
    try:
        resolved.relative_to(_ALLOWED_PATH_ROOT)
    except ValueError as exc:
        raise ValueError(f"path must be under '{_ALLOWED_PATH_ROOT}' (got '{resolved}')") from exc
    return str(resolved)


# ── 요청 ──


class PipelineRequest(BaseModel):
    keyword: str
    generate_images: bool = True
    regenerate_images: bool = False
    force_analyze: bool = False
    pattern_card_path: str | None = None

    @field_validator("pattern_card_path")
    @classmethod
    def _check_pattern_card_path(cls, v: str | None) -> str | None:
        return _validate_under_output(v)


class AnalyzeRequest(BaseModel):
    keyword: str


class GenerateRequest(BaseModel):
    keyword: str | None = None
    pattern_card_path: str | None = None
    generate_images: bool = True
    regenerate_images: bool = False

    @field_validator("pattern_card_path")
    @classmethod
    def _check_pattern_card_path(cls, v: str | None) -> str | None:
        return _validate_under_output(v)


class ValidateRequest(BaseModel):
    content_path: str

    @field_validator("content_path")
    @classmethod
    def _check_content_path(cls, v: str) -> str:
        checked = _validate_under_output(v)
        assert checked is not None  # content_path 는 required, None 불가
        return checked


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
