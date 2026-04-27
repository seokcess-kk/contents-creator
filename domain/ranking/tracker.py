"""SERP 매칭 로직 — 섹션 기반.

🔴 도메인 격리: 본 파일은 `domain.crawler` 를 import 하지 않는다.
SERP URL 생성과 fetch 는 application 레이어가 callable 로 주입한다.
파서는 domain.ranking.serp_parser 를 직접 사용 (같은 도메인 내 모듈).

SPEC-RANKING.md §3, domain/ranking/CLAUDE.md 참조.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from domain.ranking.model import RankingMatchError, RankingSnapshot
from domain.ranking.serp_parser import find_section_position, parse_integrated_serp

logger = logging.getLogger(__name__)

SerpFetcher = Callable[[str], str]
"""(serp_url) -> raw HTML"""

SerpUrlBuilder = Callable[[str], str]
"""(keyword) -> serp_url"""


def find_position(
    keyword: str,
    target_url: str,
    publication_id: str,
    serp_url_builder: SerpUrlBuilder,
    serp_fetcher: SerpFetcher,
) -> RankingSnapshot:
    """target_url 이 keyword 의 통합검색 SERP 에서 어느 섹션 몇 위인지 측정.

    Returns:
        RankingSnapshot: position=None & section=None 이면 미노출.
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
        result = parse_integrated_serp(html)
    except Exception as exc:
        raise RankingMatchError(f"SERP parse 실패: {exc}") from exc

    match = find_section_position(result, target_url)
    total = sum(len(s.urls) for s in result.sections)

    if match is None:
        logger.info(
            "ranking.not_found keyword=%r target=%s sections=%d total=%d",
            keyword,
            target_url,
            len(result.sections),
            total,
        )
        return RankingSnapshot(
            publication_id=publication_id,
            section=None,
            position=None,
            total_results=total,
        )

    logger.info(
        "ranking.matched keyword=%r target=%s section=%s position=%d total=%d",
        keyword,
        target_url,
        match.section,
        match.position,
        total,
    )
    return RankingSnapshot(
        publication_id=publication_id,
        section=match.section,
        position=match.position,
        total_results=total,
    )
