"""작업 관리자 — in-memory Job 저장소 + ThreadPoolExecutor + EventBus.

서버 재시작 시 작업 목록은 초기화되지만 output/ 파일은 유지된다.
내부 1~3명 사용 기준이므로 DB 저장 없이 in-memory 로 충분하다.

Phase J2 (2026-05-08): `JOB_PERSISTENCE_ENABLED=true` 시 Supabase jobs 테이블
write-through 가 활성화돼 컨테이너 재시작 후에도 GET /api/jobs/{id} 가 응답
가능. flag default false → 본 모듈 동작은 기존 in-memory 와 동일.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import threading
import uuid
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from application.job_context import job_id_var
from application.models import (
    AnalyzeResult,
    GenerateResult,
    PipelineResult,
    ValidateResult,
)
from application.orchestrator import (
    run_analyze_only,
    run_generate_only,
    run_pipeline,
    run_validate_only,
)
from application.ranking_bulk_check import bulk_check_rankings
from config.settings import settings
from domain.brand_card.model import RenderedCardSet
from domain.ranking.model import RankingCheckSummary
from web.api import job_store
from web.api.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)

MAX_WORKERS = 2

# Phase J2 — 컨테이너 식별. RENDER_INSTANCE_ID 가 표준이고, 없으면 hostname.
# main.py 의 재시작 알림 (J1.4) 과 동일 식별. PR4 startup sweep 의
# `mark_running_as_orphaned(instance_id=...)` 가 이 값과 매칭되어야 자기
# 컨테이너의 stale running 만 깨끗이 마킹.
INSTANCE_ID = os.environ.get("RENDER_INSTANCE_ID") or socket.gethostname()


@dataclass
class Job:
    id: str
    type: str
    keyword: str
    status: str = "pending"  # pending|running|succeeded|failed|cancelled|timed_out
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: list[dict[str, Any]] = field(default_factory=list)
    future: Future[Any] | None = field(default=None, repr=False)
    cancel_requested: bool = False


class JobEventBus:
    """sync worker 스레드 → async WebSocket 브릿지."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[job_id].append(q)
        return q

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subs = self._subscribers.get(job_id, [])
        if queue in subs:
            subs.remove(queue)

    def emit(self, job_id: str, event: dict[str, Any]) -> None:
        """Thread-safe. Worker 스레드에서 호출."""
        self._history[job_id].append(event)
        if self._loop is None:
            return
        for q in self._subscribers.get(job_id, []):
            self._loop.call_soon_threadsafe(q.put_nowait, event)

    def get_history(self, job_id: str) -> list[dict[str, Any]]:
        return list(self._history.get(job_id, []))


