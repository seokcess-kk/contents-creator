"""WebSocket 진행 리포터 — ProgressReporter 프로토콜 구현.

sync worker 스레드에서 호출되며, JobEventBus 를 통해
async WebSocket 클라이언트에게 이벤트를 전달한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from web.api.job_manager import Job, JobEventBus


class WebSocketProgressReporter:
    """application.progress.ProgressReporter 프로토콜 구현체."""

    def __init__(self, job_id: str, event_bus: JobEventBus, job: Job) -> None:
        self._job_id = job_id
        self._bus = event_bus
        self._job = job

    def stage_start(self, stage: str, total: int | None = None) -> None:
        event: dict[str, Any] = {
            "type": "stage_start",
            "stage": stage,
            "total": total,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)

    def stage_progress(self, current: int, detail: str = "") -> None:
        event: dict[str, Any] = {
            "type": "stage_progress",
            "current": current,
            "detail": detail,
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)

    def stage_end(self, stage: str, result_summary: dict[str, Any]) -> None:
        event: dict[str, Any] = {
            "type": "stage_end",
            "stage": stage,
            "summary": result_summary,
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)

    def pipeline_complete(self, result: Any) -> None:
        event: dict[str, Any] = {
            "type": "pipeline_complete",
            "status": "succeeded",
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)

    def pipeline_error(self, stage: str, error: Exception) -> None:
        event: dict[str, Any] = {
            "type": "pipeline_error",
            "stage": stage,
            "error": str(error),
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)
