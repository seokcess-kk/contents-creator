"""Phase J2 PR4 — startup mark_orphaned + 5min sweep + 알림 dedupe 회귀.

검증:
1. startup flag off → mark_running_as_orphaned 호출 0
2. startup flag on + DB hit count=N → 통합 메시지 (instance + orphaned=N)
3. startup flag on + DB hit count=0 → 기존 J1.4 메시지 (orphaned 부분 생략)
4. _orphaned_sweep_loop — flag off 진입 시 즉시 종료
5. _orphaned_sweep_loop — count > 0 시 notifier 알림
6. _orphaned_sweep_loop — Supabase 장애 graceful (continue)
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


# 본 파일 테스트는 매 테스트가 직접 monkeypatch + TestClient(app) 으로 lifespan
# 트리거. 공통 fixture 가 거의 없어 별도 추출 안 함.


# ── startup mark_running_as_orphaned + 알림 dedupe ──────────────────────


class TestStartupFlagOff:
    def test_does_not_call_mark_orphaned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", None)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)

        mark_mock = MagicMock(return_value=0)
        monkeypatch.setattr("web.api.main.job_store.mark_running_as_orphaned", mark_mock)
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        from web.api.main import app

        with TestClient(app):
            pass

        # flag off → mark 호출 0
        assert mark_mock.call_count == 0
        # 알림은 J1.4 형식 그대로 (orphaned 부분 생략)
        assert notify_mock.call_count >= 1
        msg = notify_mock.call_args.args[0]
        assert "백엔드 재시작 감지" in msg
        assert "orphaned" not in msg


class TestStartupFlagOnWithOrphaned:
    def test_unified_message_with_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", None)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        # sweep loop 가 즉시 시작하지 않도록 interval 매우 길게
        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 99999)

        mark_mock = MagicMock(return_value=3)
        monkeypatch.setattr("web.api.main.job_store.mark_running_as_orphaned", mark_mock)
        # mark_stale 도 mock — sweep task 가 한 tick 도 못 돌게
        monkeypatch.setattr(
            "web.api.main.job_store.mark_stale_running_as_orphaned", MagicMock(return_value=0)
        )
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        from web.api.main import app

        with TestClient(app):
            pass

        assert mark_mock.call_count == 1
        # 통합 알림 메시지에 orphaned=3 포함
        startup_msg = next(
            c.args[0] for c in notify_mock.call_args_list if "백엔드 재시작 감지" in c.args[0]
        )
        assert "orphaned=3" in startup_msg


class TestStartupFlagOnNoOrphaned:
    def test_message_omits_orphaned_when_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.ranking_scheduler_enabled", False)
        monkeypatch.setattr("config.settings.settings.admin_api_key", None)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 99999)

        monkeypatch.setattr(
            "web.api.main.job_store.mark_running_as_orphaned", MagicMock(return_value=0)
        )
        monkeypatch.setattr(
            "web.api.main.job_store.mark_stale_running_as_orphaned", MagicMock(return_value=0)
        )
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        from web.api.main import app

        with TestClient(app):
            pass

        startup_msg = next(
            c.args[0] for c in notify_mock.call_args_list if "백엔드 재시작 감지" in c.args[0]
        )
        # count=0 이면 기존 J1.4 형식 (orphaned 미포함)
        assert "orphaned" not in startup_msg


# ── _orphaned_sweep_loop ────────────────────────────────────────────────


class TestSweepLoop:
    def test_exits_when_flag_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.main import _orphaned_sweep_loop

        # 매우 짧은 interval 로 한 번 sleep 후 flag 체크
        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 60)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        mark_mock = MagicMock(return_value=0)
        monkeypatch.setattr("web.api.main.job_store.mark_stale_running_as_orphaned", mark_mock)

        async def _run() -> None:
            # asyncio.sleep 을 무력화 (즉시 반환)
            async def _no_sleep(_seconds: float) -> None:
                return None

            monkeypatch.setattr(asyncio, "sleep", _no_sleep)
            await _orphaned_sweep_loop()

        asyncio.run(asyncio.wait_for(_run(), timeout=2.0))
        # flag off 라 mark 호출 0
        assert mark_mock.call_count == 0

    def test_calls_notifier_when_count_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.main import _orphaned_sweep_loop

        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 60)
        monkeypatch.setattr("config.settings.settings.job_orphaned_grace_seconds", 300)
        # 1 tick 만 동작 후 두 번째 tick 진입에서 flag off → loop 종료.
        # flag 토글 자체는 sleep mock 안에서 처리.
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        mark_mock = MagicMock(return_value=2)
        monkeypatch.setattr("web.api.main.job_store.mark_stale_running_as_orphaned", mark_mock)
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        async def _run() -> None:
            tick_count = {"n": 0}

            async def _one_tick(_seconds: float) -> None:
                tick_count["n"] += 1
                if tick_count["n"] >= 2:
                    # 두 번째 sleep 진입 시 flag 끄기 → loop 종료
                    monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)

            monkeypatch.setattr(asyncio, "sleep", _one_tick)
            await _orphaned_sweep_loop()

        asyncio.run(asyncio.wait_for(_run(), timeout=2.0))
        assert mark_mock.call_count == 1
        mark_kwargs = mark_mock.call_args.kwargs
        assert mark_kwargs["grace_seconds"] == 300
        # count > 0 → 알림
        assert notify_mock.call_count == 1
        msg = notify_mock.call_args.args[0]
        assert "orphaned sweep" in msg
        assert "2 job(s)" in msg

    def test_no_notify_when_count_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.main import _orphaned_sweep_loop

        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 60)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        mark_mock = MagicMock(return_value=0)
        monkeypatch.setattr("web.api.main.job_store.mark_stale_running_as_orphaned", mark_mock)
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        async def _run() -> None:
            tick_count = {"n": 0}

            async def _one_tick(_seconds: float) -> None:
                tick_count["n"] += 1
                if tick_count["n"] >= 2:
                    monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)

            monkeypatch.setattr(asyncio, "sleep", _one_tick)
            await _orphaned_sweep_loop()

        asyncio.run(asyncio.wait_for(_run(), timeout=2.0))
        assert mark_mock.call_count == 1
        # count=0 → 알림 호출 0
        assert notify_mock.call_count == 0

    def test_supabase_failure_continues_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from web.api.main import _orphaned_sweep_loop

        monkeypatch.setattr("config.settings.settings.job_sweep_interval_seconds", 60)
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        # 매번 raise — graceful continue 검증
        mark_mock = MagicMock(side_effect=RuntimeError("supabase down"))
        monkeypatch.setattr("web.api.main.job_store.mark_stale_running_as_orphaned", mark_mock)
        notify_mock = MagicMock()
        monkeypatch.setattr("web.api.main.notifier.send_text", notify_mock)

        async def _run() -> None:
            tick_count = {"n": 0}

            async def _one_tick(_seconds: float) -> None:
                tick_count["n"] += 1
                if tick_count["n"] >= 3:
                    monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)

            monkeypatch.setattr(asyncio, "sleep", _one_tick)
            await _orphaned_sweep_loop()

        # 두 번 mark 시도 (1, 2) 후 종료 (3에서 flag off)
        asyncio.run(asyncio.wait_for(_run(), timeout=2.0))
        assert mark_mock.call_count == 2
        # 알림은 발송 0 (raise 내부에서 continue)
        assert notify_mock.call_count == 0
