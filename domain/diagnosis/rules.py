"""미노출 사유 진단 룰 — evidence 기반.

5개 룰을 우선순위 순으로 적용한다. 결정적 진단(no_publication, no_measurement)
은 발견 즉시 단일 반환, 그 외에는 후보 모두를 confidence 순으로 반환한다.

신뢰도 산출은 결정적 함수로 명시 — LLM 환각 회피.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from domain.diagnosis.model import Diagnosis
from domain.ranking.model import Publication, RankingSnapshot, Top10Snapshot

# 한 번도 미노출(never_indexed) 진단 시작 기준 — 발행 후 충분한 색인 시간
_NEVER_INDEXED_MIN_DAYS = 3
_NEVER_INDEXED_MAX_CONFIDENCE = 0.85
# 노출 후 이탈(lost_visibility) 진단 — 최근 N회 연속 null 이면 강한 신호
_LOST_VISIBILITY_NULL_STREAK = 3
# 카니발라이제이션 — Top10 안에 같은 author 의 다른 URL 1개 이상이면 신호 강함
_CANNIBALIZATION_BASE_CONFIDENCE = 0.9


def diagnose(
    publication: Publication,
    snapshots: list[RankingSnapshot],
    top10_recent: list[Top10Snapshot],
    *,
    now: datetime | None = None,
) -> list[Diagnosis]:
    """모든 룰을 적용해 발견된 진단을 confidence desc 로 반환.

    snapshots 는 captured_at desc, top10_recent 는 가장 최근 측정의 Top10 만 (rank asc).
    now 는 테스트 주입용 (기본 UTC 현재).
    """
    now = now or datetime.now(tz=UTC)
    if publication.id is None:
        return []

    pub_id = publication.id

    # Rule 1·2 결정적: 발행/측정 누락 — 발견 즉시 단독 반환
    no_pub = _rule_no_publication(publication, pub_id)
    if no_pub:
        return [no_pub]
    no_meas = _rule_no_measurement(snapshots, pub_id)
    if no_meas:
        return [no_meas]

    # Rule 3·4·5 정황 — 모두 평가해 후보 누적
    candidates: list[Diagnosis] = []
    for rule in (
        _rule_lost_visibility,
        _rule_never_indexed,
        _rule_cannibalization,
    ):
        diag = rule(publication, snapshots, top10_recent, pub_id, now)
        if diag is not None:
            candidates.append(diag)

    candidates.sort(key=lambda d: d.confidence, reverse=True)
    return candidates


def _rule_no_publication(publication: Publication, pub_id: str) -> Diagnosis | None:
    """publications.url 비어 있으면 결정적 진단 (현재 모델에선 url 필수라 거의 발생 X)."""
    if not publication.url:
        return Diagnosis(
            publication_id=pub_id,
            reason="no_publication",
            confidence=1.0,
            evidence=["publications.url 미등록"],
            metrics={},
            recommended_action="발행 URL 을 등록해 주세요.",
        )
    return None


def _rule_no_measurement(snapshots: list[RankingSnapshot], pub_id: str) -> Diagnosis | None:
    """ranking_snapshots 가 0건이면 측정 안 됐다는 결정적 신호."""
    if not snapshots:
        return Diagnosis(
            publication_id=pub_id,
            reason="no_measurement",
            confidence=1.0,
            evidence=["순위 측정 이력 0건"],
            metrics={"snapshot_count": 0},
            recommended_action="지금 측정 버튼으로 즉시 SERP 측정을 실행해 주세요.",
        )
    return None


def _rule_lost_visibility(
    publication: Publication,
    snapshots: list[RankingSnapshot],
    top10_recent: list[Top10Snapshot],
    pub_id: str,
    now: datetime,
) -> Diagnosis | None:
    """과거 노출 이력 있고 최근 N회 연속 미노출이면 이탈 진단."""
    _ = (publication, top10_recent, now)
    if len(snapshots) < _LOST_VISIBILITY_NULL_STREAK:
        return None

    historical = [s for s in snapshots if s.position is not None]
    if not historical:
        return None  # 한 번도 노출 안 된 케이스는 never_indexed 가 처리

    recent = snapshots[:_LOST_VISIBILITY_NULL_STREAK]
    if any(s.position is not None for s in recent):
        return None  # 최근에도 잡혀 있음

    # 신뢰도: 연속 null streak 길이에 비례
    streak = _count_leading_nulls(snapshots)
    confidence = min(0.6 + 0.05 * (streak - _LOST_VISIBILITY_NULL_STREAK), 0.9)

    best = min(historical, key=lambda s: s.position or 999)
    last_seen = historical[0]
    return Diagnosis(
        publication_id=pub_id,
        reason="lost_visibility",
        confidence=round(confidence, 2),
        evidence=[
            f"{streak}일 연속 미노출",
            f"최근 노출: {last_seen.captured_at.date() if last_seen.captured_at else '?'} "
            f"{last_seen.section or '?'} {last_seen.position}위",
            f"최고 순위: {best.section or '?'} {best.position}위",
        ],
        metrics={
            "null_streak": streak,
            "best_position": best.position,
            "best_section": best.section,
            "last_seen_at": last_seen.captured_at.isoformat() if last_seen.captured_at else None,
            "historical_count": len(historical),
        },
        recommended_action="SERP 재분석 후 리라이트 또는 재발행 후보. 상위글 변화도 함께 점검하세요.",
    )


def _rule_never_indexed(
    publication: Publication,
    snapshots: list[RankingSnapshot],
    top10_recent: list[Top10Snapshot],
    pub_id: str,
    now: datetime,
) -> Diagnosis | None:
    """발행 D+N 이상 + 모든 측정에서 미노출 + 한 번도 노출 이력 없음."""
    _ = top10_recent
    if not snapshots:
        return None
    if any(s.position is not None for s in snapshots):
        return None  # 한 번이라도 잡혔으면 lost_visibility 영역

    base = publication.published_at or publication.created_at
    if base is None:
        return None
    days_since = (now - base).days
    if days_since < _NEVER_INDEXED_MIN_DAYS:
        return None  # 색인 지연 가능성, 보류

    confidence = min(
        0.5 + 0.05 * (days_since - _NEVER_INDEXED_MIN_DAYS), _NEVER_INDEXED_MAX_CONFIDENCE
    )
    return Diagnosis(
        publication_id=pub_id,
        reason="never_indexed",
        confidence=round(confidence, 2),
        evidence=[
            f"발행 후 {days_since}일 경과",
            f"측정 {len(snapshots)}회 중 노출 0회",
            "한 번도 SERP 에서 발견되지 않음",
        ],
        metrics={
            "days_since_publish": days_since,
            "measurement_count": len(snapshots),
        },
        recommended_action=(
            "제목·도입부에 타겟 키워드 의도가 약한지 점검. 콘텐츠 갭 분석 후 재발행 권장."
        ),
    )


def _rule_cannibalization(
    publication: Publication,
    snapshots: list[RankingSnapshot],
    top10_recent: list[Top10Snapshot],
    pub_id: str,
    now: datetime,
) -> Diagnosis | None:
    """우리 URL 미노출 + Top10 안에 같은 작성자의 다른 URL 노출 시."""
    _ = now
    if not snapshots:
        return None
    if not top10_recent:
        return None
    # 최근 측정에서 우리 URL 이 노출된 상태면 카니발라이제이션 진단 부적절
    if snapshots[0].position is not None:
        return None

    target_blog = _author_id(publication.url)
    if target_blog is None:
        return None

    same_author_others = [
        t
        for t in top10_recent
        if t.blog_id == target_blog and _normalize(t.url) != _normalize(publication.url)
    ]
    if not same_author_others:
        return None

    primary = min(same_author_others, key=lambda t: t.rank)
    return Diagnosis(
        publication_id=pub_id,
        reason="cannibalization",
        confidence=_CANNIBALIZATION_BASE_CONFIDENCE,
        evidence=[
            f"Top10 안에 동일 블로거의 다른 글이 {primary.section or '?'} {primary.rank}위로 노출 중",
            f"노출 URL: {primary.url}",
            f"동일 블로거 노출 글 수: {len(same_author_others)}",
        ],
        metrics={
            "competing_url": primary.url,
            "competing_rank": primary.rank,
            "competing_section": primary.section,
            "same_author_count": len(same_author_others),
        },
        recommended_action=(
            "신규 재발행보다 기존 노출 글을 강화·통합하는 편이 효율적. "
            "두 글이 같은 의도라면 정식 재작성으로 통합을 검토하세요."
        ),
    )


# ── 헬퍼 ────────────────────────────────────────────


def _count_leading_nulls(snapshots: list[RankingSnapshot]) -> int:
    """captured_at desc 정렬된 snapshots 의 선행 null 길이."""
    n = 0
    for s in snapshots:
        if s.position is not None:
            return n
        n += 1
    return n


def _author_id(url: str) -> str | None:
    """url_match._author_key 와 동일 로직 (격리를 위해 import 대신 복제).

    blog.naver.com/{user}/{post} → blog:{user}
    cafe.naver.com/{cafe}/{post} → cafe:{cafe}
    cafe.naver.com/ca-fe/cafes/{id}/articles/{post} → cafe:{id}
    in.naver.com/{user}/contents → in:{user}
    그 외 → host:{netloc}
    """
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host in ("blog.naver.com", "m.blog.naver.com"):
        return f"blog:{parts[0]}" if parts else f"blog:{host}"
    if host in ("cafe.naver.com", "m.cafe.naver.com"):
        if parts and parts[0] == "ca-fe" and len(parts) >= 3:
            return f"cafe:{parts[2]}"
        return f"cafe:{parts[0]}" if parts else f"cafe:{host}"
    if host == "in.naver.com":
        return f"in:{parts[0]}" if parts else f"in:{host}"
    return f"host:{host}"


def _normalize(url: str) -> str:
    """단순 비교용 정규화 (host lowercase + path 트레일링 슬래시 제거)."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host in ("blog.naver.com", "m.blog.naver.com"):
        host = "m.blog.naver.com"
    return f"{host}{parsed.path.rstrip('/')}"


# 미사용 import 회피용 — 향후 evidence 시간차 계산에 사용
_ = timedelta
