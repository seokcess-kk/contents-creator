"""순위 추적 API. SPEC-RANKING.md §3 [조회] 참조.

운영 OS 엔드포인트:
- GET    /rankings/summary                      — 운영 홈 상단 요약 카운트
- GET    /rankings/queue?tab=action_required    — 탭별 작업 큐 (enrich 포함)
- POST   /rankings/publications/{id}/hold       — 보류 액션
- POST   /rankings/publications/{id}/release    — 보류 해제
- POST   /rankings/publications/{id}/dismiss    — 기각
- POST   /rankings/publications/{id}/restore    — 기각 취소
- POST   /rankings/publications/{id}/republish  — 재발행 트리거 (파이프라인 job 시작)
- GET    /rankings/publications/{id}/actions    — 액션 히스토리

기존 엔드포인트:
- POST   /rankings/publications        — URL 등록
- GET    /rankings/publications        — 등록 목록
- GET    /rankings/publications/{id}   — 단건 + timeline
- PATCH  /rankings/publications/{id}   — 부분 수정
- DELETE /rankings/publications/{id}   — 삭제
- GET    /rankings/publications/{id}/diagnoses  — 진단 시계열
- POST   /rankings/publications/{id}/diagnose   — 진단 즉시 실행
- POST   /rankings/diagnoses/{id}/action        — 진단 액션 (legacy)
- GET    /rankings/diagnoses/board              — 조치 필요 publication + 최신 진단 보드
- POST   /rankings/diagnoses/bulk-action        — 진단 ID 일괄 액션 (republish/hold/dismiss/mark)
- GET    /rankings/calendar            — 월별 캘린더
- POST   /rankings/check/{publication_id}  — 즉시 SERP 체크
- GET    /rankings/{publication_id}    — Snapshot 시계열
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from application import ranking_orchestrator
from domain.ranking.model import RankingDuplicateUrlError, RankingMatchError
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

# 외부 cron(GitHub Actions)이 매일 호출하는 /check-all 의 동시 실행 가드.
# 단일 컨테이너 전제 — 멀티 인스턴스 전환 시 Supabase advisory lock 으로 교체.
_check_all_lock = threading.Lock()
_check_all_running = False
# 마지막 check-all 실행 결과 — workflow 검증 단계가 polling 으로 읽어
# errors_count 또는 usage_save_failed_count > 0 이면 자동 fail + issue.
_last_check_all_result: dict[str, Any] = {"status": "never_run"}

router = APIRouter(
    prefix="/rankings",
    tags=["rankings"],
    dependencies=[Depends(require_api_key)],
)


# ── Request/Response 스키마 ──


class PublicationCreateRequest(BaseModel):
    keyword: str = Field(min_length=1)
    url: str | None = None  # null = draft 생성, str = 정식 등록 (네이버 블로그)
    slug: str | None = Field(default=None, min_length=1)
    job_id: str | None = None
    published_at: datetime | None = None
    blog_channel_id: str | None = None

    @field_validator("url")
    @classmethod
    def reject_empty_url(cls, v: str | None) -> str | None:
        """빈 문자열은 모호한 입력 — 400. draft 생성 시 명시적으로 null 사용."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("url 이 비어있습니다 (draft 생성은 null 사용)")
        return v


class PublicationUpdateRequest(BaseModel):
    """부분 수정. 전달된 필드만 적용."""

    keyword: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    published_at: datetime | None = None
    blog_channel_id: str | None = None


# ── 엔드포인트 ──


