"""API 사용량 데이터 모델 + contextvars 기반 누적기.

도메인 함수는 API 호출 후 `record_usage()` 로 사용량을 기록하고,
application 레이어는 `collect_usage()` 로 단계별 사용량을 수확한다.

도메인 함수의 시그니처·반환 모델을 변경하지 않는다.
"""

from __future__ import annotations

import contextvars
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiUsage(BaseModel):
    """단일 API 호출의 사용량."""

    provider: str  # "anthropic" | "gemini" | "brightdata"
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 1


_usage_var: contextvars.ContextVar[list[ApiUsage]] = contextvars.ContextVar("api_usage_accumulator")


def record_usage(usage: ApiUsage) -> None:
    """현재 컨텍스트에 사용량 1건 기록. 도메인 함수가 호출."""
    try:
        items = _usage_var.get()
    except LookupError:
        items = []
        _usage_var.set(items)
    items.append(usage)


def collect_usage() -> list[ApiUsage]:
    """누적된 사용량을 반환하고 초기화. application 레이어가 호출."""
    try:
        items = list(_usage_var.get())
        _usage_var.get().clear()
        return items
    except LookupError:
        return []


def reset_usage() -> None:
    """누적기 초기화. 단계 시작 전 호출."""
    _usage_var.set([])


def run_in_isolated_usage_ctx(
    fn: Callable[..., T], *args: Any, **kwargs: Any
) -> tuple[T, list[ApiUsage]]:
    """fn 을 격리된 usage 컨텍스트에서 실행하고 (결과, usage 리스트)를 반환한다.

    `ThreadPoolExecutor.submit` 워커는 부모의 ContextVar 상태를 공유하지 않으므로
    순진하게 `record_usage()` 를 호출하면 부모 `collect_usage()` 에서 누락된다.
    이 래퍼는 `contextvars.copy_context()` 로 격리된 컨텍스트를 만들고,
    fn 종료 후 수집된 usage 를 명시적으로 돌려준다. 호출자는 이 리스트를
    부모 컨텍스트에 `record_usage(u) for u in returned` 로 주입해 합친다.
    """

    def _wrapped() -> tuple[T, list[ApiUsage]]:
        reset_usage()
        result = fn(*args, **kwargs)
        usage = collect_usage()
        return result, usage

    ctx = contextvars.copy_context()
    return ctx.run(_wrapped)
