"""InsaneFetcher 단위 테스트. vendor fetch 는 monkeypatch (실 네트워크 없음)."""

from __future__ import annotations

from typing import Any

import pytest

from domain.common import usage as usage_mod
from domain.crawler import insane_fetcher as insf
from domain.crawler.brightdata_client import BrightDataTransientError
from domain.crawler.insane_fetcher import InsaneFetcher, InsaneFetchError
from vendor.insane_search import FetchResult

_URL = "https://m.blog.naver.com/knowlog-/224279043573"
# 500자 초과 정상 본문 (content sanity 통과용)
_LONG = "<html><body>" + "본문 내용 텍스트 " * 100 + "</body></html>"


class _SemaphoreSpy:
    """with 진입/종료를 카운트하는 세마포어 대체 스파이."""

    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0

    def __enter__(self) -> _SemaphoreSpy:
        self.acquired += 1
        return self

    def __exit__(self, *exc: object) -> None:
        self.released += 1


def _result(*, ok: bool, verdict: str, content: str) -> FetchResult:
    return FetchResult(ok=ok, content=content, verdict=verdict)


def _install(monkeypatch: pytest.MonkeyPatch, result_or_exc: Any) -> dict[str, Any]:
    """vendor_fetch 를 고정 반환/예외로 교체하고 호출 카운트+kwargs 를 캡처."""
    calls: dict[str, Any] = {"n": 0, "kwargs": None}

    def fake(url: str, **kwargs: Any) -> FetchResult:
        calls["n"] += 1
        calls["kwargs"] = kwargs
        if isinstance(result_or_exc, Exception):
            raise result_or_exc
        return result_or_exc

    monkeypatch.setattr(insf, "vendor_fetch", fake)
    return calls


@pytest.fixture(autouse=True)
def _reset_usage() -> None:
    usage_mod.reset_usage()


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """retry wait 를 0 으로 단축해 테스트 속도 확보."""
    from tenacity import wait_none

    retry_obj = getattr(InsaneFetcher._fetch_with_retry, "retry", None)
    if retry_obj is not None:
        monkeypatch.setattr(retry_obj, "wait", wait_none())


def test_ok_true_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    assert InsaneFetcher().fetch(_URL) == _LONG
    assert any(u.provider == "insane" for u in usage_mod.collect_usage())


def test_ok_true_passes_curl_only_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    InsaneFetcher().fetch(_URL)
    kwargs = calls["kwargs"]
    assert kwargs["device_class"] == "mobile"
    assert kwargs["enable_playwright"] is False
    assert kwargs["enable_learning"] is False


def test_default_ctor_passes_body_hardcoded_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """default InsaneFetcher() = 본문 하드코딩(mobile + selector None + phase0 + max=3) 무변경."""
    calls = _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    InsaneFetcher().fetch(_URL)
    kwargs = calls["kwargs"]
    assert kwargs["device_class"] == "mobile"
    assert kwargs["success_selectors"] is None
    assert kwargs["enable_phase0"] is True
    assert kwargs["max_attempts"] == insf._VENDOR_MAX_ATTEMPTS


def test_serp_ctor_passes_desktop_and_success_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """SERP 튜닝 인스턴스가 desktop + success_selectors 를 vendor_fetch 로 전파."""
    calls = _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    InsaneFetcher(device_class="desktop", success_selectors=["#main_pack"]).fetch(_URL)
    kwargs = calls["kwargs"]
    assert kwargs["device_class"] == "desktop"
    assert kwargs["success_selectors"] == ["#main_pack"]
    # curl-only 격리는 파라미터화 무관하게 항상 고정
    assert kwargs["enable_playwright"] is False
    assert kwargs["enable_learning"] is False


def test_custom_phase0_and_max_attempts_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """enable_phase0/max_attempts 커스텀 값이 vendor_fetch 로 전파."""
    calls = _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    InsaneFetcher(enable_phase0=False, max_attempts=5).fetch(_URL)
    kwargs = calls["kwargs"]
    assert kwargs["enable_phase0"] is False
    assert kwargs["max_attempts"] == 5


