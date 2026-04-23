"""API 사용량 비용 계산 + Supabase 저장.

도메인 함수가 `record_usage()` 로 기록한 사용량을
stage_runner 가 `collect_usage()` 로 수확한 뒤 이 모듈로 저장한다.
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from domain.common.usage import ApiUsage

logger = logging.getLogger(__name__)

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


def save_usage_to_supabase(
    usages: list[ApiUsage],
    *,
    job_id: str | None = None,
    keyword: str | None = None,
    stage: str | None = None,
) -> bool:
    """사용량 레코드들을 Supabase api_usage 테이블에 저장.

    Returns:
        True — 저장 성공 또는 Supabase 미설정(정상 스킵).
        False — 저장 시도했으나 예외 발생. 호출자가 summary 에 보고해 운영자가 인지.
    """
    if not usages:
        return True

    if not settings.supabase_url or not settings.supabase_key:
        logger.debug("Supabase 미설정, usage 저장 스킵")
        return True

    try:
        from config.supabase import get_client

        client = get_client()
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
        client.table("api_usage").insert(rows).execute()
        return True
    except Exception:
        logger.error(
            "api_usage 저장 실패 job=%s stage=%s (파이프라인은 계속)",
            job_id,
            stage,
            exc_info=True,
        )
        return False


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
