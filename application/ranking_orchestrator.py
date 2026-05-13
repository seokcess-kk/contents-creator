"""순위 추적 use case. CLI / FastAPI / 스케줄러 공통 진입점.

도메인 격리: ranking 은 crawler 를 직접 import 하지 않으므로 본 파일이
crawler.serp_collector 와 ranking.tracker 를 합성해 호출한다.

SPEC-RANKING.md §3 참조.
"""

from __future__ import annotations

import calendar as _calendar
import logging
import threading
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from application.usage_tracker import save_usage_to_supabase
from config.settings import require, settings
from domain.common.usage import collect_usage, reset_usage
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

# 2026-05-02 silent-failure 사고 후속 — check_all_active_rankings 사이클 동안의
# api_usage 저장 실패 건수를 thread-safe 로 누적해 summary 에 노출한다.
_check_all_counters_lock = threading.Lock()
_check_all_usage_save_failures = 0


def _reset_check_all_counters() -> None:
    """check_all_active_rankings 진입 시 호출 — 카운터 초기화."""
    global _check_all_usage_save_failures
    with _check_all_counters_lock:
        _check_all_usage_save_failures = 0


def _record_usage_save_failure() -> None:
    """save_usage_to_supabase 가 False 반환 시 호출 — 카운터 +1."""
    global _check_all_usage_save_failures
    with _check_all_counters_lock:
        _check_all_usage_save_failures += 1


def _read_usage_save_failures() -> int:
    with _check_all_counters_lock:
        return _check_all_usage_save_failures