class JobManager:
    """작업 저장소 + 백그라운드 실행."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.event_bus = JobEventBus()
        self._on_finished_hooks: list[Callable[[Job], None]] = []

    def register_on_finished(self, hook: Callable[[Job], None]) -> None:
        """job 종료(succeeded/failed/cancelled/timed_out) 시 호출되는 훅 등록.

        훅 실행 중 예외는 swallow + 로깅 (다른 훅·후속 처리 차단 방지).
        republish_jobs 라이프사이클 동기화 등에 사용.
        """
        self._on_finished_hooks.append(hook)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.event_bus.set_loop(loop)

    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def submit_pipeline(self, params: dict[str, Any]) -> Job:
        return self._submit("pipeline", params)

    def submit_analyze(self, params: dict[str, Any]) -> Job:
        return self._submit("analyze", params)

    def submit_generate(self, params: dict[str, Any]) -> Job:
        return self._submit("generate", params)

    def submit_validate(self, params: dict[str, Any]) -> Job:
        return self._submit("validate", params)

    def submit_ranking_bulk_check(self, params: dict[str, Any]) -> Job:
        """일괄 SERP 측정 job 제출. params: {publication_ids?: [...]}."""
        return self._submit("ranking_bulk_check", params)

    def submit_brand_card_render(self, params: dict[str, Any]) -> Job:
        """브랜드 카드 렌더 job 제출.

        params: {reuse_group_id, brand_name?, brand_url?}.
        Playwright PNG 렌더 + AI 이미지 prefetch — 5~30s 소요라 동기 응답이
        클라이언트 UX 를 막아 background 처리. 진행은 GET /api/jobs/{job_id} 폴링.
        """
        return self._submit("brand_card_render", params)

    def _submit(self, job_type: str, params: dict[str, Any]) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            type=job_type,
            keyword=params.get("keyword", ""),
            params=params,
        )
        # Phase J2 — flag on 시 in-memory dict put 직전 동기 insert (transactional).
        # insert 실패해도 in-memory 는 정상 생성 → 사용자 즉시 응답 (graceful).
        # 이 경우 컨테이너 재시작 시 해당 job 은 영구 분실, 클라이언트는 J1.1
        # retry-bound 로 종결. flag off 면 noop.
        if settings.job_persistence_enabled:
            try:
                job_store.insert_job(
                    job_id,
                    job_type=job_type,
                    keyword=job.keyword,
                    params=params,
                    instance_id=INSTANCE_ID,
                )
            except Exception:
                logger.warning("job_store.insert_job exception job_id=%s", job_id, exc_info=True)
        self._jobs[job_id] = job
        job.future = self._executor.submit(self._run_job, job)
        self._arm_timeout(job)
        return job

    # Phase J2 — DB write 단일 진입점. flag off 시 즉시 return.
    # 4지점 (`_run_job` running/succeeded/failed, `_arm_timeout` timed_out,
    # `cancel_job` cancelled) 이 모두 이 helper 호출. graceful degrade 책임.
    def _persist_status(
        self,
        job: Job,
        status: str,
        *,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        if not settings.job_persistence_enabled:
            return
        try:
            job_store.update_job_status(
                job.id,
                status,
                error=error,
                started_at=started_at,
                finished_at=finished_at,
                result=result,
            )
        except Exception:
            logger.warning(
                "job_store.update_job_status exception job_id=%s status=%s",
                job.id,
                status,
                exc_info=True,
            )

    def _arm_timeout(self, job: Job) -> None:
        """job_timeout_seconds 초 후 여전히 running 이면 timed_out 표시.

        Python 스레드는 강제 종료할 수 없으므로 상태만 전환하고 이벤트를 발행한다.
        워커 스레드는 백그라운드에서 계속 실행될 수 있다(soft timeout).
        """
        timeout = max(60, int(settings.job_timeout_seconds))

        def _check() -> None:
            if job.status == "running":
                # cancel_requested 를 먼저 세워야 reporter.check_cancel() 폴링 지점에서
                # 워커가 실제로 중단된다. 이게 빠지면 상태만 timed_out 이고 백그라운드에서
                # LLM/크롤링이 계속 과금되는 "cosmetic timeout" 이 된다.
                job.cancel_requested = True
                job.status = "timed_out"
                job.error = f"job timed out after {timeout}s"
                job.finished_at = datetime.now(tz=UTC)
                logger.warning("Job %s timed out after %ds", job.id, timeout)
                self.event_bus.emit(
                    job.id,
                    {"type": "pipeline_error", "stage": "timeout", "error": job.error},
                )
                self.event_bus.emit(job.id, {"type": "job_status", "status": "timed_out"})
                self._persist_status(job, "timed_out", error=job.error, finished_at=job.finished_at)

        # daemon=True — 서버 종료 시 timeout 대기 없이 즉시 정리.
        timer = threading.Timer(timeout, _check)
        timer.daemon = True
        timer.start()

    def cancel_job(self, job_id: str) -> bool:
        """취소 요청. 대기 중이면 future.cancel() 로 즉시 종료.

        이미 실행 중이면 cancel_requested 플래그만 세우고 상태를 cancelled 로 표시.
        실제 워커 스레드는 강제 종료 불가하나, reporter 호출 시점에
        파이프라인 측에서 플래그를 검사해 중단할 수 있다.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False
        if job.status in ("succeeded", "failed", "cancelled", "timed_out"):
            return False
        job.cancel_requested = True
        if job.future is not None and job.future.cancel():
            job.status = "cancelled"
            job.finished_at = datetime.now(tz=UTC)
            self.event_bus.emit(job.id, {"type": "job_status", "status": "cancelled"})
            self._persist_status(job, "cancelled", finished_at=job.finished_at)
            return True
        # 이미 실행 중 — soft cancel
        job.status = "cancelled"
        job.finished_at = datetime.now(tz=UTC)
        self.event_bus.emit(job.id, {"type": "job_status", "status": "cancelled"})
        self._persist_status(job, "cancelled", finished_at=job.finished_at)
        return True

    def _run_job(self, job: Job) -> None:
        if job.cancel_requested:
            job.status = "cancelled"
            job.finished_at = datetime.now(tz=UTC)
            self.event_bus.emit(job.id, {"type": "job_status", "status": "cancelled"})
            self._persist_status(job, "cancelled", finished_at=job.finished_at)
            return
        job.status = "running"
        job.started_at = datetime.now(tz=UTC)
        self.event_bus.emit(job.id, {"type": "job_status", "status": "running"})
        self._persist_status(job, "running", started_at=job.started_at)

        reporter = WebSocketProgressReporter(job.id, self.event_bus, job)

        token = job_id_var.set(job.id)
        try:
            result = self._dispatch(job, reporter)
            # timeout/cancel 이 먼저 터졌으면 그 상태를 유지
            if job.status in ("timed_out", "cancelled"):
                return
            job.status = "succeeded"
            job.result = result.model_dump(mode="json")
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            if job.status not in ("timed_out", "cancelled"):
                job.status = "failed"
                job.error = str(exc)
                self.event_bus.emit(
                    job.id, {"type": "pipeline_error", "stage": "unknown", "error": str(exc)}
                )
        finally:
            job_id_var.reset(token)
            job.finished_at = datetime.now(tz=UTC)
            self.event_bus.emit(job.id, {"type": "job_status", "status": job.status})
            # Phase J2 — terminal 상태만 DB 동기화. timed_out/cancelled 는 위에서 이미
            # _persist_status 호출됐으므로 여기서는 succeeded/failed 만 다시 갱신.
            # (timed_out/cancelled 도 다시 보내면 동일 상태 update 라 idempotent 하지만
            # finished_at 이 약간 미래로 덮일 수 있어 분기 처리)
            if job.status in ("succeeded", "failed"):
                self._persist_status(
                    job,
                    job.status,
                    error=job.error,
                    finished_at=job.finished_at,
                    result=job.result,
                )
            for hook in self._on_finished_hooks:
                try:
                    hook(job)
                except Exception:
                    logger.exception(
                        "on_finished hook failed for job %s (%s)", job.id, hook.__name__
                    )

    def _dispatch(
        self,
        job: Job,
        reporter: WebSocketProgressReporter,
    ) -> (
        PipelineResult
        | AnalyzeResult
        | GenerateResult
        | ValidateResult
        | RankingCheckSummary
        | RenderedCardSet
    ):
        p = job.params

        if job.type == "pipeline":
            card_path = Path(p["pattern_card_path"]) if p.get("pattern_card_path") else None
            return run_pipeline(
                keyword=p["keyword"],
                reporter=reporter,
                pattern_card_path=card_path,
                generate_images=p.get("generate_images", True),
                regenerate_images=p.get("regenerate_images", False),
                force_analyze=p.get("force_analyze", False),
            )

        if job.type == "analyze":
            return run_analyze_only(keyword=p["keyword"], reporter=reporter)

        if job.type == "generate":
            card_path = Path(p["pattern_card_path"]) if p.get("pattern_card_path") else None
            return run_generate_only(
                keyword=p.get("keyword"),
                pattern_card_path=card_path,
                reporter=reporter,
                generate_images=p.get("generate_images", True),
                regenerate_images=p.get("regenerate_images", False),
            )

        if job.type == "validate":
            return run_validate_only(
                content_path=Path(p["content_path"]),
                reporter=reporter,
            )

        if job.type == "ranking_bulk_check":
            return bulk_check_rankings(
                publication_ids=p.get("publication_ids"),
                reporter=reporter,
            )

        if job.type == "brand_card_render":
            from application.brand_card_orchestrator import render_card_set

            output_root_str = p.get("output_root")
            return render_card_set(
                p["reuse_group_id"],
                output_root=Path(output_root_str) if output_root_str else None,
                brand_name=p.get("brand_name"),
                brand_url=p.get("brand_url"),
            )

        msg = f"Unknown job type: {job.type}"
        raise ValueError(msg)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
