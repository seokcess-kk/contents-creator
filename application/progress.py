"""진행 리포트 프로토콜과 기본 구현.

SPEC-SEO-TEXT.md §12-3 참조.

- MVP: LoggingProgressReporter (CLI) + NullProgressReporter (테스트)
- Phase 2: WebSocketProgressReporter 를 추가 구현하면 기존 코드 변경 없이 주입 가능
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from application.models import PipelineResult


logger = logging.getLogger(__name__)


class JobCancelled(Exception):  # noqa: N818 — 제어 예외, Error 접미사 부적합
    """사용자/시스템 요청으로 실행 중인 job 이 취소되었음을 알리는 제어 예외.

    reporter 가 stage_start 호출 시 cancel_requested 플래그를 감지하면 raise.
    orchestrator 의 try/except 가 이 예외를 별도 처리해 status=cancelled 로 반환한다.
    """


class ProgressReporter(Protocol):
    """파이프라인 진행 상황 콜백 프로토콜.

    모든 stage_runner 호출자가 이 프로토콜을 주입받아 단계 경계에서 호출한다.
    구현체는 CLI 로깅, WebSocket 푸시, null 등 자유롭게 교체 가능.
    """

    def stage_start(self, stage: str, total: int | None = None) -> None:
        """단계 시작. total 은 해당 단계의 서브 항목 수 (예: 블로그 10개)."""
        ...

    def stage_progress(self, current: int, detail: str = "") -> None:
        """단계 내 진행 상황 업데이트."""
        ...

    def stage_end(self, stage: str, result_summary: dict[str, Any]) -> None:
        """단계 완료. result_summary 는 요약 정보 (소요, 성공/실패 수 등)."""
        ...

    def pipeline_complete(self, result: PipelineResult) -> None:
        """파이프라인 전체 완료."""
        ...

    def pipeline_error(self, stage: str, error: Exception) -> None:
        """파이프라인 중간 실패."""
        ...

    def check_cancel(self) -> None:
        """취소/타임아웃 폴링 지점. cancel_requested 플래그 시 JobCancelled raise.

        stage_start/progress 가 닿지 않는 장기 루프(섹션 보강, compliance 이터레이션,
        이미지 생성 반복 등) 직전에 명시적으로 호출해 협력적 취소 해상도를 높인다.
        Logging/Null 구현은 no-op.
        """
        ...


class NullProgressReporter:
    """모든 호출을 무시하는 Null Object.

    테스트와 라이브러리 사용자의 기본값.
    """

    def stage_start(self, stage: str, total: int | None = None) -> None:
        pass

    def stage_progress(self, current: int, detail: str = "") -> None:
        pass

    def stage_end(self, stage: str, result_summary: dict[str, Any]) -> None:
        pass

    def pipeline_complete(self, result: PipelineResult) -> None:
        pass

    def pipeline_error(self, stage: str, error: Exception) -> None:
        pass

    def check_cancel(self) -> None:
        pass


class LoggingProgressReporter:
    """logging 모듈로 진행 상황 출력. CLI 기본값."""

    def stage_start(self, stage: str, total: int | None = None) -> None:
        if total is not None:
            logger.info("[stage:%s] 시작 (총 %d개 항목)", stage, total)
        else:
            logger.info("[stage:%s] 시작", stage)

    def stage_progress(self, current: int, detail: str = "") -> None:
        if detail:
            logger.info("  진행 %d — %s", current, detail)
        else:
            logger.info("  진행 %d", current)

    def stage_end(self, stage: str, result_summary: dict[str, Any]) -> None:
        logger.info("[stage:%s] 완료 — %s", stage, result_summary)

    def pipeline_complete(self, result: PipelineResult) -> None:
        logger.info("[pipeline] 완료 — status=%s", result.status)

    def pipeline_error(self, stage: str, error: Exception) -> None:
        logger.error("[pipeline] 실패 at %s: %s", stage, error)

    def check_cancel(self) -> None:
        # CLI 실행에는 외부 취소 신호가 없다 (Ctrl+C 는 SIGINT 로 따로 처리).
        pass
