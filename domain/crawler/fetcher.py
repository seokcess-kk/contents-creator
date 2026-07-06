# 크롤링 fetch 추상화 — Bright Data / insane(curl_cffi) 공통 인터페이스.
"""HTML fetch 계약 Protocol.

크롤러가 상위글 HTML 을 가져올 때 의존하는 최소 인터페이스를 정의한다.
Bright Data 클라이언트(`BrightDataClient`)와 후속 어댑터(insane/curl_cffi 등)가
모두 이 구조를 구조적(structural)으로 만족하므로 명시적 상속은 불필요하다.

예외 계약 (Protocol 은 예외를 강제하지 못하므로 규약으로 명시한다):
    구현체는 `fetch` 실패 시
    `domain.crawler.brightdata_client.BrightDataError` 계열(또는 그 하위
    호환 예외)을 raise 한다. 호출부(`page_scraper`)는 `except BrightDataError`
    로 이를 포착해 URL 단위 실패로 누적한다.
"""

from __future__ import annotations

from typing import Protocol


class HtmlFetcher(Protocol):
    """URL → raw HTML 문자열 fetch + context manager 계약.

    멤버 시그니처는 `BrightDataClient` 와 일치한다. 구조적 서브타이핑으로
    `BrightDataClient` 및 후속 어댑터가 별도 상속 없이 이 Protocol 을 만족한다.
    """

    def fetch(self, url: str) -> str:
        """`url` 을 fetch 해 raw HTML 문자열 반환. 실패 시 BrightDataError 계열 raise."""
        ...

    def close(self) -> None:
        """내부 세션/리소스를 정리한다."""
        ...

    def __enter__(self) -> HtmlFetcher:
        """`with` 진입 — self 반환."""
        ...

    def __exit__(self, *exc_info: object) -> None:
        """`with` 종료 — `close()` 로 리소스 해제."""
        ...
