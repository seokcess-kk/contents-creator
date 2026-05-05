"""scripts/run_batch.py — Phase 3 PR2 cron 시간대 게이트 단위 테스트.

`_is_overnight_window` 만 검증 — argparse / orchestrator 호출은 다른 테스트가 커버.
실제 시각 의존을 피하려고 datetime 을 mock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from scripts.run_batch import _is_overnight_window

_KST = timezone(timedelta(hours=9))


def test_batch_id_bypass_gate() -> None:
    """운영자 명시 batch_id 트리거 — 시간대 무관 True."""
    fake_now = datetime(2026, 5, 5, 14, 0, tzinfo=_KST)  # 14시 KST
    with patch("scripts.run_batch.datetime") as dt:
        dt.now.return_value = fake_now
        assert _is_overnight_window(batch_id="b-1") is True


def test_force_env_bypass_gate() -> None:
    """BATCH_OVERNIGHT_FORCE=true — 시간대 무관 True."""
    fake_now = datetime(2026, 5, 5, 14, 0, tzinfo=_KST)
    with (
        patch("scripts.run_batch.datetime") as dt,
        patch("scripts.run_batch.settings") as st,
    ):
        dt.now.return_value = fake_now
        st.batch_overnight_force = True
        st.batch_overnight_hour_kst = 22
        assert _is_overnight_window(batch_id=None) is True


def test_within_window_returns_true() -> None:
    """현재 KST 시각이 활성 시간 == True."""
    fake_now = datetime(2026, 5, 5, 22, 0, tzinfo=_KST)
    with (
        patch("scripts.run_batch.datetime") as dt,
        patch("scripts.run_batch.settings") as st,
    ):
        dt.now.return_value = fake_now
        st.batch_overnight_force = False
        st.batch_overnight_hour_kst = 22
        assert _is_overnight_window(batch_id=None) is True


def test_outside_window_returns_false() -> None:
    """비활성 시간대 — False (cron 호출 시 noop)."""
    fake_now = datetime(2026, 5, 5, 14, 0, tzinfo=_KST)
    with (
        patch("scripts.run_batch.datetime") as dt,
        patch("scripts.run_batch.settings") as st,
    ):
        dt.now.return_value = fake_now
        st.batch_overnight_force = False
        st.batch_overnight_hour_kst = 22
        assert _is_overnight_window(batch_id=None) is False