@pytest.mark.parametrize(
    "verdict",
    ["challenge", "blocked", "not_found", "auth_required", "rate_limited"],
)
def test_failure_verdicts_raise_and_no_usage(monkeypatch: pytest.MonkeyPatch, verdict: str) -> None:
    _install(monkeypatch, _result(ok=False, verdict=verdict, content=""))
    with pytest.raises(BrightDataTransientError):
        InsaneFetcher().fetch(_URL)
    assert usage_mod.collect_usage() == []  # 실패 시 usage 미기록


def test_suspect_ok_with_sane_content_accepts(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=False, verdict="suspect_ok", content=_LONG))
    assert InsaneFetcher().fetch(_URL) == _LONG
    assert any(u.provider == "insane" for u in usage_mod.collect_usage())


def test_suspect_ok_with_short_content_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=False, verdict="suspect_ok", content="<p>tiny</p>"))
    with pytest.raises(BrightDataTransientError):
        InsaneFetcher().fetch(_URL)


def test_strong_ok_with_block_marker_skips_sanity(monkeypatch: pytest.MonkeyPatch) -> None:
    """strong_ok = success_selector positive proof → bare 'captcha' 소프트마커 재검 스킵.

    정상 네이버 SERP 는 captcha.nid.naver.com config 를 임베드해 'captcha' 문자열이 항상
    존재한다. strong_ok(selector 매칭 확인) 이면 폴백하지 않고 content 를 반환해야 한다.
    """
    serp_like = (
        "<html><body id='main_pack'>" + "본문 " * 200 + " captcha.nid.naver.com</body></html>"
    )
    _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=serp_like))
    assert (
        InsaneFetcher(device_class="desktop", success_selectors=["#main_pack"]).fetch(_URL)
        == serp_like
    )
    assert any(u.provider == "insane" for u in usage_mod.collect_usage())


def test_weak_ok_with_block_marker_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """weak_ok(휴리스틱, selector 없음) 은 기존대로 content sanity 2차 방어 → 차단마커 reject."""
    tainted = "<html>" + "x" * 600 + " CAPTCHA required</html>"
    _install(monkeypatch, _result(ok=True, verdict="weak_ok", content=tainted))
    with pytest.raises(BrightDataTransientError):
        InsaneFetcher().fetch(_URL)
    assert usage_mod.collect_usage() == []  # 폴백 유도, usage 미기록


def test_ok_true_with_short_content_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=True, verdict="weak_ok", content="<p>too short</p>"))
    with pytest.raises(BrightDataTransientError):
        InsaneFetcher().fetch(_URL)


def test_vendor_exception_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(monkeypatch, RuntimeError("network boom"))
    with pytest.raises(BrightDataTransientError):
        InsaneFetcher().fetch(_URL)
    assert calls["n"] == insf.MAX_ATTEMPTS  # 초기 1 + 재시도 1 = 2


def test_raised_type_is_insane_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=False, verdict="challenge", content=""))
    with pytest.raises(InsaneFetchError):
        InsaneFetcher().fetch(_URL)


def test_fetch_acquires_semaphore(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    spy = _SemaphoreSpy()
    monkeypatch.setattr(insf, "_concurrent_semaphore", spy)
    InsaneFetcher().fetch(_URL)
    assert spy.acquired == 1
    assert spy.released == 1


def test_close_resets_vendor_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    from vendor.insane_search import transport

    called: dict[str, int] = {"reset": 0}
    monkeypatch.setattr(
        transport.POOL, "reset", lambda: called.__setitem__("reset", called["reset"] + 1)
    )
    InsaneFetcher().close()
    assert called["reset"] == 1


def test_context_manager_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    from vendor.insane_search import transport

    _install(monkeypatch, _result(ok=True, verdict="strong_ok", content=_LONG))
    called: dict[str, int] = {"reset": 0}
    monkeypatch.setattr(
        transport.POOL, "reset", lambda: called.__setitem__("reset", called["reset"] + 1)
    )
    with InsaneFetcher() as fetcher:
        assert fetcher.fetch(_URL) == _LONG
    assert called["reset"] == 1
