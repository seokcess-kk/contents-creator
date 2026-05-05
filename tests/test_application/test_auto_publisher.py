"""application/auto_publisher — Phase 4 PR2 publication 자동 등록 (opt-in).

storage 와 ranking_orchestrator.register_publication 을 mock 해 use case 동작만
검증. 실제 Supabase / SERP 호출 0건.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from application import auto_publisher
from domain.batch.model import KeywordBatch, KeywordBatchItem
from domain.ranking.model import Publication


def _batch(**overrides: object) -> KeywordBatch:
    base: dict[str, object] = {"id": "b-1", "total_count": 3, "auto_publish_enabled": True}
    base.update(overrides)
    return KeywordBatch(**base)  # type: ignore[arg-type]


def _item(**overrides: object) -> KeywordBatchItem:
    base: dict[str, object] = {
        "id": "i-1",
        "batch_id": "b-1",
        "keyword": "kw",
        "operation": "pipeline",
        "status": "ready_to_publish",
    }
    base.update(overrides)
    return KeywordBatchItem(**base)  # type: ignore[arg-type]


def _pub(**overrides: object) -> Publication:
    base: dict[str, object] = {
        "id": "pub-1",
        "keyword": "kw",
        "url": "https://blog.naver.com/example/123",
    }
    base.update(overrides)
    return Publication(**base)  # type: ignore[arg-type]


def test_disabled_returns_skipped_reason() -> None:
    """auto_publish_enabled=False 인 batch — 즉시 noop, register 호출 0."""
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch(auto_publish_enabled=False)
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["skipped_reason"] == "auto_publish_disabled"
    assert result["registered"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 0
    ro.register_publication.assert_not_called()


def test_missing_batch_raises_value_error() -> None:
    with patch("application.auto_publisher.storage") as st:
        st.get_batch.return_value = None
        with pytest.raises(ValueError, match="batch 미존재"):
            auto_publisher.auto_publish_ready_items("missing")


def test_no_target_url_skipped() -> None:
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [_item(id="i-1", target_url=None)]
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["registered"] == 0
    assert result["skipped"] == 1
    assert result["items"][0]["reason"] == "no_target_url"
    ro.register_publication.assert_not_called()


def test_already_linked_skipped() -> None:
    """publication_id 채워진 item 은 skipped (멱등 — 두 번째 호출 또는 백필 결과)."""
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [
            _item(
                id="i-1",
                target_url="https://blog.naver.com/example/123",
                publication_id="pub-existing",
            )
        ]
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["skipped"] == 1
    assert result["items"][0]["reason"] == "already_linked"
    ro.register_publication.assert_not_called()


def test_eligible_item_calls_register_publication() -> None:
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [
            _item(
                id="i-1",
                target_url="https://blog.naver.com/example/123",
                job_id="batch-i-1-abc",
            )
        ]
        ro.register_publication.return_value = _pub(id="pub-new")
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["registered"] == 1
    assert result["skipped"] == 0
    ro.register_publication.assert_called_once()
    # 인자 검증 — keyword/url/job_id 전달
    kwargs = ro.register_publication.call_args.kwargs
    assert kwargs["keyword"] == "kw"
    assert kwargs["url"] == "https://blog.naver.com/example/123"
    assert kwargs["job_id"] == "batch-i-1-abc"
    # 결과에 publication_id 포함
    assert result["items"][0]["publication_id"] == "pub-new"


def test_register_value_error_marks_failed() -> None:
    """register_publication 이 ValueError raise (URL 형식 오류) → failed."""
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [
            _item(id="i-1", target_url="https://invalid-domain.com/x"),
        ]
        ro.register_publication.side_effect = ValueError("네이버 블로그 URL 아님")
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["failed"] == 1
    assert "ValueError" in result["items"][0]["reason"]


def test_unexpected_exception_marks_failed_not_raised() -> None:
    """register_publication 이 예기치 못한 예외 → failed, 본 함수는 raise 안 함."""
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [
            _item(id="i-1", target_url="https://blog.naver.com/example/1"),
            _item(id="i-2", target_url="https://blog.naver.com/example/2", keyword="kw2"),
        ]
        # 첫 번째만 실패, 두 번째는 성공 — 둘 다 처리되는지 검증 (배치 처리 robust)
        ro.register_publication.side_effect = [
            RuntimeError("supabase down"),
            _pub(id="pub-2", url="https://blog.naver.com/example/2", keyword="kw2"),
        ]
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["registered"] == 1
    assert result["failed"] == 1
    # 결과 순서 확인 — 두 item 모두 결과에 포함
    assert len(result["items"]) == 2


def test_mixed_batch_aggregates_correctly() -> None:
    """target_url 없음 / 이미 링크 / 정상 등록 / 실패 — 4 종 mix 집계 검증."""
    with (
        patch("application.auto_publisher.storage") as st,
        patch("application.auto_publisher.ranking_orchestrator") as ro,
    ):
        st.get_batch.return_value = _batch()
        st.list_items.return_value = [
            _item(id="i-1", target_url=None),  # skipped: no_target_url
            _item(
                id="i-2",
                target_url="https://blog.naver.com/example/2",
                publication_id="pub-old",
            ),  # skipped: already_linked
            _item(id="i-3", target_url="https://blog.naver.com/example/3"),  # registered
            _item(id="i-4", target_url="https://blog.naver.com/example/4"),  # failed
        ]
        ro.register_publication.side_effect = [
            _pub(id="pub-3", url="https://blog.naver.com/example/3"),
            ValueError("URL 오류"),
        ]
        result = auto_publisher.auto_publish_ready_items("b-1")
    assert result["registered"] == 1
    assert result["skipped"] == 2
    assert result["failed"] == 1
    # 결과 sequence 보존
    reasons = [r["result"] for r in result["items"]]
    assert reasons == ["skipped", "skipped", "registered", "failed"]


_: Any = None