@router.post("/publications")
def create_publication(req: PublicationCreateRequest) -> dict[str, Any]:
    """발행 URL 등록 (멱등). 동일 url 재호출은 기존 publication 반환."""
    try:
        publication = ranking_orchestrator.register_publication(
            keyword=req.keyword,
            slug=req.slug,
            url=req.url,
            job_id=req.job_id,
            published_at=req.published_at,
            blog_channel_id=req.blog_channel_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return publication.model_dump(mode="json")


class BulkPublicationItem(BaseModel):
    keyword: str = Field(min_length=1)
    url: str | None = None
    slug: str | None = Field(default=None, min_length=1)
    published_at: datetime | None = None
    blog_channel_id: str | None = None


class BulkPublicationsRequest(BaseModel):
    items: list[BulkPublicationItem] = Field(min_length=1, max_length=500)


@router.post("/publications/bulk")
def bulk_create_publications(req: BulkPublicationsRequest) -> dict[str, Any]:
    """대량 외부 URL 등록.

    중복은 사전 조회로 skipped, 형식 오류는 failed 로 분리.
    한 번에 최대 500개 — 그 이상은 클라이언트에서 분할 호출 권장.
    """
    items_payload = [it.model_dump(mode="python") for it in req.items]
    result = ranking_orchestrator.bulk_register_publications(items_payload)
    return {
        "total": len(req.items),
        "created_count": len(result["created"]),
        "skipped_count": len(result["skipped"]),
        "failed_count": len(result["failed"]),
        **result,
    }


@router.get("/publications")
def list_publications(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """등록 목록 조회. keyword 지정 시 필터."""
    from domain.ranking import storage

    publications = storage.list_publications(keyword=keyword, limit=limit)
    return {
        "count": len(publications),
        "items": [p.model_dump(mode="json") for p in publications],
    }


@router.get("/publications/by-slug/{slug}")
def get_latest_publication_by_slug(slug: str) -> dict[str, Any]:
    """slug 기준 최신 publication 조회. 결과 상세 화면 초기 로딩 최적화용."""
    from domain.ranking import storage

    publication = storage.get_latest_publication_by_slug(slug)
    if publication is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return publication.model_dump(mode="json")


@router.get("/publications/{publication_id}")
def get_publication_with_timeline(publication_id: str) -> dict[str, Any]:
    """단건 publication + 최근 90개 snapshot timeline."""
    timeline = ranking_orchestrator.get_publication_timeline(publication_id, limit=90)
    if timeline is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return timeline.model_dump(mode="json")


@router.patch("/publications/{publication_id}")
def update_publication(publication_id: str, req: PublicationUpdateRequest) -> dict[str, Any]:
    """publication 부분 수정. 전달된 필드만 갱신."""
    try:
        updated = ranking_orchestrator.update_publication(
            publication_id,
            keyword=req.keyword,
            url=req.url,
            slug=req.slug,
            published_at=req.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RankingDuplicateUrlError as exc:
        raise HTTPException(status_code=409, detail=f"이미 등록된 URL 입니다: {exc}") from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return updated.model_dump(mode="json")


@router.delete("/publications/{publication_id}", status_code=204)
def delete_publication(publication_id: str) -> Response:
    """publication 삭제. snapshots 도 cascade 로 함께 삭제."""
    deleted = ranking_orchestrator.delete_publication(publication_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return Response(status_code=204)


class DiagnosisActionRequest(BaseModel):
    user_action: str = Field(min_length=1, max_length=50)


@router.get("/publications/{publication_id}/diagnoses")
def list_diagnoses(
    publication_id: str, limit: int = Query(default=30, ge=1, le=200)
) -> dict[str, Any]:
    """publication 의 진단 시계열 (diagnosed_at desc)."""
    from domain.diagnosis import storage as diagnosis_storage

    items = diagnosis_storage.list_diagnoses_by_publication(publication_id, limit=limit)
    return {
        "publication_id": publication_id,
        "count": len(items),
        "items": [d.model_dump(mode="json") for d in items],
    }


@router.post("/publications/{publication_id}/diagnose")
def trigger_diagnose(publication_id: str) -> dict[str, Any]:
    """publication 진단 즉시 실행 (수동 트리거). 룰 평가 후 저장된 진단 반환."""
    from application.diagnosis_orchestrator import diagnose_publication

    diagnoses = diagnose_publication(publication_id)
    return {
        "publication_id": publication_id,
        "count": len(diagnoses),
        "items": [d.model_dump(mode="json") for d in diagnoses],
    }


@router.post("/diagnoses/{diagnosis_id}/action")
def record_diagnosis_action(diagnosis_id: str, req: DiagnosisActionRequest) -> dict[str, Any]:
    """사용자 액션 기록 (republished | held | dismissed | marked_competitor_strong)."""
    from datetime import UTC, datetime

    from domain.diagnosis import storage as diagnosis_storage

    updated = diagnosis_storage.update_user_action(
        diagnosis_id,
        user_action=req.user_action,
        user_action_at=datetime.now(tz=UTC).isoformat(),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="diagnosis 미존재")
    return updated.model_dump(mode="json")


# ── 진단 보드 (조치 필요 publication 의 최신 진단 + 일괄 액션) ────────────


class DiagnosisBoardBulkRequest(BaseModel):
    diagnosis_ids: list[str] = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=64)


@router.get("/diagnoses/board")
def get_diagnoses_board(
    min_confidence: float = Query(default=0.6, ge=0.0, le=1.0),
    reasons: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    """workflow_status=action_required 인 publication 중 필터 통과 최신 진단."""
    from application.diagnosis_board_orchestrator import get_diagnosis_board

    board = get_diagnosis_board(
        min_confidence=min_confidence,
        reasons=reasons,
        limit=limit,
    )
    return board.model_dump(mode="json")


@router.post("/diagnoses/bulk-action")
def execute_diagnoses_bulk_action(req: DiagnosisBoardBulkRequest) -> dict[str, Any]:
    """진단 ID 들에 대한 일괄 액션. action 별로 다른 orchestrator 라우팅.

    응답: total / succeeded[] / skipped[] / failed[]. partial failure 는 데이터로 노출.
    """
    from application.diagnosis_board_orchestrator import execute_bulk_action

    try:
        result = execute_bulk_action(
            diagnosis_ids=req.diagnosis_ids,
            action=req.action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump(mode="json")


class BulkCheckRequest(BaseModel):
    """publication_ids=None 이면 measurable 전체."""

    publication_ids: list[str] | None = None


@router.get("/bulk-check/preview")
def bulk_check_preview(
    publication_ids: Annotated[list[str] | None, Query()] = None,
) -> dict[str, int]:
    """일괄 측정 시 실제 대상 publication 개수 미리보기 (UI 모달용)."""
    from application.ranking_bulk_check import count_measurable

    count = count_measurable(publication_ids)
    return {"measurable_count": count}


@router.post("/bulk-check", status_code=202)
def trigger_bulk_check(req: BulkCheckRequest) -> dict[str, str]:
    """일괄 SERP 측정 job 시작. job_id 반환 → /jobs/{id} 로 진행률 폴링.

    publication_ids=None 이면 measurable 전체 (URL 있고 active/action_required).
    """
    from web.api.main import job_manager

    job = job_manager.submit_ranking_bulk_check({"publication_ids": req.publication_ids})
    return {"job_id": job.id}


@router.get("/summary")
def get_operations_summary() -> dict[str, int]:
    """운영 홈 상단 요약 카드 — workflow_status 별 카운트."""
    from application.operations_home import get_summary

    return get_summary()


@router.get("/queue")
def get_operations_queue(
    tab: str = Query(default="action_required"),
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    """탭별 작업 큐. tab: action_required | republishing | held | active | dismissed | all."""
    from application.operations_home import list_publications_for_tab

    try:
        items = list_publications_for_tab(tab, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tab": tab, "count": len(items), "items": items}


# ── 운영 액션 ──


class HoldRequest(BaseModel):
    days: int = Field(ge=1, le=90, description="보류 기간 (일)")
    reason: str | None = Field(default=None, max_length=200)


@router.post("/publications/{publication_id}/hold")
def hold_publication(publication_id: str, req: HoldRequest) -> dict[str, Any]:
    """publication 을 N일간 보류. held_until 자동 산출."""
    from application.publication_actions_orchestrator import hold

    pub = hold(publication_id, days=req.days, reason=req.reason)
    if pub is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return pub.model_dump(mode="json")


@router.post("/publications/{publication_id}/release")
def release_publication(publication_id: str) -> dict[str, Any]:
    """보류 해제 → action_required 복귀."""
    from application.publication_actions_orchestrator import release_hold

    pub = release_hold(publication_id)
    if pub is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return pub.model_dump(mode="json")


class DismissRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


@router.post("/publications/{publication_id}/dismiss")
def dismiss_publication(publication_id: str, req: DismissRequest) -> dict[str, Any]:
    """publication 기각 → workflow_status=dismissed."""
    from application.publication_actions_orchestrator import dismiss

    pub = dismiss(publication_id, reason=req.reason)
    if pub is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return pub.model_dump(mode="json")


@router.post("/publications/{publication_id}/restore")
def restore_publication(publication_id: str) -> dict[str, Any]:
    """기각 취소 → action_required 복귀."""
    from application.publication_actions_orchestrator import restore

    pub = restore(publication_id)
    if pub is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    return pub.model_dump(mode="json")


@router.get("/publications/{publication_id}/actions")
def list_publication_actions(
    publication_id: str, limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    """publication 액션 히스토리 (publication_actions, created_at desc)."""
    from domain.ranking import publication_actions as actions_storage

    items = actions_storage.list_actions_by_publication(publication_id, limit=limit)
    return {
        "publication_id": publication_id,
        "count": len(items),
        "items": [a.model_dump(mode="json") for a in items],
    }


@router.get("/publications/{publication_id}/events")
def list_publication_events(
    publication_id: str,
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    """publication 통합 이벤트 타임라인 — snapshot/diagnosis/action 시간순 merge."""
    from application.events_aggregator import (
        list_publication_events as aggregate_events,
    )

    events = aggregate_events(publication_id)
    sliced = events[:limit]
    return {
        "publication_id": publication_id,
        "count": len(sliced),
        "items": [e.model_dump(mode="json") for e in sliced],
    }


# ── 재발행 ──


class RepublishRequest(BaseModel):
    strategy: str = Field(default="full_rewrite")
    diagnosis_id: str | None = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in ("full_rewrite", "light", "cluster"):
            raise ValueError(f"strategy 는 full_rewrite/light/cluster 중 하나: {v!r}")
        return v


@router.post("/publications/{publication_id}/republish")
def trigger_republish(publication_id: str, req: RepublishRequest) -> dict[str, Any]:
    """재발행 트리거 — draft publication 자동 생성 + 파이프라인 job 시작.

    - 동일 source 에 active(queued/running) job 있으면 409 (DB partial unique 제약)
    - 부모 publication.workflow_status = republishing
    """
    from application.republish_orchestrator import start_republish

    try:
        result = start_republish(
            publication_id,
            strategy=req.strategy,
            diagnosis_id=req.diagnosis_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        # active job 충돌
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.get("/calendar")
def get_calendar(
    month: str = Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM (KST 기준)"),
) -> dict[str, Any]:
    """월별 publication × 일자 캘린더 (KST). 같은 일 다회 측정은 마지막 측정 사용."""
    try:
        year_str, month_str = month.split("-")
        calendar = ranking_orchestrator.get_monthly_calendar(int(year_str), int(month_str))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return calendar.model_dump(mode="json")


@router.post("/check/{publication_id}")
def trigger_check(publication_id: str) -> dict[str, Any]:
    """단일 publication 즉시 SERP 체크 (수동 트리거)."""
    try:
        snapshot = ranking_orchestrator.check_rankings_for_publication(publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RankingMatchError as exc:
        raise HTTPException(status_code=502, detail=f"SERP 측정 실패: {exc}") from exc
    return snapshot.model_dump(mode="json")


@router.post("/check-all")
def trigger_check_all(background_tasks: BackgroundTasks, response: Response) -> dict[str, Any]:
    """전체 활성 publication 일괄 SERP 체크. **외부 cron 진입점**.

    GitHub Actions 가 매일 09:00 KST 에 호출. 즉시 202 + 백그라운드 실행.

    **idempotent** — 이미 실행 중일 때 같은 호출이 또 와도 (workflow retry,
    cold-start timeout 후 재전송 등) 200 + 현재 진행 정보를 반환한다. 2026-05-04
    workflow retry × 우리 lock 충돌로 409 폭발한 사고 후 변경. POST 가 멱등이
    아니라는 점을 외부 retry 전략에 의존하지 않고 endpoint 자체에서 흡수.

    in-process APScheduler 가 컨테이너 재시작에 취약했던 문제(2026-04-30·05-01
    누락 실측)를 해결하려고 외부 cron 진입점으로 설계. 컨테이너 lifecycle 과
    무관하게 정확히 한 번 발화한다.
    """
    global _check_all_running
    with _check_all_lock:
        if _check_all_running:
            response.status_code = 200
            return {
                "status": "already_running",
                "started_at": _last_check_all_result.get("started_at"),
                "detail": "이미 실행 중인 배치가 있어 새 호출을 무시했습니다 (idempotent).",
            }
        _check_all_running = True

    started_at = datetime.now(UTC).isoformat()
    _last_check_all_result.clear()
    _last_check_all_result.update({"status": "running", "started_at": started_at})
    background_tasks.add_task(_run_check_all_safely, started_at)
    logger.info("rankings.check_all_accepted started_at=%s", started_at)
    response.status_code = 202
    return {"status": "accepted", "started_at": started_at}


def _run_check_all_safely(started_at: str) -> None:
    """BackgroundTasks 실행 본체. 종료 후 lock 해제 + 결과 저장 보장."""
    global _check_all_running
    try:
        summary = ranking_orchestrator.check_all_active_rankings()
        finished_at = datetime.now(UTC).isoformat()
        result: dict[str, Any] = {
            "status": "succeeded",
            "started_at": started_at,
            "finished_at": finished_at,
            "checked_count": summary.checked_count,
            "found_count": summary.found_count,
            "errors_count": summary.errors_count,
            "usage_save_failed_count": summary.usage_save_failed_count,
            "duration_seconds": summary.duration_seconds,
        }
        _last_check_all_result.clear()
        _last_check_all_result.update(result)
        logger.info(
            "rankings.check_all_done checked=%d found=%d errors=%d "
            "usage_save_failed=%d duration=%.1fs",
            summary.checked_count,
            summary.found_count,
            summary.errors_count,
            summary.usage_save_failed_count,
            summary.duration_seconds,
        )
    except Exception as exc:
        _last_check_all_result.clear()
        _last_check_all_result.update(
            {
                "status": "failed",
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        logger.exception("rankings.check_all_failed")
    finally:
        with _check_all_lock:
            _check_all_running = False


@router.get("/check-all/last")
def get_last_check_all_result() -> dict[str, Any]:
    """마지막 check-all 실행 결과. **GitHub Actions 검증 단계가 polling**.

    workflow 가 호출 후 적절한 wait 뒤 이 endpoint 를 polling 해 status="succeeded"
    + errors_count == 0 + usage_save_failed_count == 0 인지 확인. 어느 하나라도
    어긋나면 workflow 가 fail + GitHub Issue 자동 생성.

    응답 status:
    - "never_run" — 서비스 시작 후 아직 호출 없음
    - "running"   — 현재 실행 중
    - "succeeded" — 정상 종료 (errors_count·usage_save_failed_count 별도 확인 필요)
    - "failed"    — orchestrator 가 raise 한 예외 종료
    """
    return dict(_last_check_all_result)


@router.get("/{publication_id}")
def list_snapshots(
    publication_id: str,
    limit: int = Query(default=90, ge=1, le=365),
) -> dict[str, Any]:
    """publication 의 RankingSnapshot 시계열 (captured_at desc)."""
    from domain.ranking import storage

    publication = storage.get_publication(publication_id)
    if publication is None:
        raise HTTPException(status_code=404, detail="publication 미존재")
    snapshots = storage.list_snapshots(publication_id, limit=limit)
    return {
        "publication_id": publication_id,
        "count": len(snapshots),
        "items": [s.model_dump(mode="json") for s in snapshots],
    }
