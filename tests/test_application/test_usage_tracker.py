"""save_usage_to_supabase 보강 테스트 — 2026-05-02 silent failure 사고 회귀 방지.

- 일시 장애에서 retry 로 복구되는지
- 끝까지 실패하면 False 반환 + ERROR 로그가 row 수·exception type 포함하는지
- 빈 입력 / Supabase 미설정은 정상 True 스킵인지
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from application import usage_tracker
from domain.common.usage import ApiUsage


def _usages() -> list[ApiUsage]:
    return [
        ApiUsage(provider="brightdata", model="web_unlocker", requests=1),
        ApiUsage(provider="anthropic", model="claude-sonnet", input_tokens=100, output_tokens=50),
    ]


@pytest.fixture(autouse=True)
def _supabase_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supabase 설정 존재 가정 — 미설정 분기는 별도 테스트에서 검증."""
    monkeypatch.setattr("config.settings.settings.supabase_url", "https://x.supabase.co")
    monkeypatch.setattr("config.settings.settings.supabase_key", "test-key")


def test_save_usage_succeeds_first_attempt() -> None:
    """단순 성공 — 한 번에 INSERT, True 반환."""
    fake_client = MagicMock()
    with patch("config.supabase.get_client", return_value=fake_client):
        ok = usage_tracker.save_usage_to_supabase(
            _usages(), keyword="test-kw", stage="ranking_check"
        )
    assert ok is True
    fake_client.table.assert_called_once_with("api_usage")
    insert_call = fake_client.table.return_value.insert
    insert_call.assert_called_once()
    rows = insert_call.call_args.args[0]
    assert len(rows) == 2
    assert rows[0]["stage"] == "ranking_check"


def test_save_usage_recovers_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 호출 실패, 두 번째 성공 — retry 로 복구 + True 반환."""
    call_count = {"n": 0}

    def fake_get_client() -> MagicMock:
        call_count["n"] += 1
        client = MagicMock()
        if call_count["n"] == 1:
            client.table.return_value.insert.return_value.execute.side_effect = ConnectionError(
                "transient"
            )
        return client

    # tenacity 의 wait 를 0 으로 단축해 테스트 빠르게
    monkeypatch.setattr(usage_tracker._insert_with_retry.retry, "wait", lambda *_, **__: 0)
    with patch("config.supabase.get_client", side_effect=fake_get_client):
        ok = usage_tracker.save_usage_to_supabase(_usages(), keyword="kw", stage="ranking_check")
    assert ok is True
    assert call_count["n"] == 2  # 1차 실패 + 2차 성공


def test_save_usage_returns_false_after_all_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """3회 모두 실패 → False + ERROR 로그에 row_count·exc_type·sample 포함."""

    def fake_get_client() -> MagicMock:
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = ConnectionError(
            "persistent"
        )
        return client

    monkeypatch.setattr(usage_tracker._insert_with_retry.retry, "wait", lambda *_, **__: 0)
    with (
        caplog.at_level(logging.ERROR, logger="application.usage_tracker"),
        patch("config.supabase.get_client", side_effect=fake_get_client),
    ):
        ok = usage_tracker.save_usage_to_supabase(
            _usages(), keyword="diet-hospital", stage="ranking_check"
        )
    assert ok is False
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    msg = error_records[0].getMessage()
    # 사후 진단에 필요한 정보 모두 포함
    assert "row_count=2" in msg
    assert "stage=ranking_check" in msg
    assert "exc_type=ConnectionError" in msg
    assert "first_row_provider=brightdata" in msg
    assert "first_row_keyword=diet-hospital" in msg


def test_save_usage_skips_empty_input() -> None:
    """빈 usage 리스트 — INSERT 안 하고 True (정상 스킵)."""
    fake_client = MagicMock()
    with patch("config.supabase.get_client", return_value=fake_client):
        ok = usage_tracker.save_usage_to_supabase([], stage="ranking_check")
    assert ok is True
    fake_client.table.assert_not_called()


def test_save_usage_skips_when_supabase_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supabase 미설정 — 호출 자체 스킵, True 반환 (개발 모드)."""
    monkeypatch.setattr("config.settings.settings.supabase_url", "")
    monkeypatch.setattr("config.settings.settings.supabase_key", "")
    fake_client = MagicMock()
    with patch("config.supabase.get_client", return_value=fake_client):
        ok = usage_tracker.save_usage_to_supabase(_usages(), stage="ranking_check")
    assert ok is True
    fake_client.table.assert_not_called()


def test_build_rows_attaches_estimated_cost_and_metadata() -> None:
    """row 가 stage·keyword·job_id + 비용까지 정확히 채우는지."""
    rows = usage_tracker._build_rows(
        [ApiUsage(provider="brightdata", model="web_unlocker", requests=2)],
        job_id="job-x",
        keyword="kw",
        stage="ranking_check",
    )
    assert rows == [
        {
            "job_id": "job-x",
            "keyword": "kw",
            "stage": "ranking_check",
            "provider": "brightdata",
            "model": "web_unlocker",
            "input_tokens": 0,
            "output_tokens": 0,
            "requests": 2,
            "estimated_cost_usd": rows[0]["estimated_cost_usd"],  # cost 계산 자체는 별도 테스트
        }
    ]
    assert isinstance(rows[0]["estimated_cost_usd"], float)


def _kwargs_to_dict(call_args: Any) -> dict[str, Any]:
    return dict(call_args.kwargs)
