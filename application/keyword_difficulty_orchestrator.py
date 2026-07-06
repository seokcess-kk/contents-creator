"""키워드 난이도 분석 application 오케스트레이터.

domain/keyword_difficulty 는 격리 도메인이므로 SERP HTML fetch 를 직접 수행하지
않는다. 본 오케스트레이터가 SERP fetcher(`crawler_serp_fetcher` 토글 — 기본 insane
하이브리드 + Bright Data 폴백)를 인스턴스화해 주입한다.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from application.stage_runner import _build_serp_fetcher
from application.usage_tracker import save_usage_to_supabase
from config.settings import settings
from domain.common.usage import collect_usage, record_usage, reset_usage, run_in_isolated_usage_ctx
from domain.crawler.brightdata_client import BrightDataError
from domain.crawler.fetcher import HtmlFetcher
from domain.keyword_difficulty import storage
from domain.keyword_difficulty.cache import get_cached, put_cached
from domain.keyword_difficulty.model import KeywordDifficulty, SearchVolume, SerpFetchError
from domain.keyword_difficulty.naver_ad_client import get_search_volume
from domain.keyword_difficulty.parser import parse_serp
from domain.keyword_difficulty.scorer import score_difficulty

logger = logging.getLogger(__name__)

_SERP_URL = "https://search.naver.com/search.naver?query={query}"


def _batch_rate_limit_sec() -> float:
    """settings 로부터 동적 로딩. 운영 중 env 로 즉시 보정 가능."""
    return settings.keyword_difficulty_batch_rate_seconds


def _batch_default_parallel() -> int:
    """settings 로부터 동적 로딩. 운영 중 env 로 즉시 보정 가능."""
    return settings.keyword_difficulty_batch_parallel


def _build_client() -> HtmlFetcher:
    """난이도 SERP fetcher 를 생성한다. `crawler_serp_fetcher` 토글에 따라 insane
    하이브리드(desktop+`#main_pack` 우선 + Bright Data 폴백) 또는 Bright Data 단독.

    stage_runner._build_serp_fetcher 를 재사용해 selector/토글을 단일 출처로 유지한다
    (application↔application import — application/CLAUDE.md 상 허용).
    """
    return _build_serp_fetcher()


def _safe_get_volume(keyword: str) -> SearchVolume | None:
    """검색량 fetch 의 모든 예외를 None 으로 흡수 (분석 본 흐름 비차단)."""
    try:
        return get_search_volume(keyword)
    except Exception:
        logger.warning("keyword_difficulty.search_volume_failed keyword=%s", keyword, exc_info=True)
        return None


def analyze_keyword(
    keyword: str,
    *,
    client: HtmlFetcher | None = None,
    persist: bool = True,
) -> KeywordDifficulty:
    """단일 키워드 SERP fetch → 파싱 → 점수 → (옵션) Supabase 저장.

    Args:
        keyword: 검색 키워드.
        client: SERP fetcher (테스트 주입용). None 이면 `_build_client()`(토글 기반)로 생성.
        persist: True 면 결과를 keyword_difficulty_snapshots 에 insert.

    Returns: 분석 결과 KeywordDifficulty.

    Raises:
        SerpFetchError: SERP fetch 실패.
    """
    cli = client or _build_client()
    url = _SERP_URL.format(query=quote(keyword))

    # 2026-04-29 F3: SERP 캐시 hit 시 Bright Data 호출 우회. 검색량은 캐시 안 함
    # (검색량 API 자체가 빠르고 신선도 영향 작음).
    cached_html = get_cached(keyword)

    # 2026-04-29 F2: SERP fetch + 검색량 fetch 를 ThreadPool(2) 로 병렬.
    # 캐시 hit 시 SERP fetch 는 즉시 반환 → 검색량 fetch 만 실제 외부 호출.
    reset_usage()
    search_volume: SearchVolume | None = None
    try:
        if cached_html is not None:
            html = cached_html
            # 검색량만 호출 (격리 ctx 불필요 — 단일 호출)
            search_volume = _safe_get_volume(keyword)
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                html_future = executor.submit(run_in_isolated_usage_ctx, cli.fetch, url)
                vol_future = executor.submit(run_in_isolated_usage_ctx, _safe_get_volume, keyword)
                try:
                    html, html_usages = html_future.result()
                except BrightDataError as exc:
                    raise SerpFetchError(f"SERP fetch 실패: {keyword}") from exc
                search_volume, vol_usages = vol_future.result()

            # 부모 컨텍스트에 usage 머지
            for u in html_usages + vol_usages:
                record_usage(u)
            # 성공 시 캐시 put
            put_cached(keyword, html)
    finally:
        usages = collect_usage()
        if usages:
            save_usage_to_supabase(usages, keyword=keyword, stage="keyword_difficulty")

    composition = parse_serp(html)
    # search_volume 이 None 이어도 scorer 가 sov_grade=UNKNOWN 으로 채움
    diff = score_difficulty(keyword, composition, search_volume=search_volume)

    if persist:
        try:
            diff = storage.insert_snapshot(diff)
        except Exception:
            # 저장 실패가 분석 자체를 막지 않도록 warning 후 인-메모리 결과 반환
            logger.exception("keyword_difficulty.persist_failed keyword=%s", keyword)

    logger.info(
        "keyword_difficulty.analyzed keyword=%s grade=%s score=%s blog=%d spam=%d total=%d",
        keyword,
        diff.grade.value,
        diff.score,
        composition.blog_slots,
        composition.spam_cards,
        composition.total_cards,
    )
    return diff


def batch_analyze_keywords(
    keywords: list[str],
    *,
    parallel: int | None = None,
    persist: bool = True,
) -> list[KeywordDifficulty]:
    """다수 키워드를 병렬 분석. ThreadPoolExecutor + rate limit.

    Bright Data 호출 비용·rate 보호를 위해 동시 실행 수를 제한 (default settings).
    각 워커는 호출 후 settings.keyword_difficulty_batch_rate_seconds 만큼 sleep.
    parallel/rate 모두 settings 에서 읽어 운영 중 env 로 즉시 보정 가능
    (2026-05-04 Phase F 후속 — 4xx 발생 시 코드 수정 없이 하향).

    Returns: 입력 순서와 무관한 결과 리스트. 실패한 키워드는 결과에서 제외되며 logging.error.
    """
    if not keywords:
        return []

    cli = _build_client()
    results: list[KeywordDifficulty] = []
    rate_sec = _batch_rate_limit_sec()
    workers = parallel if parallel is not None else _batch_default_parallel()

    def _worker(kw: str) -> KeywordDifficulty | None:
        try:
            diff = analyze_keyword(kw, client=cli, persist=persist)
            time.sleep(rate_sec)
            return diff
        except Exception:
            logger.exception("keyword_difficulty.batch_worker_failed keyword=%s", kw)
            return None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(_worker, kw): kw for kw in keywords}
        for fut in as_completed(futures):
            res = fut.result()
            if res is not None:
                results.append(res)

    logger.info(
        "keyword_difficulty.batch_completed requested=%d succeeded=%d parallel=%d rate=%.2fs",
        len(keywords),
        len(results),
        workers,
        rate_sec,
    )
    return results
