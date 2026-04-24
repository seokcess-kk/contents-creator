"""SERP 매칭 로직 — 의존성 주입 패턴.

🔴 도메인 격리: 본 파일은 `domain.crawler` 를 import 하지 않는다.
SERP fetch/parse 는 application 레이어에서 합성해 callable 로 주입한다.
SPEC-RANKING.md §3, domain/ranking/CLAUDE.md 참조.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from domain.ranking.model import RankingMatchError, RankingSnapshot
from domain.ranking.url_match import urls_match

logger = logging.getLogger(__name__)


class ParsedSerpItem(Protocol):
    """application 이 주입하는 SERP 결과 1건의 최소 인터페이스.

    crawler.SerpResult 와 호환되지만 직접 import 하지 않기 위해 Protocol 로 둔다.
    """

    rank: int
    url: object  # HttpUrl 또는 str — str() 변환으로 사용
    title: str


SerpFetcher = Callable[[str], str]
"""(serp_url) -> raw HTML"""

SerpParser = Callable[[str], list[ParsedSerpItem]]
"""(raw HTML) -> [ParsedSerpItem, ...]"""

SerpUrlBuilder = Callable[[str], str]
"""(keyword) -> serp_url"""


def find_position(
    keyword: str,
    target_url: str,
    publication_id: str,
    serp_url_builder: SerpUrlBuilder,
    serp_fetcher: SerpFetcher,
    serp_parser: SerpParser,
) -> RankingSnapshot:
    """target_url 이 keyword 의 SERP 에서 몇 위인지 측정.

    Returns:
        RankingSnapshot: position=None 이면 100위 밖 (미발견).
                         id, captured_at 은 storage 레이어에서 채움.

    Raises:
        RankingMatchError: SERP fetch/parse 실패. publication 단위 격리는
                           orchestrator 가 책임.
    """
    serp_url = serp_url_builder(keyword)
    try:
        html = serp_fetcher(serp_url)
    except Exception as exc:
        raise RankingMatchError(f"SERP fetch 실패: {exc}") from exc

    try:
        items = serp_parser(html)
    except Exception as exc:
        raise RankingMatchError(f"SERP parse 실패: {exc}") from exc

    position: int | None = None
    for item in items:
        if urls_match(target_url, str(item.url)):
            position = item.rank
            break

    logger.info(
        "ranking.checked keyword=%r target=%s position=%s items=%d",
        keyword,
        target_url,
        position,
        len(items),
    )
    return RankingSnapshot(
        publication_id=publication_id,
        position=position,
        total_results=len(items),
    )
