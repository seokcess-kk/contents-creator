"""API 사용량 데이터 모델 + contextvars 기반 누적기.

도메인 함수는 API 호출 후 `record_usage()` 로 사용량을 기록하고,
application 레이어는 `collect_usage()` 로 단계별 사용량을 수확한다.

도메인 함수의 시그니처·반환 모델을 변경하지 않는다.
"""

from __future__ import annotations

import contextvars

from pydantic import BaseModel


class ApiUsage(BaseModel):
    """단일 API 호출의 사용량."""

    provider: str  # "anthropic" | "gemini" | "brightdata"
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 1


_usage_var: contextvars.ContextVar[list[ApiUsage]] = contextvars.ContextVar(
    "api_usage_accumulator"
)


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
