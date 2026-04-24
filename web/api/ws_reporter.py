"""WebSocket 진행 리포터 — ProgressReporter 프로토콜 구현.

sync worker 스레드에서 호출되며, JobEventBus 를 통해
async WebSocket 클라이언트에게 이벤트를 전달한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from application.progress import JobCancelled

if TYPE_CHECKING:
    from web.api.job_manager import Job, JobEventBus


class WebSocketProgressReporter:
    """application.progress.ProgressReporter 프로토콜 구현체.

    stage_start/progress 와 명시적 check_cancel() 에서 job.cancel_requested 를 검사해
    JobCancelled 를 raise. 장기 LLM 루프는 단계 경계가 없으므로 stage_runner 가
    루프 반복마다 `reporter.check_cancel()` 을 직접 호출해야 취소가 즉시 반영된다.
    """

    def __init__(self, job_id: str, event_bus: JobEventBus, job: Job) -> None:
        self._job_id = job_id
        self._bus = event_bus
        self._job = job

    def check_cancel(self) -> None:
        if self._job.cancel_requested:
            raise JobCancelled(f"job {self._job_id} cancelled by user")

    # 하위 호환 — 기존 내부 호출자 보존
    _check_cancel = check_cancel

    def stage_start(self, stage: str, total: int | None = None) -> None:
        self.check_cancel()
        event: dict[str, Any] = {
            "type": "stage_start",
            "stage": stage,
            "total": total,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }
        self._job.progress.append(event)
        self._bus.emit(self._job_id, event)

    def stage_progress(self, current: int, detail: str = "") -> None:
        self.check_cancel()
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
