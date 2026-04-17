"""Bright Data 공통 HTTP 클라이언트.

SPEC-SEO-TEXT.md §3 [1][2] 의 모든 Bright Data 호출은 이 모듈을 경유한다.
개별 파일에서 `requests.post()` 를 직접 호출하지 않는다. (domain/crawler/CLAUDE.md #1)

- Web Unlocker 단일 zone 으로 SERP 페이지와 블로그 본문 모두 fetch
- 재시도: tenacity exponential backoff (2s → 5s), 최대 2회 재시도 = 총 3회 시도
- 타임아웃: 요청당 30초
"""

from __future__ import annotations

import logging

import requests

from domain.common.usage import ApiUsage, record_usage
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"
REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3  # 초기 1회 + 재시도 2회
RETRY_WAIT_MIN_SECONDS = 2
RETRY_WAIT_MAX_SECONDS = 5


class BrightDataError(RuntimeError):
    """Bright Data 호출 실패 (HTTP·네트워크·재시도 초과 포함)."""


class BrightDataClientError(BrightDataError):
    """4xx 등 재시도 의미 없는 클라이언트 에러. tenacity 재시도 대상에서 제외."""


class BrightDataTransientError(BrightDataError):
    """5xx·timeout 등 재시도 가능한 일시 에러."""


class BrightDataClient:
    """Bright Data Web Unlocker 호출 전용 클라이언트.

    사용 예:
        client = BrightDataClient(api_key=..., zone=...)
        html = client.fetch("https://search.naver.com/search.naver?query=...&where=blog")
    """

    def __init__(self, api_key: str, zone: str) -> None:
        if not api_key:
            raise ValueError("Bright Data api_key 가 비어 있습니다.")
        if not zone:
            raise ValueError("Bright Data zone 이 비어 있습니다.")
        self._api_key = api_key
        self._zone = zone
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def fetch(self, url: str) -> str:
        """Web Unlocker 로 URL 을 fetch 해 raw HTML 문자열을 반환.

        재시도 2회 후에도 실패하면 BrightDataError 를 발생시킨다.
        """
        try:
            return self._fetch_with_retry(url)
        except RetryError as exc:
            last = exc.last_attempt.exception() if exc.last_attempt else None
            raise BrightDataError(
                f"Bright Data fetch 실패 (재시도 {MAX_ATTEMPTS - 1}회 후 종료): {url}"
            ) from last

    @retry(
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN_SECONDS, max=RETRY_WAIT_MAX_SECONDS),
        retry=retry_if_exception_type((requests.RequestException, BrightDataTransientError)),
        reraise=False,
    )
    def _fetch_with_retry(self, url: str) -> str:
        payload = {"zone": self._zone, "url": url, "format": "raw"}
        logger.info("brightdata.fetch url=%s zone=%s", url, self._zone)
        try:
            response = self._session.post(
                BRIGHTDATA_ENDPOINT,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            logger.warning("brightdata.timeout url=%s", url)
            raise BrightDataTransientError(f"timeout: {url}") from exc

        if response.status_code >= 500:
            logger.warning("brightdata.5xx status=%s url=%s", response.status_code, url)
            raise BrightDataTransientError(f"server error {response.status_code}: {url}")
        if response.status_code < 400:
            record_usage(ApiUsage(provider="brightdata", model="web_unlocker"))
        if response.status_code >= 400:
            logger.error(
                "brightdata.4xx status=%s url=%s body=%s",
                response.status_code,
                url,
                response.text[:500],
            )
            raise BrightDataClientError(f"client error {response.status_code}: {url}")

        return response.text

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> BrightDataClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
