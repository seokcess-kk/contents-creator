"""Phase J2 — Supabase jobs 테이블 CRUD (영속화 레이어).

`web/api/job_manager.JobManager._jobs` (in-memory dict) 의 영속 백업. 컨테이너
재시작 시 in-memory 가 휘발해도 DB 가 정본이라 GET /api/jobs/{id} 가 200 OK
+ status=orphaned 로 자연 종결 가능.

graceful degrade 정책: 모든 함수는 Supabase 미설정 / 호출 실패 시 `logger.warning`
흡수 + caller 에게 None / False / 0 반환. **본 흐름 차단 금지** — 알림 끊겨도
파이프라인은 동작해야 한다는 운영 철학 (notifier.py 패턴 그대로).

feature flag: caller (`job_manager`) 가 `settings.job_persistence_enabled` 분기.
flag off 면 본 모듈 자체 호출 X. 본 모듈은 항상 동작 시도하는 dumb storage.

domain/batch/storage.py 의 코드 스타일을 그대로 복제 (격리 도메인 정신).
다만 본 파일은 `web/api/` 영역 — JobManager 와 함께 운영되는 인프라 레이어.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from config.supabase import get_client

logger = logging.getLogger(__name__)

_JOBS_TABLE = "jobs"
_PROGRESS_TABLE = "progress_events"


# ── 1) 생성 ─────────────────────────────────────────────────────────────


def insert_job(
    job_id: str,
    *,
    job_type: str,
    keyword: str = "",
    params: dict[str, Any] | None = None,
    instance_id: str | None = None,
) -> bool:
    """submit 시점에 1회 호출 — pending row 생성. 동기 호출 (transactional).

    실패 시 logger.warning + False 반환. caller 가 in-memory only 로 강등.
    """
    payload: dict[str, Any] = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "keyword": keyword,
        "params": params or {},
    }
    if instance_id is not None:
        payload["instance_id"] = instance_id
    try:
        get_client().table(_JOBS_TABLE).insert(payload).execute()
    except Exception:
        logger.warning("job_store.insert_job failed job_id=%s", job_id, exc_info=True)
        return False
    return True


# ── 2) 조회 ─────────────────────────────────────────────────────────────


def get_job(job_id: str) -> dict[str, Any] | None:
    """단건 조회 — in-memory miss 시 GET /api/jobs/{id} 의 fallback.

    실패 시 None (404 처리는 caller).
    """
    try:
        result = get_client().table(_JOBS_TABLE).select("*").eq("id", job_id).limit(1).execute()
    except Exception:
        logger.warning("job_store.get_job failed job_id=%s", job_id, exc_info=True)
        return None
    rows = result.data or []
    return cast("dict[str, Any]", rows[0]) if rows else None


# ── 3) 상태 갱신 ────────────────────────────────────────────────────────


def update_job_status(
    job_id: str,
    status: str,
    *,
    error: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    result: dict[str, Any] | None = None,
) -> bool:
    """status 머신 + 메타 partial update. None 인자는 변경 안 함.

    job_manager 의 4지점 (`_run_job` running/succeeded/failed, `_arm_timeout`
    timed_out, `cancel_job` cancelled) 에서 호출. 모두 fire-and-forget.
    """
    payload: dict[str, Any] = {"status": status}
    if error is not None:
        payload["error"] = error
    if started_at is not None:
        payload["started_at"] = started_at.isoformat()
    if finished_at is not None:
        payload["finished_at"] = finished_at.isoformat()
    if result is not None:
        payload["result"] = result
    try:
        get_client().table(_JOBS_TABLE).update(payload).eq("id", job_id).execute()
    except Exception:
        logger.warning(
            "job_store.update_job_status failed job_id=%s status=%s",
            job_id,
            status,
            exc_info=True,
        )
        return False
    return True


def update_heartbeat(job_id: str) -> bool:
    """running job 의 last_heartbeat 갱신. 30초 daemon thread 가 호출 (PR3).

    sweep 이 stale 검출하지 않도록 주기적 갱신. status 가 이미 terminal 이면
    update 자체는 성공하지만 의미 없음 — caller 가 thread 정리.
    """
    try:
        get_client().table(_JOBS_TABLE).update(
            {"last_heartbeat": datetime.now(UTC).isoformat()}
        ).eq("id", job_id).execute()
    except Exception:
        logger.warning("job_store.update_heartbeat failed job_id=%s", job_id, exc_info=True)
        return False
    return True


# ── 4) progress_events ──────────────────────────────────────────────────


def append_progress_event(job_id: str, seq: int, event: dict[str, Any]) -> bool:
    """진행 이벤트 1건 append. PK (job_id, seq) — 같은 seq 두 번 insert 시 충돌.

    fire-and-forget. JobEventBus.emit 에서 호출 (PR3). 실패는 logger.warning.
    """
    try:
        get_client().table(_PROGRESS_TABLE).insert(
            {"job_id": job_id, "seq": seq, "event": event}
        ).execute()
    except Exception:
        logger.warning(
            "job_store.append_progress_event failed job_id=%s seq=%s",
            job_id,
            seq,
            exc_info=True,
        )
        return False
    return True


# ── 5) orphaned sweep ──────────────────────────────────────────────────


def list_orphaned_jobs(*, limit: int = 50) -> list[dict[str, Any]]:
    """status=orphaned 인 job 목록 — 운영 가시성 / 알림 메시지 구성용.

    실제 sweep 마킹은 `mark_*_as_orphaned` 가 담당. 본 함수는 단순 조회.
    """
    try:
        result = (
            get_client()
            .table(_JOBS_TABLE)
            .select("*")
            .eq("status", "orphaned")
            .order("finished_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        logger.warning("job_store.list_orphaned_jobs failed", exc_info=True)
        return []
    return [cast("dict[str, Any]", r) for r in (result.data or [])]


def mark_running_as_orphaned(*, instance_id: str) -> int:
    """startup hook 용 — 자기 instance_id 의 status=running 모두 orphaned 마킹.

    "내 컨테이너가 죽었다 살아난 것" 시나리오. 자기 instance 의 in-flight job 은
    재시작 후 in-memory 에 없으므로 모두 orphaned 처리. 다른 instance 의 job 은
    `mark_stale_running_as_orphaned` 가 heartbeat 만료로 처리.

    PostgREST eq 필터 + update 한 번으로 처리. 반환값은 마킹된 row 수.
    """
    finished = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "status": "orphaned",
        "finished_at": finished,
        "error": "container restart — in-memory state lost",
    }
    try:
        result = (
            get_client()
            .table(_JOBS_TABLE)
            .update(payload)
            .eq("instance_id", instance_id)
            .eq("status", "running")
            .execute()
        )
    except Exception:
        logger.warning(
            "job_store.mark_running_as_orphaned failed instance_id=%s",
            instance_id,
            exc_info=True,
        )
        return 0
    return len(result.data or [])


def mark_stale_running_as_orphaned(*, grace_seconds: int) -> int:
    """5분 sweep 용 — last_heartbeat 가 grace 초 이상 stale 한 running 모두 orphaned.

    instance_id 무관 — 어느 컨테이너의 job 이든 heartbeat 가 끊기면 orphaned.
    PR4 의 주기 sweep 가 호출. grace 는 settings.job_orphaned_grace_seconds (기본 300).

    PostgREST 가 `lt` 필터로 timestamp 비교 가능 — `last_heartbeat < threshold`.
    """
    threshold = (datetime.now(UTC) - timedelta(seconds=grace_seconds)).isoformat()
    finished = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "status": "orphaned",
        "finished_at": finished,
        "error": f"heartbeat stale > {grace_seconds}s",
    }
    try:
        result = (
            get_client()
            .table(_JOBS_TABLE)
            .update(payload)
            .eq("status", "running")
            .lt("last_heartbeat", threshold)
            .execute()
        )
    except Exception:
        logger.warning(
            "job_store.mark_stale_running_as_orphaned failed grace=%ss",
            grace_seconds,
            exc_info=True,
        )
        return 0
    return len(result.data or [])


__all__ = [
    "append_progress_event",
    "get_job",
    "insert_job",
    "list_orphaned_jobs",
    "mark_running_as_orphaned",
    "mark_stale_running_as_orphaned",
    "update_heartbeat",
    "update_job_status",
]
