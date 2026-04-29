"""키워드 난이도 분석 application 오케스트레이터.

domain/keyword_difficulty 는 격리 도메인이므로 SERP HTML fetch 를 직접 수행하지
않는다. 본 오케스트레이터가 BrightDataClient 를 인스턴스화해 주입.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from config.settings import settings
from domain.crawler.brightdata_client import BrightDataClient, BrightDataError
from domain.keyword_difficulty import storage
from domain.keyword_difficulty.model import KeywordDifficulty, SerpFetchError
from domain.keyword_difficulty.parser import parse_serp
from domain.keyword_difficulty.scorer import score_difficulty

logger = logging.getLogger(__name__)

_SERP_URL = "https://search.naver.com/search.naver?query={query}"
_BATCH_RATE_LIMIT_SEC = 1.0  # Bright Data rate 보호: 키워드당 최소 간격
_BATCH_DEFAULT_PARALLEL = 3


def _build_client() -> BrightDataClient:
    return BrightDataClient(
        api_key=settings.bright_data_api_key,
        zone=settings.bright_data_web_unlocker_zone,
    )


def analyze_keyword(
    keyword: str,
    *,
    client: BrightDataClient | None = None,
    persist: bool = True,
) -> KeywordDifficulty:
    """단일 키워드 SERP fetch → 파싱 → 점수 → (옵션) Supabase 저장.

    Args:
        keyword: 검색 키워드.
        client: Bright Data 클라이언트 (테스트 주입용). None 이면 settings 에서 생성.
        persist: True 면 결과를 keyword_difficulty_snapshots 에 insert.

    Returns: 분석 결과 KeywordDifficulty.

    Raises:
        SerpFetchError: SERP fetch 실패.
    """
    cli = client or _build_client()
    url = _SERP_URL.format(query=quote(keyword))
    try:
        html = cli.fetch(url)
    except BrightDataError as exc:
        raise SerpFetchError(f"SERP fetch 실패: {keyword}") from exc

    composition = parse_serp(html)
    diff = score_difficulty(keyword, composition)

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
    parallel: int = _BATCH_DEFAULT_PARALLEL,
    persist: bool = True,
) -> list[KeywordDifficulty]:
    """다수 키워드를 병렬 분석. ThreadPoolExecutor + rate limit.

    Bright Data 호출 비용·rate 보호를 위해 동시 실행 수를 제한 (기본 3).
    각 워커는 호출 후 _BATCH_RATE_LIMIT_SEC 만큼 sleep.

    Returns: 입력 순서와 무관한 결과 리스트. 실패한 키워드는 결과에서 제외되며 logging.error.
    """
    if not keywords:
        return []

    cli = _build_client()
    results: list[KeywordDifficulty] = []

    def _worker(kw: str) -> KeywordDifficulty | None:
        try:
            diff = analyze_keyword(kw, client=cli, persist=persist)
            time.sleep(_BATCH_RATE_LIMIT_SEC)
            return diff
        except Exception:
            logger.exception("keyword_difficulty.batch_worker_failed keyword=%s", kw)
            return None

    with ThreadPoolExecutor(max_workers=max(1, parallel)) as executor:
        futures = {executor.submit(_worker, kw): kw for kw in keywords}
        for fut in as_completed(futures):
            res = fut.result()
            if res is not None:
                results.append(res)

    logger.info(
        "keyword_difficulty.batch_completed requested=%d succeeded=%d",
        len(keywords),
        len(results),
    )
    return results
