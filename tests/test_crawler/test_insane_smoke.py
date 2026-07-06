"""실 vendor 1-URL 통합 스모크 — 네트워크 의존, 기본 skip (PR3 완료 게이트, step16).

mock 은 vendor fetch 시그니처 오타/실 반환구조 오류를 못 잡으므로, 실제
`vendor.insane_search.fetch` 를 InsaneFetcher 경유로 1회 호출해 HTML 수신을 실측한다.

실행 (opt-in):
    RUN_INSANE_SMOKE=1 .venv/Scripts/python.exe -m pytest \
        tests/test_crawler/test_insane_smoke.py --no-cov -s
"""

from __future__ import annotations

import os

import pytest

from domain.crawler.insane_fetcher import InsaneFetcher

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INSANE_SMOKE") != "1",
    reason="네트워크 의존 통합 스모크 — RUN_INSANE_SMOKE=1 로 opt-in",
)

# PoC 에서 insane 성공 확인된 실 URL.
_SMOKE_URL = "https://m.blog.naver.com/knowlog-/224279043573"


@pytest.mark.integration
def test_real_vendor_fetch_returns_html() -> None:
    with InsaneFetcher() as fetcher:
        html = fetcher.fetch(_SMOKE_URL)
    assert isinstance(html, str)
    assert len(html) >= 500
    assert "<" in html
