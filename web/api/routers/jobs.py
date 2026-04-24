"""작업 제출·조회 API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

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
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


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
