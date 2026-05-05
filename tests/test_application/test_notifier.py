"""application/notifier — Slack webhook 알림 unit 테스트.

webhook URL 미설정 → 모든 함수 noop. 설정 시 requests.post 1회 호출 + JSON
payload 의 핵심 필드 검증. 외부 통신 실패 시 logger.warning 로 흡수, raise X.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from application import notifier
from domain.batch.model import KeywordBatch, KeywordBatchItem


def _batch(**overrides: object) -> KeywordBatch:
    base: dict[str, object] = {"id": "b-1", "total_count": 5, "name": "야간-1"}
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "다이어트 한의원",
        "operation": "pipeline",
        "status": "needs_review",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def test_send_text_noop_when_webhook_missing() -> None:
    """webhook URL 미설정 시 requests.post 호출 0."""
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = None
        notifier.send_text("test")
    req.post.assert_not_called()


def test_send_text_calls_webhook_when_set() -> None:
    """webhook 설정 시 requests.post 호출 + payload 에 text 포함."""
    response = MagicMock(status_code=200)
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = response
        notifier.send_text("hello")
    req.post.assert_called_once()
    kwargs = req.post.call_args.kwargs
    assert kwargs["json"] == {"text": "hello"}
    assert kwargs["timeout"] == 5.0


def test_send_text_swallows_exceptions() -> None:
    """requests.post 가 raise 해도 본 함수는 raise 안 함 (graceful)."""
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.side_effect = RuntimeError("network down")
        # 예외 발생하지 않아야 함
        notifier.send_text("hello")


def test_send_text_swallows_http_error() -> None:
    """4xx/5xx 응답도 logger.warning 으로 흡수."""
    response = MagicMock(status_code=500, text="server error")
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = response
        notifier.send_text("hello")  # raise 안 함


def test_send_batch_completed_includes_counters() -> None:
    counters = {
        "ready_to_publish_count": 7,
        "needs_review_count": 2,
        "succeeded_count": 1,
        "failed_count": 0,
        "skipped_count": 0,
    }
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = MagicMock(status_code=200)
        notifier.send_batch_completed(_batch(estimated_cost_usd=1.23), counters)
    text = req.post.call_args.kwargs["json"]["text"]
    assert "ready_to_publish" in text
    assert "7" in text
    assert "needs_review" in text
    assert "$1.23" in text


def test_send_batch_failed_includes_reason() -> None:
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = MagicMock(status_code=200)
        notifier.send_batch_failed(_batch(), reason="all 5 items failed")
    text = req.post.call_args.kwargs["json"]["text"]
    assert "배치 실패" in text
    assert "all 5 items failed" in text


def test_send_compliance_violation_respects_toggle() -> None:
    """slack_notify_compliance_violations=False 일 때 noop."""
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        st.slack_notify_compliance_violations = False
        notifier.send_compliance_violation(_item(), ["효과 과장"])
    req.post.assert_not_called()


def test_send_compliance_violation_includes_categories() -> None:
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        st.slack_notify_compliance_violations = True
        req.post.return_value = MagicMock(status_code=200)
        notifier.send_compliance_violation(_item(), ["효과 과장", "1인칭 홍보"])
    text = req.post.call_args.kwargs["json"]["text"]
    assert "다이어트 한의원" in text
    assert "효과 과장" in text
    assert "1인칭 홍보" in text


def test_send_overnight_dispatched_skips_when_zero_items() -> None:
    """dispatched_items=0 → noop (운영 노이즈 회피)."""
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        notifier.send_overnight_dispatched(0, 0)
    req.post.assert_not_called()


def test_send_overnight_dispatched_includes_counts() -> None:
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = MagicMock(status_code=200)
        notifier.send_overnight_dispatched(2, 17)
    text = req.post.call_args.kwargs["json"]["text"]
    assert "batches=2" in text
    assert "items=17" in text


def test_send_review_queue_threshold_skips_when_zero() -> None:
    """needs_review_count == 0 또는 threshold <= 0 → noop."""
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        notifier.send_review_queue_threshold(_batch(), 0, 5)
        notifier.send_review_queue_threshold(_batch(), 7, 0)
    req.post.assert_not_called()


def test_send_review_queue_threshold_includes_counts() -> None:
    with (
        patch("application.notifier.settings") as st,
        patch("application.notifier.requests") as req,
    ):
        st.slack_webhook_url = "https://hooks.slack.com/services/xxx"
        req.post.return_value = MagicMock(status_code=200)
        notifier.send_review_queue_threshold(_batch(), 12, 10)
    text = req.post.call_args.kwargs["json"]["text"]
    assert "검수 큐 누적 임계" in text
    assert "12" in text
    assert "10" in text


# ── all sentinel coverage ──


def test_module_exports_complete() -> None:
    """__all__ 정합성 — 외부에서 사용하는 함수 전부 export."""
    expected: set[str] = {
        "send_text",
        "send_batch_completed",
        "send_batch_failed",
        "send_compliance_violation",
        "send_overnight_dispatched",
        "send_review_queue_threshold",
    }
    assert set(notifier.__all__) == expected


# 타입 힌트 회피용 (mypy/pyright 가 unused 경고 안 내도록)
_: Any = None
