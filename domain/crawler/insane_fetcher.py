# insane(curl_cffi) 본문 fetch 어댑터 — HtmlFetcher 구현. 성공 판정 = FetchResult.ok.
"""InsaneFetcher — vendor insane-search(curl_cffi) 를 HtmlFetcher 계약으로 감싼 어댑터.

- 성공 판정 기본은 `FetchResult.ok` + content sanity(최소 길이 + 차단마커 부재) 2차 방어.
  두 가지 특례: (1) `verdict == "strong_ok"` — vendor Layer 5 가 우리 success_selector
  (예: `#main_pack`) 매칭을 확인한 강한 positive proof 이므로 content sanity 재검을
  스킵한다. 정상 네이버 SERP 가 captcha.nid.naver.com config 를 임베드해 bare "captcha"
  소프트마커에 걸리는 false positive(→ 불필요한 Bright Data 폴백)를 차단한다. (2)
  `verdict == "suspect_ok"`(부분성공) 는 ok=False 지만 content sanity 통과 시 채택한다.
- 그 외 모든 실패(challenge/blocked/rate_limited/auth_required/not_found, suspect_ok
  sanity 미달, ok=True 이나 content 비정상) 는 `InsaneFetchError` 로 raise 해 상위
  `FallbackFetcher` 가 Bright Data 로 폴백하도록 유도한다. not_found(404) 도 폴백한다
  (낭비 감수 — verdict 별 특례 분기로 단순성을 해치지 않는다).
- `InsaneFetchError` 는 `BrightDataTransientError` 하위라 HtmlFetcher 예외 계약
  (BrightDataError 계열) 을 만족한다. 성공 시에만 usage(provider="insane", cost=0) 기록.
- 어댑터 tenacity 재시도는 폴백이 존재하므로 1회로 최소화(총 2회 시도). 단일 IP insane
  타격·유료 폭증(RI-9) 억제. 동시성은 module-level BoundedSemaphore 로 강제.
"""

from __future__ import annotations

import logging
import threading

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from domain.common.usage import ApiUsage, record_usage
from domain.crawler.brightdata_client import BrightDataTransientError
from vendor.insane_search import FetchResult
from vendor.insane_search import fetch as vendor_fetch

logger = logging.getLogger(__name__)

# 어댑터 tenacity 재시도 = 총 2회(초기 1 + 재시도 1). 폴백(FallbackFetcher)이 존재하므로
# insane 자체 재시도를 최소화해 단일 IP 타격·유료 폭증(RI-9)을 억제한다.
MAX_ATTEMPTS = 2
RETRY_WAIT_MIN_SECONDS = 1
RETRY_WAIT_MAX_SECONDS = 3

# vendor grid 소진 상한 — insane 이 오래 TLS 프로파일을 소진하지 않도록 작게 고정.
_VENDOR_MAX_ATTEMPTS = 3

# content sanity 임계 — suspect_ok(부분성공) 및 ok=True 응답의 2차 방어(매직넘버 승격).
_MIN_CONTENT_LENGTH = 500
# strong_ok = success_selector positive proof(vendor Layer 5) → content sanity 재검 스킵.
_STRONG_OK_VERDICT = "strong_ok"
_SUSPECT_OK_VERDICT = "suspect_ok"
# 차단/챌린지 마커(소문자) — 존재 시 content 를 신뢰하지 않고 폴백 유도.
_BLOCK_MARKERS: tuple[str, ...] = (
    "captcha",
    "자동등록방지",
    "비정상적인 접근",
    "access denied",
    "정상적인 방법으로 접속",
)

# 전역 동시성 가드 — brightdata_client._concurrent_semaphore 패턴 미러. 모듈 레벨 싱글턴.
# settings.insane_concurrent_limit 을 실제 소비(no-op 아님). 단일 프로세스 안전망 —
# 배치 워커(BATCH_MAX_WORKERS)가 단일 IP insane 을 무제한 동시 타격하는 것을 막는다.
_concurrent_semaphore = threading.BoundedSemaphore(settings.insane_concurrent_limit)


class InsaneFetchError(BrightDataTransientError):
    """insane(curl_cffi) fetch 실패 — 폴백 유도용 전용 예외.

    `BrightDataTransientError` 하위이므로 (1) HtmlFetcher 예외 계약(BrightDataError
    계열), (2) 재시도/폴백 유도 계약(BrightDataTransientError) 을 동시에 만족한다.
    상위 FallbackFetcher 는 이 예외(또는 BrightDataError)를 포착해 폴백한다.
    """


