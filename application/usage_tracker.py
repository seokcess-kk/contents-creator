"""API 사용량 비용 계산 + Supabase 저장.

도메인 함수가 `record_usage()` 로 기록한 사용량을
stage_runner 가 `collect_usage()` 로 수확한 뒤 이 모듈로 저장한다.

저장 실패는 silent 가 아니어야 한다 — 2026-05-02 사고에서 ranking_snapshots 48건이
정상 INSERT 됐는데 같은 호출 사이클의 api_usage 가 0 건 (모두 실패 + except swallow)
이었던 사례 이후 retry + 명시적 ERROR + caller 인지로 보강.
"""

from __future__ import annotations

import logging
from typing import Any

from tenacity import (
    RetryError,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from domain.common.usage import ApiUsage

logger = logging.getLogger(__name__)

# Supabase 일시 장애·rate limit 흡수. 1s → 2s → 4s = 총 3 시도, 약 7 초 안에 복구 또는 포기.
_INSERT_MAX_ATTEMPTS = 3
_INSERT_WAIT_MIN = 1
_INSERT_WAIT_MAX = 4

# 모델별 비용 매핑 (USD per 1 token)
_COST_MAP: dict[str, tuple[float, float]] = {}


def _get_cost_per_token(model: str | None) -> tuple[float, float]:
    """(input_cost_per_token, output_cost_per_token) 반환.

    Note: Extended Thinking 토큰은 Anthropic 응답에서 output_tokens 에 포함되어
    반환되므로 별도 처리 불필요 (동일 단가로 과금).
    """
    if not _COST_MAP:
        # lazy init
        _COST_MAP[settings.model_opus] = (
            settings.cost_anthropic_opus_input / 1_000_000,
            settings.cost_anthropic_opus_output / 1_000_000,
        )
        _COST_MAP[settings.model_editor] = (
            settings.cost_anthropic_editor_input / 1_000_000,
            settings.cost_anthropic_editor_output / 1_000_000,
        )
        _COST_MAP[settings.model_sonnet] = (
            settings.cost_anthropic_sonnet_input / 1_000_000,
            settings.cost_anthropic_sonnet_output / 1_000_000,
        )
    if model and model in _COST_MAP:
        return _COST_MAP[model]
    return (0.0, 0.0)


def estimate_cost(usage: ApiUsage) -> float:
    """단일 ApiUsage 의 예상 비용(USD)을 계산."""
    if usage.provider == "anthropic":
        inp_cost, out_cost = _get_cost_per_token(usage.model)
        return usage.input_tokens * inp_cost + usage.output_tokens * out_cost
    if usage.provider == "gemini":
        return usage.requests * settings.cost_gemini_image_per_request
    if usage.provider == "brightdata":
        return usage.requests * settings.cost_brightdata_per_request
    return 0.0


def _build_rows(
    usages: list[ApiUsage],
    *,
    job_id: str | None,
    keyword: str | None,
    stage: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for u in usages:
        cost = estimate_cost(u)
        rows.append(
            {
                "job_id": job_id,
                "keyword": keyword,
                "stage": stage,
                "provider": u.provider,
                "model": u.model,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "requests": u.requests,
                "estimated_cost_usd": round(cost, 6),
            }
        )
    return rows


@retry(
    stop=stop_after_attempt(_INSERT_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=_INSERT_WAIT_MIN, max=_INSERT_WAIT_MAX),
    reraise=True,
)
def _insert_with_retry(rows: list[dict[str, Any]]) -> None:
    """Supabase api_usage INSERT — 일시 장애 흡수 (1s→2s→4s, 3 시도)."""
    from config.supabase import get_client

    client = get_client()
    client.table("api_usage").insert(rows).execute()


def save_usage_to_supabase(
    usages: list[ApiUsage],
    *,
    job_id: str | None = None,
    keyword: str | None = None,
    stage: str | None = None,
) -> bool:
    """사용량 레코드들을 Supabase api_usage 테이블에 저장.

    재시도 3회 후에도 실패하면 ERROR 로그 + False 반환. 호출자(orchestrator)가
    summary 의 usage_save_failed_count 에 누적해 운영자가 인지하도록 한다.

    Returns:
        True — 저장 성공 또는 Supabase 미설정·빈 입력(정상 스킵).
        False — 재시도 후에도 INSERT 실패. caller 가 summary 에 보고.
    """
    if not usages:
        return True

    if not settings.supabase_url or not settings.supabase_key:
        logger.debug("Supabase 미설정, usage 저장 스킵")
        return True

    rows = _build_rows(usages, job_id=job_id, keyword=keyword, stage=stage)

    try:
        _insert_with_retry(rows)
        return True
    except RetryError as exc:
        last = exc.last_attempt.exception() if exc.last_attempt else exc
        _log_insert_failure(rows, job_id=job_id, stage=stage, exception=last)
        return False
    except Exception as exc:
        _log_insert_failure(rows, job_id=job_id, stage=stage, exception=exc)
        return False


def _log_insert_failure(
    rows: list[dict[str, Any]],
    *,
    job_id: str | None,
    stage: str | None,
    exception: BaseException | None,
) -> None:
    """save 실패의 ERROR 로그 — 사후 진단에 필요한 정보를 모두 포함."""
    sample = rows[0] if rows else {}
    logger.error(
        "api_usage 저장 실패 — row_count=%d job=%s stage=%s exc_type=%s "
        "first_row_provider=%s first_row_keyword=%s",
        len(rows),
        job_id,
        stage,
        type(exception).__name__ if exception else "unknown",
        sample.get("provider"),
        sample.get("keyword"),
        exc_info=exception if isinstance(exception, BaseException) else None,
    )


def summarize_usages(usages: list[ApiUsage]) -> dict[str, Any]:
    """사용량 리스트를 요약 dict 로 변환 (StageResult.summary 용)."""
    total_input = sum(u.input_tokens for u in usages)
    total_output = sum(u.output_tokens for u in usages)
    total_requests = sum(u.requests for u in usages)
    total_cost = sum(estimate_cost(u) for u in usages)
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "requests": total_requests,
        "estimated_cost_usd": round(total_cost, 6),
    }
