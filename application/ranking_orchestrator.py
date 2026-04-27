"""순위 추적 use case. CLI / FastAPI / 스케줄러 공통 진입점.

도메인 격리: ranking 은 crawler 를 직접 import 하지 않으므로 본 파일이
crawler.serp_collector 와 ranking.tracker 를 합성해 호출한다.

SPEC-RANKING.md §3 참조.
"""

from __future__ import annotations

import calendar as _calendar
import logging
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup

from config.settings import require, settings
from domain.crawler.brightdata_client import BrightDataClient
from domain.crawler.serp_collector import (
    BLOG_POST_URL_RE,
    build_integrated_serp_url,
)
from domain.ranking import storage, tracker
from domain.ranking.model import (
    CalendarRow,
    Publication,
    RankingCalendar,
    RankingCheckSummary,
    RankingDuplicateUrlError,
    RankingMatchError,
    RankingSnapshot,
    RankingTimeline,
)
from domain.ranking.url_match import normalize_blog_url

KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


def register_publication(
    *,
    keyword: str,
    url: str,
    slug: str | None = None,
    job_id: str | None = None,
    published_at: datetime | None = None,
) -> Publication:
    """URL 등록. 동일 url 재호출은 기존 row 반환 (멱등).

    slug 가 None 이면 외부 URL 추적 (본 프로젝트로 발행하지 않은 글).
    같은 URL 이 본 프로젝트로 나중에 발행되면 slug 를 채워 다시 등록할 수 있다 —
    그 경우 멱등 분기에서 기존 row 가 반환되므로 별도 update API 가 필요하면
    추후 도입한다.

    Raises:
        ValueError: url 형식이 네이버 블로그 포스트가 아님.
    """
    normalized = normalize_blog_url(url)
    if normalized is None:
        raise ValueError(f"네이버 블로그 포스트 URL 형식이 아닙니다: {url!r}")

    publication = Publication(
        job_id=job_id,
        keyword=keyword,
        slug=slug,
        url=normalized,
        published_at=published_at,
    )
    try:
        return storage.insert_publication(publication)
    except RankingDuplicateUrlError:
        existing = storage.get_publication_by_url(normalized)
        if existing is None:
            # 매우 드문 경합 — duplicate 신호 후 select 0건. 명시적 에러.
            raise
        logger.info(
            "publication.duplicate keyword=%r url=%s — returning existing", keyword, normalized
        )
        return existing


def update_publication(
    publication_id: str,
    *,
    keyword: str | None = None,
    url: str | None = None,
    slug: str | None = None,
    published_at: datetime | None = None,
) -> Publication | None:
    """publication 부분 수정. 전달된 필드만 갱신.

    URL 이 제공되면 normalize 후 저장. 정규화 실패 시 ValueError.
    멱등 처리는 storage 레이어가 담당 (UNIQUE 충돌은 RankingDuplicateUrlError).
    """
    normalized_url: str | None = None
    if url is not None:
        normalized_url = normalize_blog_url(url)
        if normalized_url is None:
            raise ValueError(f"네이버 블로그 포스트 URL 형식이 아닙니다: {url!r}")

    return storage.update_publication(
        publication_id,
        keyword=keyword,
        url=normalized_url,
        slug=slug,
        published_at=published_at,
    )


def delete_publication(publication_id: str) -> bool:
    """publication 삭제. snapshots 은 cascade 로 같이 사라진다."""
    return storage.delete_publication(publication_id)


def check_rankings_for_publication(publication_id: str) -> RankingSnapshot:
    """단일 publication 의 현재 SERP 위치 측정 + snapshot 저장.

    Raises:
        ValueError: publication 미존재.
        RankingMatchError: SERP fetch/parse 실패.
    """
    publication = storage.get_publication(publication_id)
    if publication is None:
        raise ValueError(f"publication 미존재: {publication_id}")

    client = BrightDataClient(
        api_key=require("bright_data_api_key"),
        zone=require("bright_data_web_unlocker_zone"),
    )
    try:
        snapshot = tracker.find_position(
            keyword=publication.keyword,
            target_url=publication.url,
            publication_id=publication_id,
            serp_url_builder=build_integrated_serp_url,
            serp_fetcher=client.fetch,
            serp_parser=_parse_serp_for_ranking,
        )
    finally:
        client.close()
    return storage.insert_snapshot(snapshot)


