"""SPEC-BATCH §3 Phase 4 PR1 — Slack 알림 인프라.

웹훅 미설정 (`SLACK_WEBHOOK_URL` env 부재) 시 모든 함수는 즉시 noop. 외부 통신
실패도 graceful — `logger.warning` 로 흡수하고 본 흐름 영향 없음. 알림이 끊겨도
파이프라인 자체는 정상 동작해야 한다는 운영 철학.

호출 흐름:
- `application.batch_orchestrator._dispatch_item` — 의료법 위반 단건 알림
- `application.batch_orchestrator.recompute_batch_status` — 배치 완료 요약 / 전체 실패
- `application.batch_orchestrator.dispatch_overnight_batches` — 야간 시작/종료

테스트는 `requests.post` 를 mock 해 호출 횟수와 payload 만 검증한다.
"""

from __future__ import annotations

import logging

import requests

from config.settings import settings
from domain.batch.model import KeywordBatch, KeywordBatchItem

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0


def send_text(message: str) -> None:
    """단순 텍스트 알림. webhook 미설정 시 noop."""
    webhook = settings.slack_webhook_url
    if not webhook:
        return
    payload = {"text": message}
    try:
        response = requests.post(webhook, json=payload, timeout=_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            logger.warning(
                "notifier.slack.http_error status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
    except Exception:
        logger.warning("notifier.slack.send_failed", exc_info=True)


def send_batch_completed(batch: KeywordBatch, counters: dict[str, int]) -> None:
    """배치 완료 요약 — ready_to_publish / needs_review / failed 카운터 + 추정 비용.

    `auto_publish_enabled=true` 면 자동 발행 안내 추가.
    """
    if not settings.slack_webhook_url:
        return
    name = batch.name or f"batch-{batch.id}"
    lines = [
        f"*배치 완료* — {name}",
        f"  ready_to_publish : {counters.get('ready_to_publish_count', 0)}",
        f"  needs_review     : {counters.get('needs_review_count', 0)}",
        f"  succeeded        : {counters.get('succeeded_count', 0)}",
        f"  failed           : {counters.get('failed_count', 0)}",
        f"  skipped          : {counters.get('skipped_count', 0)}",
        f"  estimated_cost   : ${batch.estimated_cost_usd:.2f}",
    ]
    send_text("\n".join(lines))


def send_batch_failed(batch: KeywordBatch, reason: str) -> None:
    """배치 전체 실패 즉시 알림."""
    if not settings.slack_webhook_url:
        return
    name = batch.name or f"batch-{batch.id}"
    send_text(f":rotating_light: *배치 실패* — {name}\n사유: {reason}")


def send_compliance_violation(item: KeywordBatchItem, categories: list[str]) -> None:
    """의료법 위반 단건 알림 — 키워드 + 위반 카테고리.

    `slack_notify_compliance_violations=False` 면 noop (개별 알림 비활성).
    SPEC-BATCH §3 Phase 4 운영 철학상 검수 큐가 1차이므로 노이즈 회피 토글.
    """
    if not settings.slack_webhook_url:
        return
    if not settings.slack_notify_compliance_violations:
        return
    cats = ", ".join(categories) if categories else "(unspecified)"
    send_text(
        f":warning: *의료법 위반* — {item.keyword}\n"
        f"  operation : {item.operation}\n"
        f"  카테고리   : {cats}"
    )


def send_overnight_dispatched(dispatched_batches: int, dispatched_items: int) -> None:
    """야간 일괄 dispatch 시작 알림. dispatched_items=0 이면 noop."""
    if not settings.slack_webhook_url:
        return
    if dispatched_items <= 0:
        return
    send_text(
        f":new_moon: *overnight dispatch* — batches={dispatched_batches} items={dispatched_items}"
    )


__all__ = [
    "send_text",
    "send_batch_completed",
    "send_batch_failed",
    "send_compliance_violation",
    "send_overnight_dispatched",
]
