"""Anthropic SDK 공용 헬퍼.

모든 LLM 호출이 동일한 timeout·재시도 정책을 공유하도록 한 곳에 정의.

- httpx.Timeout(read=180s, connect=10s) — NSSM 서비스의 job_timeout_seconds(3600s)
  보다 훨씬 짧게 두어 네트워크 지연을 조기에 감지한다.
- tenacity 로 transient 에러(APITimeoutError, RateLimitError, 429/529 등)에 대해
  exponential backoff 3회 재시도.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic
import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import require

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(180.0, connect=10.0)
_RETRY_STOP_AFTER = 3
_RETRY_WAIT_MIN = 2.0  # seconds
_RETRY_WAIT_MAX = 30.0

# 재시도 대상 상태 코드 (Anthropic 공통 transient).
_RETRY_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504, 529})


def _is_transient(exc: BaseException) -> bool:
    """네트워크/서버 일시 장애인지 판정."""
    if isinstance(exc, anthropic.APITimeoutError | anthropic.APIConnectionError):
        return True
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return int(getattr(exc, "status_code", 0)) in _RETRY_STATUS_CODES
    return False


def _log_retry(retry_state: Any) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "anthropic.retry attempt=%d err=%s",
        retry_state.attempt_number,
        type(exc).__name__ if exc else "unknown",
    )


def build_client() -> anthropic.Anthropic:
    """타임아웃이 명시된 Anthropic 클라이언트 생성."""
    return anthropic.Anthropic(
        api_key=require("anthropic_api_key"),
        timeout=_DEFAULT_TIMEOUT,
    )


def messages_create_with_retry(client: anthropic.Anthropic, **kwargs: Any) -> Any:
    """`client.messages.create(**kwargs)` + 재시도.

    모든 Anthropic 호출의 단일 진입점. timeout + exponential backoff 3회.
    """

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(_RETRY_STOP_AFTER),
        wait=wait_exponential(multiplier=_RETRY_WAIT_MIN, min=_RETRY_WAIT_MIN, max=_RETRY_WAIT_MAX),
        reraise=True,
        before_sleep=_log_retry,
    )
    def _call() -> Any:
        return client.messages.create(**kwargs)

    return _call()
