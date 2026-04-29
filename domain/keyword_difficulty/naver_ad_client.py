"""네이버 검색광고 API - 키워드도구 클라이언트.

월간 검색량 (PC + 모바일) + 경쟁 강도 조회. 무료 API. 분 60회 한도.

인증: HMAC SHA256 서명. 헤더 4개 (X-Timestamp / X-API-KEY / X-Customer / X-Signature).
서명 메시지: "{timestamp_ms}.{HTTP_METHOD}.{URI_PATH}"

엔드포인트: GET /keywordstool?hintKeywords={keyword}
응답: { keywordList: [{ relKeyword, monthlyPcQcCnt, monthlyMobileQcCnt, compIdx }, ...] }

실패 시 None 반환 (분석은 계속 진행 — 정책 결정 (b)).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from config.settings import settings
from domain.common.usage import ApiUsage, record_usage
from domain.keyword_difficulty.model import SearchVolume

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.searchad.naver.com"
_KEYWORDSTOOL_PATH = "/keywordstool"
_TIMEOUT_SEC = 10.0


def get_search_volume(keyword: str) -> SearchVolume | None:
    """네이버 검색광고 API 로 월간 검색량 조회. 실패 시 None.

    인증 정보 누락 / 네트워크 오류 / API 응답 비정상 모두 None 반환 (warning 로깅).
    분석 파이프라인은 검색량 None 일 때도 정상 완료된다 (정책 (b)).
    """
    api_key = settings.naver_ad_api_key
    secret_key = settings.naver_ad_secret_key
    customer_id = settings.naver_ad_customer_id
    if not (api_key and secret_key and customer_id):
        logger.debug("naver_ad: 환경 변수 미설정 — 검색량 조회 스킵")
        return None

    timestamp = str(int(time.time() * 1000))
    signature = _sign(timestamp, "GET", _KEYWORDSTOOL_PATH, secret_key)
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature,
    }
    params = {"hintKeywords": keyword, "showDetail": "1"}

    try:
        with httpx.Client(timeout=_TIMEOUT_SEC) as client:
            resp = client.get(_BASE_URL + _KEYWORDSTOOL_PATH, params=params, headers=headers)
        record_usage(ApiUsage(provider="naver_searchad", model="keywordstool"))
        if resp.status_code != 200:
            logger.warning(
                "naver_ad.keywordstool status=%d body=%s", resp.status_code, resp.text[:200]
            )
            return None
        data: dict[str, Any] = resp.json()
    except Exception:
        logger.warning("naver_ad.keywordstool 호출 실패 keyword=%s", keyword, exc_info=True)
        return None

    return _pick_volume_for_keyword(data, keyword)


def _sign(timestamp: str, method: str, uri: str, secret: str) -> str:
    """HMAC SHA256 서명 생성. 메시지 = `{timestamp}.{method}.{uri}` (uri 는 query 제외)."""
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _pick_volume_for_keyword(data: dict[str, Any], keyword: str) -> SearchVolume | None:
    """응답의 keywordList 에서 입력 키워드와 정확히 일치하는 항목을 찾아 SearchVolume 으로 변환.

    정확 일치 항목이 없으면 첫 번째 항목 폴백 (네이버가 키워드 정규화로 미세하게 다른 표기를
    돌려주는 케이스 대응). 일치 항목 자체가 0개면 None.
    """
    rows = data.get("keywordList") or []
    if not rows:
        return None

    target = _normalize(keyword)
    chosen: dict[str, Any] | None = None
    for row in rows:
        rel = row.get("relKeyword", "")
        if isinstance(rel, str) and _normalize(rel) == target:
            chosen = row
            break
    if chosen is None:
        chosen = rows[0]

    return SearchVolume(
        monthly_pc=_to_int(chosen.get("monthlyPcQcCnt")),
        monthly_mobile=_to_int(chosen.get("monthlyMobileQcCnt")),
        competition_idx=chosen.get("compIdx") if isinstance(chosen.get("compIdx"), str) else None,
    )


def _to_int(raw: Any) -> int:
    """네이버 응답의 검색량은 보통 int 지만 한 자릿수는 `< 10` 같은 문자열로 옴.

    숫자로 변환 가능하면 그대로, "< 10" 같은 형태는 5 (대략값) 로 정규화, 그 외는 0.
    """
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if s.isdigit():
            return int(s)
        if "<" in s or "%" in s:
            # "< 10" 또는 "<10" 형태 — 절반값으로 추정
            return 5
    return 0


def _normalize(s: str) -> str:
    """공백·특수문자 제거 후 소문자 비교."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _build_url_with_params(path: str, params: dict[str, str]) -> str:
    """디버깅용 — query string 포함 URL. 서명에는 포함하지 않는다."""
    qs = "&".join(f"{quote(k)}={quote(v)}" for k, v in params.items())
    return f"{_BASE_URL}{path}?{qs}"
