"""작업 제출·조회 API."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from config.settings import settings
from web.api import job_store
from web.api.auth import require_api_key
from web.api.schemas import (
    AnalyzeRequest,
    GenerateRequest,
    JobResponse,
    JobSubmitResponse,
    PipelineRequest,
    ValidateRequest,
)
from web.api.signed_token import MAX_TTL_SECONDS, mint

if TYPE_CHECKING:
    from web.api.job_manager import Job

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])


def _get_manager():  # type: ignore[no-untyped-def]
    from web.api.main import job_manager

    return job_manager


def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        type=job.type,
        keyword=job.keyword,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        params=job.params,
        result=job.result,
        error=job.error,
        progress=job.progress,
    )


def _parse_dt(value: Any) -> datetime | None:
    """Supabase row 의 ISO8601 timestamp 문자열을 datetime 으로 변환."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Postgres timestamptz: "2026-05-08T12:00:00+00:00" 또는 "...Z"
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _row_to_response(row: dict[str, Any]) -> JobResponse:
    """Phase J2 PR3 — DB row → JobResponse. in-memory miss 시 fallback 응답.

    progress 는 빈 list (PR3 범위 밖). progress_events 테이블에서 재생하는 동선은
    후속 PR 또는 별도 endpoint 로 분리.
    """
    return JobResponse(
        id=str(row.get("id", "")),
        type=str(row.get("type", "")),
        keyword=str(row.get("keyword") or ""),
        status=str(row.get("status", "orphaned")),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        started_at=_parse_dt(row.get("started_at")),
        finished_at=_parse_dt(row.get("finished_at")),
        params=row.get("params") or {},
        result=row.get("result"),
        error=row.get("error"),
        progress=[],
    )


@router.post("/pipeline", status_code=202)
def submit_pipeline(req: PipelineRequest) -> JobSubmitResponse:
    job = _get_manager().submit_pipeline(req.model_dump())
    return JobSubmitResponse(job_id=job.id)


@router.post("/analyze", status_code=202)
def submit_analyze(req: AnalyzeRequest) -> JobSubmitResponse:
    job = _get_manager().submit_analyze(req.model_dump())
    return JobSubmitResponse(job_id=job.id)


@router.post("/generate", status_code=202)
def submit_generate(req: GenerateRequest) -> JobSubmitResponse:
    job = _get_manager().submit_generate(req.model_dump())
    return JobSubmitResponse(job_id=job.id)


@router.post("/validate", status_code=202)
def submit_validate(req: ValidateRequest) -> JobSubmitResponse:
    job = _get_manager().submit_validate(req.model_dump())
    return JobSubmitResponse(job_id=job.id)


@router.get("")
def list_jobs() -> list[JobResponse]:
    return [_job_to_response(j) for j in _get_manager().list_jobs()]


@router.get("/{job_id}")
def get_job(job_id: str) -> JobResponse:
    job = _get_manager().get_job(job_id)
    if job is not None:
        return _job_to_response(job)
    # Phase J2 PR3 — in-memory miss + flag on → DB fallback. orphaned 도 정상
    # 200 OK 로 응답. 클라이언트 (`useJobPolling`) 가 orphaned 를 terminal 로
    # 인식해 retry-bound 와 별개로 자연 종결.
    if settings.job_persistence_enabled:
        row = job_store.get_job(job_id)
        if row is not None:
            return _row_to_response(row)
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/{job_id}/ws-token")
def mint_ws_token(job_id: str) -> dict[str, object]:
    """WS 연결용 단명 토큰 발급. X-API-Key 헤더 필수.

    브라우저 WS 는 커스텀 헤더를 못 붙이므로 기존에는 admin_api_key 를 `?token=` 으로
    넣었다. 이제는 jobId 에 바인딩된 HMAC 토큰을 받아 WS 핸드셰이크에만 쓴다.
    job_timeout_seconds 상한까지 TTL 허용.
    """
    mgr = _get_manager()
    if mgr.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    token, expires_at = mint("job", job_id, ttl_seconds=MAX_TTL_SECONDS)
    return {"token": token, "expires_at": expires_at}


@router.delete("/{job_id}", status_code=202)
def cancel_job(job_id: str) -> dict[str, str]:
    mgr = _get_manager()
    if mgr.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    ok = mgr.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Job already finished")
    return {"status": "cancelled"}
