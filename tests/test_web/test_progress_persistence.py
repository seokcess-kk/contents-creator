"""Phase J2 PR3 — JobEventBus.emit 의 progress_events 영속화 회귀.

검증 대상:
1. flag off → append_progress_event 호출 0
2. flag on → emit 마다 1 호출, seq 가 0,1,2,... 자동 부여
3. fire-and-forget 실패 graceful — emit 자체는 정상 종결
4. WebSocket subscriber 동작 무영향 (격리 보호)
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from web.api.job_manager import JobEventBus


class TestEmitFlagOff:
    def test_no_persist_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", False)
        append_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.append_progress_event", append_mock)

        bus = JobEventBus()
        bus.emit("job-1", {"type": "stage_start", "stage": "crawl"})
        bus.emit("job-1", {"type": "stage_progress", "current": 1, "total": 7})

        assert append_mock.call_count == 0
        # in-memory history 는 정상 누적
        assert len(bus.get_history("job-1")) == 2


class TestEmitFlagOn:
    def test_persists_with_auto_seq(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        append_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.append_progress_event", append_mock)

        bus = JobEventBus()
        bus.emit("job-1", {"type": "stage_start", "stage": "crawl"})
        bus.emit("job-1", {"type": "stage_progress", "current": 1})
        bus.emit("job-1", {"type": "stage_end", "stage": "crawl"})

        assert append_mock.call_count == 3
        # seq 가 0,1,2 자동 부여 (history 누적 길이)
        seqs = [c.args[1] for c in append_mock.call_args_list]
        assert seqs == [0, 1, 2]
        # 첫 호출의 event payload 검증
        first = append_mock.call_args_list[0]
        assert first.args[0] == "job-1"
        assert first.args[2] == {"type": "stage_start", "stage": "crawl"}

    def test_seq_per_job_id_independent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        append_mock = MagicMock(return_value=True)
        monkeypatch.setattr("web.api.job_manager.job_store.append_progress_event", append_mock)

        bus = JobEventBus()
        bus.emit("job-A", {"type": "x"})
        bus.emit("job-B", {"type": "y"})
        bus.emit("job-A", {"type": "z"})

        per_job_seqs: dict[str, list[int]] = {}
        for c in append_mock.call_args_list:
            per_job_seqs.setdefault(c.args[0], []).append(c.args[1])
        assert per_job_seqs["job-A"] == [0, 1]
        assert per_job_seqs["job-B"] == [0]


class TestEmitPersistFailureGraceful:
    def test_append_exception_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        # 매번 raise 해도 emit 자체는 정상 종결
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event",
            MagicMock(side_effect=RuntimeError("PK collision")),
        )

        bus = JobEventBus()
        # 예외 전파 없이 정상 반환 + history 정상 누적
        bus.emit("job-1", {"type": "x"})
        bus.emit("job-1", {"type": "y"})
        assert len(bus.get_history("job-1")) == 2


class TestEmitWebSocketIsolation:
    def test_subscriber_receives_event_with_persist_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WS 구독자 동작이 persist 분기와 무관해야 한다 (격리)."""
        monkeypatch.setattr("config.settings.settings.job_persistence_enabled", True)
        monkeypatch.setattr(
            "web.api.job_manager.job_store.append_progress_event", MagicMock(return_value=True)
        )

        async def _scenario() -> dict:
            loop = asyncio.get_running_loop()
            bus = JobEventBus()
            bus.set_loop(loop)
            queue = bus.subscribe("job-1")
            bus.emit("job-1", {"type": "stage_start"})
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            bus.unsubscribe("job-1", queue)
            return event

        ev = asyncio.run(_scenario())
        assert ev == {"type": "stage_start"}
