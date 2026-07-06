# 하이브리드 본문 fetch — primary(insane) 실패 시 fallback(BrightData) 자동 폴백.
"""FallbackFetcher — HtmlFetcher 2개를 primary→fallback 으로 합성한 어댑터.

- `primary.fetch` 가 `(InsaneFetchError, BrightDataError)` 로 실패하면 `fallback.fetch`
  로 넘긴다. fallback(BrightDataClient)도 실패하면 그 BrightDataError 를 **그대로 전파**
  한다 (최종 실패를 삼키지 않는다 → page_scraper 의 except BrightDataError 가 포착).
- **usage 이중집계 차단**: 폴백 발생 시 `record_usage` 를 호출하지 않고 `logger.warning`
  만 남긴다. 성공 usage 는 primary(insane) 또는 fallback(BrightDataClient)이 각자 기록.
  폴백률은 `provider=brightdata + stage=page_scraping` usage 분포로 추론한다.
- `close()`·`__exit__` 는 primary·fallback 양쪽에 위임한다.
"""

from __future__ import annotations

import logging

from domain.crawler.brightdata_client import BrightDataError
from domain.crawler.fetcher import HtmlFetcher
from domain.crawler.insane_fetcher import InsaneFetchError

logger = logging.getLogger(__name__)


class FallbackFetcher:
    """primary→fallback HtmlFetcher 합성. HtmlFetcher 4종 구현."""

    def __init__(self, primary: HtmlFetcher, fallback: HtmlFetcher) -> None:
        self._primary = primary
        self._fallback = fallback

    def fetch(self, url: str) -> str:
        """primary 로 fetch 시도, 실패 시 fallback 으로 폴백. record_usage 는 호출 안 함."""
        try:
            return self._primary.fetch(url)
        except (InsaneFetchError, BrightDataError) as exc:
            logger.warning(
                "본문 fetch 폴백 발생 — primary 실패, fallback 사용. url=%s reason=%s",
                url,
                exc,
            )
            return self._fallback.fetch(url)

    def close(self) -> None:
        try:
            self._primary.close()
        finally:
            self._fallback.close()

    def __enter__(self) -> FallbackFetcher:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
