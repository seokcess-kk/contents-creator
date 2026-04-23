"""WebSocket 엔드포인트 — 실시간 파이프라인 진행률."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from web.api.auth import require_api_key_ws

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger(__name__)


def _get_manager():  # type: ignore[no-untyped-def]
    from web.api.main import job_manager

    return job_manager


@router.websocket("/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str) -> None:
    if not await require_api_key_ws(websocket):
        return
    mgr = _get_manager()
    job = mgr.get_job(job_id)
    if job is None:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()

    # 이전 이벤트 히스토리 일괄 전송 (늦게 접속한 클라이언트 지원)
    for event in mgr.event_bus.get_history(job_id):
        await websocket.send_text(json.dumps(event, default=str))

    # 이미 완료된 작업이면 히스토리만 보내고 종료
    if job.status in ("succeeded", "failed"):
        await websocket.close()
        return

    # 실시간 이벤트 구독
    queue = mgr.event_bus.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, default=str))
            # 작업 종료 이벤트면 연결 닫기
            if event.get("type") == "job_status" and event.get("status") in (
                "succeeded",
                "failed",
            ):
                break
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for job %s", job_id)
    except asyncio.CancelledError:
        pass
    finally:
        mgr.event_bus.unsubscribe(job_id, queue)