def check_all_active_rankings() -> RankingCheckSummary:
    """등록된 모든 publication 의 SERP 위치 일괄 측정 (스케줄러·CLI 진입점).

    개별 publication 실패는 logging.warning 후 다음으로 (배치 전체 중단 X).
    Bright Data rate 보호 위해 publication 간 sleep.
    """
    started = time.monotonic()
    publications = storage.list_publications(limit=10_000)
    checked = 0
    found = 0
    errors = 0

    for pub in publications:
        if pub.id is None:
            continue
        try:
            snap = check_rankings_for_publication(pub.id)
            checked += 1
            if snap.position is not None:
                found += 1
        except (RankingMatchError, ValueError) as exc:
            errors += 1
            logger.warning(
                "ranking.check_failed publication_id=%s keyword=%r err=%s",
                pub.id,
                pub.keyword,
                exc,
            )
        time.sleep(settings.ranking_check_sleep_seconds)

    duration = time.monotonic() - started
    summary = RankingCheckSummary(
        checked_count=checked,
        found_count=found,
        errors_count=errors,
        duration_seconds=duration,
    )
    logger.info(
        "ranking.check_all_done checked=%d found=%d errors=%d duration=%.1fs",
        checked,
        found,
        errors,
        duration,
    )
    return summary


def get_monthly_calendar(year: int, month: int) -> RankingCalendar:
    """KST 기준 해당 월의 publication × 일자 캘린더 매트릭스.

    같은 KST 일에 여러 측정이 있으면 가장 늦은 captured_at 의 position 을 사용한다
    (일말 상태). 미측정 날짜는 키 미존재 (프론트가 "-" 로 표시).
    """
    if not 1 <= month <= 12:
        raise ValueError(f"월은 1~12 범위: {month}")

    start_utc, end_utc = _kst_month_bounds(year, month)
    snapshots = storage.list_snapshots_in_range(start_utc, end_utc)
    publications = storage.list_publications(limit=10_000)

    rows: list[CalendarRow] = []
    by_pub_day = _group_by_pub_day(snapshots)
    for pub in publications:
        if pub.id is None:
            continue
        days_for_pub = by_pub_day.get(pub.id, {})
        rows.append(CalendarRow(publication=pub, days=days_for_pub))

    return RankingCalendar(month=f"{year:04d}-{month:02d}", rows=rows)


def _kst_month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """KST 월 경계 [00:00, 다음달 00:00) 를 UTC datetime 으로 반환."""
    last_day = _calendar.monthrange(year, month)[1]
    start_kst = datetime(year, month, 1, tzinfo=KST)
    end_kst = datetime(year, month, last_day, tzinfo=KST) + timedelta(days=1)
    return start_kst.astimezone(UTC), end_kst.astimezone(UTC)


def _group_by_pub_day(snapshots: list[RankingSnapshot]) -> dict[str, dict[str, int | None]]:
    """snapshot 리스트 → {publication_id: {YYYY-MM-DD(KST): position}}.

    같은 일 다회 측정 시 마지막 captured_at 값을 사용 (storage 가 asc 로 반환).
    """
    out: dict[str, dict[str, int | None]] = {}
    for s in snapshots:
        if s.captured_at is None:
            continue
        day_key = s.captured_at.astimezone(KST).strftime("%Y-%m-%d")
        out.setdefault(s.publication_id, {})[day_key] = s.position
    return out


def get_publication_timeline(publication_id: str, limit: int = 90) -> RankingTimeline | None:
    """publication + 최근 snapshot 시계열. 미존재 시 None."""
    publication = storage.get_publication(publication_id)
    if publication is None:
        return None
    snapshots = storage.list_snapshots(publication_id, limit=limit)
    return RankingTimeline(publication=publication, snapshots=snapshots)


# ── 내부: SERP 파서 (ranking 전용 경량 버전) ──


class _SerpItem:
    """tracker.ParsedSerpItem Protocol 호환. crawler.SerpResult 를 직접 사용 안 함."""

    def __init__(self, rank: int, url: str, title: str = "") -> None:
        self.rank = rank
        self.url = url
        self.title = title


def _parse_serp_for_ranking(html: str) -> list[Any]:
    """SERP HTML → ranking 매칭용 항목 리스트.

    crawler.serp_collector 의 풀 파서 (스니펫 추출, 광고 필터 등) 가 필요하지
    않다. 매칭에 필요한 rank + url 만 추출. 통합검색 + 블로그 탭 모두 동일
    `BLOG_POST_URL_RE` 패턴으로 필터.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    items: list[Any] = []
    rank = 0

    candidates: list[str] = []
    for tag in soup.find_all(True):
        for attr in ("href", "data-url"):
            val = tag.get(attr)
            if isinstance(val, str):
                candidates.append(val)

    for url in candidates:
        if url in seen:
            continue
        if not BLOG_POST_URL_RE.match(url):
            continue
        seen.add(url)
        rank += 1
        items.append(_SerpItem(rank=rank, url=url))

    return items
