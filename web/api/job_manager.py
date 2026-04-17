"""작업 관리자 — in-memory Job 저장소 + ThreadPoolExecutor + EventBus.

서버 재시작 시 작업 목록은 초기화되지만 output/ 파일은 유지된다.
내부 1~3명 사용 기준이므로 DB 저장 없이 in-memory 로 충분하다.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

from web.api.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)

MAX_WORKERS = 2


@dataclass
class Job:
    id: str
    type: str
    keyword: str
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: list[dict[str, Any]] = field(default_factory=list)


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

    def _submit(self, job_type: str, params: dict[str, Any]) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            type=job_type,
            keyword=params.get("keyword", ""),
            params=params,
        )
        self._jobs[job_id] = job
        self._executor.submit(self._run_job, job)
        return job

    def _run_job(self, job: Job) -> None:
        job.status = "running"
        job.started_at = datetime.now(tz=UTC)
        self.event_bus.emit(job.id, {"type": "job_status", "status": "running"})

        reporter = WebSocketProgressReporter(job.id, self.event_bus, job)

        try:
            result = self._dispatch(job, reporter)
            job.status = "succeeded"
            job.result = result.model_dump(mode="json")
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job.status = "failed"
            job.error = str(exc)
            self.event_bus.emit(
                job.id, {"type": "pipeline_error", "stage": "unknown", "error": str(exc)}
            )
        finally:
            job.finished_at = datetime.now(tz=UTC)
            self.event_bus.emit(job.id, {"type": "job_status", "status": job.status})

    def _dispatch(
        self,
        job: Job,
        reporter: WebSocketProgressReporter,
    ) -> PipelineResult | AnalyzeResult | GenerateResult | ValidateResult:
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

        msg = f"Unknown job type: {job.type}"
        raise ValueError(msg)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
