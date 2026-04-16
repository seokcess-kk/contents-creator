"""BrightDataClient 단위 테스트. 네트워크 호출은 모두 monkeypatch."""

from __future__ import annotations

from typing import Any

import pytest
import requests

from domain.crawler import brightdata_client as bd
from domain.crawler.brightdata_client import (
    BrightDataClient,
    BrightDataClientError,
    BrightDataError,
)


class FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.post_calls: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}
        self.closed = False

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> FakeResponse:
        self.post_calls.append({"url": url, "json": json, "timeout": timeout})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, FakeResponse)
        return item

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """retry wait 를 0 으로 단축해 테스트 속도 확보."""
    from tenacity import wait_none

    original_fetch = BrightDataClient._fetch_with_retry
    retry_obj = getattr(original_fetch, "retry", None)
    if retry_obj is not None:
        monkeypatch.setattr(retry_obj, "wait", wait_none())


def _make_client(session: FakeSession) -> BrightDataClient:
    client = BrightDataClient(api_key="test-key", zone="test-zone")
    client._session = session  # type: ignore[assignment]
    return client


def test_init_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        BrightDataClient(api_key="", zone="z")


def test_init_rejects_empty_zone() -> None:
    with pytest.raises(ValueError, match="zone"):
        BrightDataClient(api_key="k", zone="")


def test_fetch_success_first_try() -> None:
    session = FakeSession([FakeResponse(200, "<html>ok</html>")])
    client = _make_client(session)

    result = client.fetch("https://example.com")

    assert result == "<html>ok</html>"
    assert len(session.post_calls) == 1
    call = session.post_calls[0]
    assert call["url"] == bd.BRIGHTDATA_ENDPOINT
    assert call["json"] == {
        "zone": "test-zone",
        "url": "https://example.com",
        "format": "raw",
    }
    assert call["timeout"] == bd.REQUEST_TIMEOUT_SECONDS


def test_fetch_retries_on_5xx_then_succeeds() -> None:
    session = FakeSession(
        [
            FakeResponse(503, "svc unavailable"),
            FakeResponse(200, "<html>ok</html>"),
        ]
    )
    client = _make_client(session)

    result = client.fetch("https://example.com")

    assert result == "<html>ok</html>"
    assert len(session.post_calls) == 2


def test_fetch_retries_on_timeout_then_succeeds() -> None:
    session = FakeSession(
        [
            requests.Timeout("boom"),
            FakeResponse(200, "<html>ok</html>"),
        ]
    )
    client = _make_client(session)

    result = client.fetch("https://example.com")

    assert result == "<html>ok</html>"
    assert len(session.post_calls) == 2


def test_fetch_exhausts_retries_on_persistent_5xx() -> None:
    session = FakeSession(
        [
            FakeResponse(500, "err"),
            FakeResponse(500, "err"),
            FakeResponse(500, "err"),
        ]
    )
    client = _make_client(session)

    with pytest.raises(BrightDataError):
        client.fetch("https://example.com")

    assert len(session.post_calls) == bd.MAX_ATTEMPTS


def test_fetch_does_not_retry_on_4xx() -> None:
    session = FakeSession([FakeResponse(403, "forbidden")])
    client = _make_client(session)

    with pytest.raises(BrightDataClientError):
        client.fetch("https://example.com")

    # 4xx 는 즉시 실패, 재시도 없음
    assert len(session.post_calls) == 1


def test_context_manager_closes_session() -> None:
    session = FakeSession([FakeResponse(200, "ok")])
    with BrightDataClient(api_key="k", zone="z") as client:
        client._session = session  # type: ignore[assignment]
        client.fetch("https://example.com")
    assert session.closed is True
