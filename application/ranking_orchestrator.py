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

from config.settings import require, settings
from domain.crawler.brightdata_client import BrightDataClient
from domain.crawler.serp_collector import build_main_search_url
from domain.ranking import storage, tracker
from domain.ranking.model import (
    CalendarCell,
    CalendarRow,
    Publication,
    RankingCalendar,
    RankingCheckSummary,
    RankingDuplicateUrlError,
    RankingMatchError,
    RankingSnapshot,
    RankingTimeline,
    Top10Snapshot,
)
from domain.ranking.serp_parser import (
    author_key,  # Top10 저장 시 blog_id 채움용
    parse_integrated_serp,
)
from domain.ranking.url_match import normalize_any_url, normalize_blog_url

KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


def register_publication(
    *,
    keyword: str,
    url: str | None = None,
    slug: str | None = None,
    job_id: str | None = None,
    published_at: datetime | None = None,
    parent_publication_id: str | None = None,
) -> Publication:
    """URL 등록. 동일 url 재호출은 기존 row 반환 (멱등).

    url=None: draft publication (재발행 임시 등). visibility=not_measured / workflow=draft.
    url=str: 정식 등록 — 네이버 블로그 URL 만 허용 (측정 매칭 정합성 보장).

    Raises:
        ValueError: url 이 네이버 블로그 포스트 URL 형식이 아님.
    """
    if url is None:
        publication = Publication(
            job_id=job_id,
            keyword=keyword,
            slug=slug,
            url=None,
            published_at=published_at,
            parent_publication_id=parent_publication_id,
            visibility_status="not_measured",
            workflow_status="draft",
        )
        return storage.insert_publication(publication)

    normalized = normalize_blog_url(url)
    if normalized is None:
        raise ValueError(f"네이버 블로그 포스트 URL 형식이 아닙니다: {url!r}")

    publication = Publication(
        job_id=job_id,
        keyword=keyword,
        slug=slug,
        url=normalized,
        published_at=published_at,
        parent_publication_id=parent_publication_id,
        visibility_status="not_measured",
        workflow_status="active",
    )
    try:
        return storage.insert_publication(publication)
    except RankingDuplicateUrlError:
        existing = storage.get_publication_by_url(normalized)
        if existing is None:
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
        normalized_url = normalize_any_url(url)  # 수정 시에만 외부 URL 허용 (운영 유연성)
        if normalized_url is None:
            raise ValueError(f"URL 형식이 유효하지 않습니다: {url!r}")

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
    """단일 publication 의 현재 SERP 위치 측정 + snapshot/Top10 저장 + 진단 자동 실행.

    측정 결과 저장 후 동일 SERP HTML 의 Top10 도 함께 보관해 카니발라이제이션·
    SOV 분석에 활용한다. Top10 저장과 진단은 best-effort — 실패해도 측정 자체는
    유지된다.

    Raises:
        ValueError: publication 미존재 또는 url=None (draft).
        RankingMatchError: SERP fetch/parse 실패.
    """
    publication = storage.get_publication(publication_id)
    if publication is None:
        raise ValueError(f"publication 미존재: {publication_id}")
    if publication.url is None:
        raise ValueError(f"publication.url 이 비어 있어 측정 불가 (draft 상태): {publication_id}")

    client = BrightDataClient(
        api_key=require("bright_data_api_key"),
        zone=require("bright_data_web_unlocker_zone"),
    )
    try:
        html = client.fetch(build_main_search_url(publication.keyword))
    finally:
        client.close()

    snapshot = _parse_and_match(html, publication, publication_id)
    saved = storage.insert_snapshot(snapshot)

    # 부가 작업: Top10 저장 + 진단 (실패해도 측정 결과는 유지)
    try:
        top10 = _build_top10_from_html(html, publication)
        if top10:
            storage.insert_top10_snapshots(top10)
    except Exception:
        logger.warning("top10.save_failed publication_id=%s", publication_id, exc_info=True)

    try:
        from application.diagnosis_orchestrator import diagnose_publication

        diagnose_publication(publication_id)
    except Exception:
        logger.warning("diagnosis.run_failed publication_id=%s", publication_id, exc_info=True)

    return saved


def _parse_and_match(html: str, publication: Publication, publication_id: str) -> RankingSnapshot:
    """SERP HTML 을 파싱해 publication.url 매칭 결과를 RankingSnapshot 으로."""
    return tracker.find_position(
        keyword=publication.keyword,
        target_url=publication.url,
        publication_id=publication_id,
        serp_url_builder=build_main_search_url,
        serp_fetcher=lambda _: html,
    )


def _build_top10_from_html(html: str, publication: Publication) -> list[Top10Snapshot]:
    """SERP HTML 을 파싱해 Top10Snapshot 리스트로 변환."""
    parsed = parse_integrated_serp(html)
    # url=None 인 draft 는 check_rankings 가 차단하므로 여기엔 도달 안 함, 방어적 처리
    target_norm = (publication.url or "").lower().rstrip("/")
    out: list[Top10Snapshot] = []
    for section in parsed.sections:
        for rank, url in enumerate(section.urls, start=1):
            out.append(
                Top10Snapshot(
                    keyword=publication.keyword,
                    rank=rank,
                    url=url,
                    section=section.name,
                    blog_id=author_key(url),
                    is_ours=(url.lower().rstrip("/") == target_norm),
                )
            )
    return out


def check_all_active_rankings() -> RankingCheckSummary:
    """등록된 모든 publication 의 SERP 위치 일괄 측정 (스케줄러·CLI 진입점).

    개별 publication 실패는 logging.warning 후 다음으로 (배치 전체 중단 X).
    Bright Data rate 보호 위해 publication 간 sleep.
    """
    started = time.monotonic()
    publications = storage.list_publications(limit=10_000)
    # 측정 대상 필터 — draft/held/republishing/dismissed 는 제외, URL 있는 active 계열만
    measurable = [
        p
        for p in publications
        if p.url is not None and p.workflow_status in ("active", "action_required")
    ]
    checked = 0
    found = 0
    errors = 0

    for pub in measurable:
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


def _group_by_pub_day(
    snapshots: list[RankingSnapshot],
) -> dict[str, dict[str, CalendarCell]]:
    """snapshot 리스트 → {publication_id: {YYYY-MM-DD(KST): CalendarCell}}.

    같은 일 다회 측정 시 마지막 captured_at 의 (section, position) 사용.
    """
    out: dict[str, dict[str, CalendarCell]] = {}
    for s in snapshots:
        if s.captured_at is None:
            continue
        day_key = s.captured_at.astimezone(KST).strftime("%Y-%m-%d")
        out.setdefault(s.publication_id, {})[day_key] = CalendarCell(
            section=s.section, position=s.position
        )
    return out


def get_publication_timeline(publication_id: str, limit: int = 90) -> RankingTimeline | None:
    """publication + 최근 snapshot 시계열. 미존재 시 None."""
    publication = storage.get_publication(publication_id)
    if publication is None:
        return None
    snapshots = storage.list_snapshots(publication_id, limit=limit)
    return RankingTimeline(publication=publication, snapshots=snapshots)


# SERP 파서는 domain.ranking.serp_parser 로 이전 (섹션 기반 매칭).
# 통합검색 메인 페이지의 블록 구조 파싱이 복잡해 별도 모듈로 분리.