def register_publication(
    *,
    keyword: str,
    url: str | None = None,
    slug: str | None = None,
    job_id: str | None = None,
    published_at: datetime | None = None,
    parent_publication_id: str | None = None,
    blog_channel_id: str | None = None,
) -> Publication:
    """URL 등록. 동일 url 재호출은 기존 row 반환 (멱등).

    url=None: draft publication (재발행 임시 등). visibility=not_measured / workflow=draft.
    url=str: 정식 등록 — 네이버 블로그 URL 만 허용 (측정 매칭 정합성 보장).
    blog_channel_id: 운영자가 어느 블로그 채널에서 발행했는지 (nullable FK).

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
            blog_channel_id=blog_channel_id,
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
        blog_channel_id=blog_channel_id,
    )
    try:
        inserted = storage.insert_publication(publication)
    except RankingDuplicateUrlError:
        existing = storage.get_publication_by_url(normalized)
        if existing is None:
            raise
        logger.info(
            "publication.duplicate keyword=%r url=%s — returning existing", keyword, normalized
        )
        _ensure_keyword_difficulty_attached(existing)
        _attach_generated_content(existing)
        return existing
    _ensure_keyword_difficulty_attached(inserted)
    _attach_generated_content(inserted)
    return inserted


def bulk_register_publications(
    items: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """대량 외부 URL 등록.

    각 item: {keyword, url, slug?, published_at?, job_id?}
    중복 URL 은 등록 전에 미리 조회해 skipped 로 명확히 분리한다.

    반환:
      {
        "created": [{"index", "publication_id", "keyword", "url"}, ...],
        "skipped": [{"index", "reason", "existing_publication_id", "url"}, ...],
        "failed":  [{"index", "reason", "input"}, ...],
      }
    """
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for idx, raw in enumerate(items):
        keyword = (raw.get("keyword") or "").strip()
        url = (raw.get("url") or "").strip() or None
        if not keyword:
            failed.append({"index": idx, "reason": "키워드 누락", "input": raw})
            continue

        # URL 이 있으면 정규화 → 사전 중복 체크 → skipped 분기
        normalized: str | None = None
        if url is not None:
            normalized = normalize_blog_url(url)
            if normalized is None:
                failed.append(
                    {
                        "index": idx,
                        "reason": "네이버 블로그 포스트 URL 형식이 아님",
                        "input": raw,
                    }
                )
                continue
            existing = storage.get_publication_by_url(normalized)
            if existing is not None:
                skipped.append(
                    {
                        "index": idx,
                        "reason": "이미 등록된 URL",
                        "existing_publication_id": existing.id,
                        "url": normalized,
                    }
                )
                continue

        try:
            pub = register_publication(
                keyword=keyword,
                url=url,
                slug=raw.get("slug"),
                job_id=raw.get("job_id"),
                published_at=_parse_iso(raw.get("published_at")),
                blog_channel_id=raw.get("blog_channel_id"),
            )
        except ValueError as exc:
            failed.append({"index": idx, "reason": str(exc), "input": raw})
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("bulk_register.unexpected idx=%d", idx, exc_info=True)
            failed.append({"index": idx, "reason": f"내부 오류: {exc}", "input": raw})
            continue

        created.append(
            {
                "index": idx,
                "publication_id": pub.id,
                "keyword": pub.keyword,
                "url": pub.url,
            }
        )

    logger.info(
        "bulk_register summary total=%d created=%d skipped=%d failed=%d",
        len(items),
        len(created),
        len(skipped),
        len(failed),
    )
    return {"created": created, "skipped": skipped, "failed": failed}


def _parse_iso(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def update_publication(
    publication_id: str,
    *,
    keyword: str | None = None,
    url: str | None = None,
    slug: str | None = None,
    published_at: datetime | None = None,
    blog_channel_id: str | None = None,
) -> Publication | None:
    """publication 부분 수정. 전달된 필드만 갱신.

    URL 이 제공되면 normalize 후 저장. 정규화 실패 시 ValueError.
    멱등 처리는 storage 레이어가 담당 (UNIQUE 충돌은 RankingDuplicateUrlError).

    draft → active 자동 전이: url 등록 시 현재 workflow_status="draft" 면
    `url_registered` 액션 기록 + workflow_status="active" 로 전이해 측정 대상화.
    재발행 자식 publication 이 URL 등록 후 측정에서 빠지지 않도록 하기 위함.

    blog_channel_id: 운영자가 어느 블로그 채널에서 발행했는지 갱신 (nullable FK).
    """
    normalized_url: str | None = None
    if url is not None:
        normalized_url = normalize_any_url(url)  # 수정 시에만 외부 URL 허용 (운영 유연성)
        if normalized_url is None:
            raise ValueError(f"URL 형식이 유효하지 않습니다: {url!r}")

    needs_activation = False
    if normalized_url is not None:
        current = storage.get_publication(publication_id)
        if current is not None and current.workflow_status == "draft":
            needs_activation = True

    updated = storage.update_publication(
        publication_id,
        keyword=keyword,
        url=normalized_url,
        slug=slug,
        published_at=published_at,
        blog_channel_id=blog_channel_id,
    )
    if updated is None:
        return None

    if needs_activation and normalized_url is not None:
        _activate_after_url_registration(publication_id, normalized_url)
        refreshed = storage.update_publication_workflow_state(
            publication_id, workflow_status="active"
        )
        if refreshed is not None:
            updated = refreshed
        _ensure_keyword_difficulty_attached(updated)
        _attach_generated_content(updated)
    elif updated.url is not None and (keyword is not None or normalized_url is not None):
        _ensure_keyword_difficulty_attached(updated, force=keyword is not None)
        _attach_generated_content(updated)
    return updated


def _ensure_keyword_difficulty_attached(publication: Publication, *, force: bool = False) -> None:
    """발행 publication에 발행 시점 키워드 난이도 스냅샷을 best-effort로 연결."""
    if publication.id is None or publication.url is None:
        return
    if publication.keyword_difficulty_snapshot_id and not force:
        return

    try:
        from application import keyword_difficulty_orchestrator

        diff = keyword_difficulty_orchestrator.analyze_keyword(publication.keyword, persist=True)
        if diff.id is None:
            logger.warning(
                "publication.keyword_difficulty_no_snapshot_id publication_id=%s keyword=%r",
                publication.id,
                publication.keyword,
            )
            return
        storage.update_publication_keyword_difficulty(publication.id, diff.id)
    except Exception:
        logger.warning(
            "publication.keyword_difficulty_attach_failed publication_id=%s keyword=%r",
            publication.id,
            publication.keyword,
            exc_info=True,
        )


def _attach_generated_content(publication: Publication) -> None:
    """Link generated content rows to the publication by job_id first, then slug.

    Phase B9 fix — publication 등록 시 generated_contents.publication_id 외에
    keyword_batch_items.publication_id 도 백필. batch item 이 후보 키워드부터
    발행 URL까지 종단 분석의 기준점이 되도록 함 (사용자 운영 철학 §4 데이터 누적).
    """
    if publication.id is None or publication.url is None:
        return
    if not publication.job_id and not publication.slug:
        return

    try:
        from config.supabase import get_client

        client = get_client()
        payload = {"publication_id": publication.id}
        if publication.job_id:
            client.table("generated_contents").update(payload).eq(
                "job_id", publication.job_id
            ).execute()
        elif publication.slug:
            client.table("generated_contents").update(payload).eq(
                "slug", publication.slug
            ).execute()
    except Exception:
        logger.warning(
            "publication.generated_content_attach_failed publication_id=%s slug=%r job_id=%r",
            publication.id,
            publication.slug,
            publication.job_id,
            exc_info=True,
        )

    _attach_batch_item(publication)


def _attach_batch_item(publication: Publication) -> None:
    """publication.publication_id 를 keyword_batch_items 에도 백필.

    Phase B9 fix — batch item 이 발행 URL 까지 추적되도록 generated_contents.id
    또는 (job_id, keyword) triple 로 매칭. graceful (실패해도 publication 등록은
    영향 없음).

    2026-05-11 fix — 동일 키워드를 서로 다른 URL 로 두 번 등록할 때 첫 등록의
    batch_item.publication_id 가 두 번째 등록에 의해 덮어씌워져 이전 publication
    이 orphan 으로 끊어지던 버그 차단. UPDATE 시 publication_id IS NULL 조건을
    부착해 비어있는 row 만 백필한다.
    """
    if publication.id is None:
        return
    try:
        from config.supabase import get_client

        client = get_client()
        payload = {"publication_id": publication.id}

        # 1차: generated_content_id 매칭 (가장 정확)
        if publication.job_id and publication.keyword:
            client.table("keyword_batch_items").update(payload).eq(
                "job_id", publication.job_id
            ).eq("keyword", publication.keyword).is_(
                "publication_id", "null"
            ).execute()
            return
        # 2차 fallback: keyword 만으로 (job_id 없는 publication 호환).
        # 덮어쓰기 방지를 위해 publication_id IS NULL row 만 갱신.
        if publication.keyword:
            client.table("keyword_batch_items").update(payload).eq(
                "keyword", publication.keyword
            ).is_("publication_id", "null").execute()
    except Exception:
        logger.warning(
            "publication.batch_item_attach_failed publication_id=%s job_id=%r keyword=%r",
            publication.id,
            publication.job_id,
            publication.keyword,
            exc_info=True,
        )


def _activate_after_url_registration(publication_id: str, url: str) -> None:
    """url_registered 액션 기록 — INSERT 실패 시 raise (status 전이 차단)."""
    from domain.ranking import publication_actions as actions_storage
    from domain.ranking.publication_actions import PublicationAction

    actions_storage.insert_action(
        PublicationAction(
            publication_id=publication_id,
            action="url_registered",
            note="URL 등록 (draft → active)",
            metadata={"url": url},
        )
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
    # SERP fetch usage 를 격리 컨텍스트에서 수확 → Supabase api_usage 저장.
    # ThreadPool/스케줄러 호출에서도 부모 컨텍스트와 누적기 분리.
    reset_usage()
    try:
        html = client.fetch(build_main_search_url(publication.keyword))
    finally:
        client.close()
        usages = collect_usage()
        if usages:
            ok = save_usage_to_supabase(usages, keyword=publication.keyword, stage="ranking_check")
            if not ok:
                _record_usage_save_failure()
                logger.warning(
                    "ranking.usage_save_failed publication_id=%s keyword=%r — "
                    "측정은 정상이지만 api_usage INSERT 실패. summary 에 누적.",
                    publication_id,
                    publication.keyword,
                )

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

    # P1-#3: 측정 결과로 visibility_status 재산출 + 변경 시 update.
    # state_calculator 의 순수 함수가 dead code 였던 사전 상태 해소.
    try:
        from application.ranking_state import recalculate_visibility_after_measurement

        recalculate_visibility_after_measurement(publication_id)
    except Exception:
        logger.warning(
            "state.visibility_recalc_failed publication_id=%s",
            publication_id,
            exc_info=True,
        )

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
    _reset_check_all_counters()
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
        except Exception as exc:  # noqa: BLE001
            # 개별 publication 실패 격리. BrightDataError / Supabase RuntimeError /
            # 기타 네트워크 예외까지 모두 catch 해 배치 전체 중단을 차단한다.
            errors += 1
            logger.warning(
                "ranking.check_failed publication_id=%s keyword=%r err=%s",
                pub.id,
                pub.keyword,
                exc,
                exc_info=True,
            )
        time.sleep(settings.ranking_check_sleep_seconds)

    # P1-#3: 측정 사이클 종료 후 workflow 자동 전이 일괄 처리.
    # held_until 만료 + republishing 타임아웃 4종을 state_calculator 에 위임.
    try:
        from application.ranking_state import sweep_workflow_transitions

        sweep_workflow_transitions()
    except Exception:
        logger.warning("state.sweep_workflow_failed", exc_info=True)

    duration = time.monotonic() - started
    usage_save_failures = _read_usage_save_failures()
    summary = RankingCheckSummary(
        checked_count=checked,
        found_count=found,
        errors_count=errors,
        usage_save_failed_count=usage_save_failures,
        duration_seconds=duration,
    )
    log_method = logger.warning if usage_save_failures > 0 else logger.info
    log_method(
        "ranking.check_all_done checked=%d found=%d errors=%d usage_save_failed=%d duration=%.1fs",
        checked,
        found,
        errors,
        usage_save_failures,
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