class InsaneFetcher:
    """vendor insane-search(curl_cffi) 어댑터. HtmlFetcher 4종 구현.

    본문·SERP 공용. 생성자 파라미터(device_class/success_selectors/enable_phase0/
    max_attempts)로 트랙별 튜닝을 주입한다. default 는 본문 전용 하드코딩 값과 동일하므로
    `InsaneFetcher()` 호출은 기존 본문 동작을 그대로 유지한다.
    `enable_playwright`/`enable_learning` 은 파라미터화하지 않고 항상 False 로 고정한다
    (curl-only 격리 + Playwright 영구 금지 + 홈디렉터리 파일쓰기 차단).
    """

    def __init__(
        self,
        *,
        device_class: str = "mobile",
        success_selectors: list[str] | None = None,
        enable_phase0: bool = True,
        max_attempts: int = _VENDOR_MAX_ATTEMPTS,
    ) -> None:
        self._device_class = device_class
        self._success_selectors = success_selectors
        self._enable_phase0 = enable_phase0
        self._max_attempts = max_attempts

    def fetch(self, url: str) -> str:
        """url 을 insane 로 fetch 해 raw HTML 반환. 실패 시 InsaneFetchError raise."""
        return self._fetch_with_retry(url)

    @retry(
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN_SECONDS, max=RETRY_WAIT_MAX_SECONDS),
        retry=retry_if_exception_type(InsaneFetchError),
        reraise=True,
    )
    def _fetch_with_retry(self, url: str) -> str:
        with _concurrent_semaphore:
            result = self._call_vendor(url)
        return self._accept(result, url)

    def _call_vendor(self, url: str) -> FetchResult:
        """curl-only 규약으로 vendor fetch 호출. 내부 예외는 전이성 실패로 변환."""
        try:
            return vendor_fetch(
                url,
                device_class=self._device_class,
                success_selectors=self._success_selectors,
                enable_playwright=False,  # 하드코딩 유지 (curl-only, Playwright 영구 금지)
                enable_learning=False,  # 하드코딩 유지 (홈디렉터리 파일쓰기 차단)
                enable_phase0=self._enable_phase0,
                max_attempts=self._max_attempts,
                timeout=settings.insane_timeout_seconds,
            )
        except Exception as exc:  # vendor 내부 예외 방어 → 폴백 유도 (전이성)
            raise InsaneFetchError(f"insane vendor 예외: {url}") from exc

    def _accept(self, result: FetchResult, url: str) -> str:
        """strong_ok 은 selector positive proof 로 즉시 채택, 그 외는 content sanity 2차 방어."""
        # strong_ok = vendor Layer 5 가 우리 success_selector(#main_pack) 매칭을 확인한 강한
        # positive proof. 정상 SERP 의 captcha.nid.naver.com 임베드가 bare "captcha" 소프트
        # 마커에 걸리는 false positive 를 피하려 content sanity 재검을 스킵한다.
        if result.verdict == _STRONG_OK_VERDICT:
            record_usage(ApiUsage(provider="insane", model="curl_cffi"))
            return result.content
        # weak_ok/suspect_ok 는 selector 없는 휴리스틱 판정 → sanity 재검이 실제 차단 2차 방어.
        accepted = result.ok or result.verdict == _SUSPECT_OK_VERDICT
        if accepted and _content_is_sane(result.content):
            record_usage(ApiUsage(provider="insane", model="curl_cffi"))
            return result.content
        raise InsaneFetchError(f"insane 실패 verdict={result.verdict!r} ok={result.ok} url={url}")

    def close(self) -> None:
        """vendor curl_cffi 세션풀(process-wide transport.POOL) 해제 — 세션 close + 캐시 비움."""
        from vendor.insane_search.transport import POOL

        POOL.reset()

    def __enter__(self) -> InsaneFetcher:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _content_is_sane(content: str) -> bool:
    """최소 길이 + 차단마커 부재로 content 신뢰 여부 판정 (2차 방어)."""
    if len(content) < _MIN_CONTENT_LENGTH:
        return False
    lowered = content.lower()
    return not any(marker in lowered for marker in _BLOCK_MARKERS)
