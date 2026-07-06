"""FallbackFetcher 단위 테스트. StubFetcher(HtmlFetcher duck-type) 사용."""

from __future__ import annotations

import pytest

from domain.common import usage as usage_mod
from domain.crawler.brightdata_client import BrightDataError, BrightDataTransientError
from domain.crawler.fallback_fetcher import FallbackFetcher
from domain.crawler.insane_fetcher import InsaneFetchError

_URL = "https://m.blog.naver.com/u/1"


class StubFetcher:
    """html 반환 또는 지정 예외 raise 하는 HtmlFetcher duck-type stub."""

    def __init__(self, *, html: str | None = None, error: Exception | None = None) -> None:
        self._html = html
        self._error = error
        self.calls = 0
        self.closed = False

    def fetch(self, url: str) -> str:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._html is not None
        return self._html

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> StubFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_primary_success_skips_fallback() -> None:
    primary = StubFetcher(html="<p>primary</p>")
    fallback = StubFetcher(html="<p>fallback</p>")
    assert FallbackFetcher(primary, fallback).fetch(_URL) == "<p>primary</p>"
    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.parametrize(
    "error",
    [InsaneFetchError("boom"), BrightDataTransientError("boom"), BrightDataError("boom")],
)
def test_primary_failure_triggers_fallback(error: Exception) -> None:
    primary = StubFetcher(error=error)
    fallback = StubFetcher(html="<p>fallback</p>")
    assert FallbackFetcher(primary, fallback).fetch(_URL) == "<p>fallback</p>"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_both_fail_propagates_brightdata_error() -> None:
    primary = StubFetcher(error=InsaneFetchError("primary down"))
    fallback = StubFetcher(error=BrightDataError("fallback down"))
    with pytest.raises(BrightDataError, match="fallback down"):
        FallbackFetcher(primary, fallback).fetch(_URL)
    assert fallback.calls == 1


def test_close_closes_both() -> None:
    primary = StubFetcher(html="x")
    fallback = StubFetcher(html="y")
    FallbackFetcher(primary, fallback).close()
    assert primary.closed is True
    assert fallback.closed is True


def test_context_manager_closes_both() -> None:
    primary = StubFetcher(html="x")
    fallback = StubFetcher(html="y")
    with FallbackFetcher(primary, fallback):
        pass
    assert primary.closed is True
    assert fallback.closed is True


def test_enter_returns_self() -> None:
    fetcher = FallbackFetcher(StubFetcher(html="x"), StubFetcher(html="y"))
    assert fetcher.__enter__() is fetcher


def test_fallback_does_not_record_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """폴백 발생 시 FallbackFetcher 는 record_usage 를 호출하지 않는다 (이중집계 차단)."""
    spy: dict[str, int] = {"n": 0}
    monkeypatch.setattr(usage_mod, "record_usage", lambda u: spy.__setitem__("n", spy["n"] + 1))
    primary = StubFetcher(error=InsaneFetchError("boom"))
    fallback = StubFetcher(html="<p>fallback</p>")
    FallbackFetcher(primary, fallback).fetch(_URL)
    assert spy["n"] == 0
