"""diagnosis 5개 룰 단위 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domain.diagnosis.rules import diagnose
from domain.ranking.model import Publication, RankingSnapshot, Top10Snapshot

_NOW = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)


def _pub(**overrides: object) -> Publication:
    base: dict[str, object] = {
        "id": "pub-1",
        "keyword": "kw",
        "url": "https://m.blog.naver.com/myuser/123456789",
        "published_at": _NOW - timedelta(days=10),
    }
    base.update(overrides)
    return Publication(**base)  # type: ignore[arg-type]


def _snap(position: int | None, days_ago: int) -> RankingSnapshot:
    return RankingSnapshot(
        publication_id="pub-1",
        section="인플루언서" if position else None,
        position=position,
        captured_at=_NOW - timedelta(days=days_ago),
    )


def _top10(rank: int, url: str, blog_id: str) -> Top10Snapshot:
    return Top10Snapshot(
        keyword="kw",
        captured_at=_NOW,
        rank=rank,
        url=url,
        section="인플루언서",
        blog_id=blog_id,
    )


class TestNoMeasurement:
    def test_returns_no_measurement_when_no_snapshots(self) -> None:
        result = diagnose(_pub(), [], [], now=_NOW)
        assert len(result) == 1
        assert result[0].reason == "no_measurement"
        assert result[0].confidence == 1.0


class TestNeverIndexed:
    def test_d_plus_3_starts_diagnosis(self) -> None:
        # 발행 4일 전, 모든 측정 미노출
        pub = _pub(published_at=_NOW - timedelta(days=4))
        snaps = [_snap(None, 0), _snap(None, 1), _snap(None, 2)]
        result = diagnose(pub, snaps, [], now=_NOW)
        reasons = [d.reason for d in result]
        assert "never_indexed" in reasons
        d = next(d for d in result if d.reason == "never_indexed")
        assert 0.45 <= d.confidence <= 0.6

    def test_d_plus_2_too_early(self) -> None:
        pub = _pub(published_at=_NOW - timedelta(days=2))
        snaps = [_snap(None, 0), _snap(None, 1)]
        result = diagnose(pub, snaps, [], now=_NOW)
        assert "never_indexed" not in [d.reason for d in result]

    def test_confidence_capped_at_max(self) -> None:
        pub = _pub(published_at=_NOW - timedelta(days=30))
        snaps = [_snap(None, 0)]
        result = diagnose(pub, snaps, [], now=_NOW)
        d = next(d for d in result if d.reason == "never_indexed")
        assert d.confidence <= 0.85


class TestLostVisibility:
    def test_three_consecutive_nulls_after_exposure(self) -> None:
        snaps = [
            _snap(None, 0),
            _snap(None, 1),
            _snap(None, 2),
            _snap(5, 3),
            _snap(7, 4),
        ]
        result = diagnose(_pub(), snaps, [], now=_NOW)
        d = next(d for d in result if d.reason == "lost_visibility")
        assert d.confidence >= 0.6
        assert any("연속 미노출" in e for e in d.evidence)

    def test_one_null_alone_not_diagnosed(self) -> None:
        snaps = [_snap(None, 0), _snap(5, 1), _snap(7, 2)]
        result = diagnose(_pub(), snaps, [], now=_NOW)
        assert "lost_visibility" not in [d.reason for d in result]

    def test_recent_exposure_skips_diagnosis(self) -> None:
        # 가장 최근에는 잡혀 있음
        snaps = [_snap(8, 0), _snap(None, 1), _snap(None, 2), _snap(None, 3), _snap(5, 4)]
        result = diagnose(_pub(), snaps, [], now=_NOW)
        assert "lost_visibility" not in [d.reason for d in result]


class TestCannibalization:
    def test_same_blogger_other_url_in_top10(self) -> None:
        # 우리 글은 미노출, Top10 안에 같은 블로거의 다른 글이 노출
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0), _snap(None, 1), _snap(None, 2)]
        top10 = [
            _top10(1, "https://blog.naver.com/myuser/999999999", "blog:myuser"),
            _top10(2, "https://blog.naver.com/other/888888888", "blog:other"),
        ]
        result = diagnose(pub, snaps, top10, now=_NOW)
        d = next(d for d in result if d.reason == "cannibalization")
        assert d.confidence == 0.9
        assert "동일 블로거" in d.evidence[0]

    def test_no_same_author_in_top10(self) -> None:
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0)]
        top10 = [_top10(1, "https://blog.naver.com/other/999999999", "blog:other")]
        result = diagnose(pub, snaps, top10, now=_NOW)
        assert "cannibalization" not in [d.reason for d in result]

    def test_target_currently_visible_skips_diagnosis(self) -> None:
        # 우리 글이 현재 노출 중이면 카니발 진단 부적절
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(5, 0)]
        top10 = [_top10(1, "https://blog.naver.com/myuser/999999999", "blog:myuser")]
        result = diagnose(pub, snaps, top10, now=_NOW)
        assert "cannibalization" not in [d.reason for d in result]

    # ── 다중 author 시나리오 (외부 검토 누락 지적) ──

    def test_multiple_same_author_urls_picks_lowest_rank_as_primary(self) -> None:
        """같은 블로거의 글이 Top10 에 3건 → primary 는 가장 높은 순위(낮은 rank).

        same_author_count=3 metric 정확히 기록 + competing_rank 가 최저값.
        """
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0), _snap(None, 1), _snap(None, 2)]
        top10 = [
            _top10(7, "https://blog.naver.com/myuser/777777777", "blog:myuser"),
            _top10(2, "https://blog.naver.com/myuser/222222222", "blog:myuser"),
            _top10(5, "https://blog.naver.com/myuser/555555555", "blog:myuser"),
            _top10(1, "https://blog.naver.com/other/111111111", "blog:other"),
        ]
        result = diagnose(pub, snaps, top10, now=_NOW)
        d = next(d for d in result if d.reason == "cannibalization")
        # 3건이 같은 author — primary 는 rank=2 (가장 높은 순위)
        assert d.metrics["competing_rank"] == 2
        assert d.metrics["competing_url"] == "https://blog.naver.com/myuser/222222222"
        assert d.metrics["same_author_count"] == 3
        # evidence 의 첫 줄에도 rank=2 반영
        assert " 2위" in d.evidence[0]
        assert "동일 블로거 노출 글 수: 3" in d.evidence[2]

    def test_self_url_excluded_from_same_author_others(self) -> None:
        """본인 URL 이 Top10 안에 있어도 other 카운트에서 제외 (정상 노출 케이스)."""
        # 우리 URL 이 Top10 에 있는데 latest snap 은 미노출 — 데이터 모순이지만
        # 본 테스트는 self URL 필터링 로직만 확인
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0)]  # latest 미노출 — cannibal 진단 진입
        top10 = [
            # 같은 URL (정규화 후 동등) — 제외 대상
            _top10(3, "https://blog.naver.com/myuser/123456789", "blog:myuser"),
            _top10(5, "https://blog.naver.com/myuser/999999999", "blog:myuser"),
        ]
        result = diagnose(pub, snaps, top10, now=_NOW)
        d = next(d for d in result if d.reason == "cannibalization")
        # self URL 제외 → same_author_count == 1, primary rank=5
        assert d.metrics["same_author_count"] == 1
        assert d.metrics["competing_rank"] == 5

    def test_cross_domain_author_match_m_blog_vs_blog(self) -> None:
        """publication 은 m.blog 인데 Top10 은 blog.naver.com — 같은 작성자로 인식."""
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0)]
        top10 = [
            _top10(4, "https://blog.naver.com/myuser/222222222", "blog:myuser"),
        ]
        result = diagnose(pub, snaps, top10, now=_NOW)
        assert any(d.reason == "cannibalization" for d in result)

    def test_publication_url_none_skips_diagnosis(self) -> None:
        """draft publication (url=None) 은 cannibalization 진단 대상 아님."""
        pub = _pub(url=None)
        snaps = [_snap(None, 0)]
        top10 = [_top10(3, "https://blog.naver.com/myuser/999999999", "blog:myuser")]
        result = diagnose(pub, snaps, top10, now=_NOW)
        assert "cannibalization" not in [d.reason for d in result]

    def test_competing_section_preserved_in_metric(self) -> None:
        """primary 의 section 이 metric 에 정확히 보존."""
        pub = _pub(url="https://m.blog.naver.com/myuser/123456789")
        snaps = [_snap(None, 0)]
        # rank=2 가 인기글 섹션, rank=5 는 VIEW
        top10 = [
            Top10Snapshot(
                keyword="kw",
                captured_at=_NOW,
                rank=2,
                url="https://blog.naver.com/myuser/aaa",
                section="인기글",
                blog_id="blog:myuser",
            ),
            Top10Snapshot(
                keyword="kw",
                captured_at=_NOW,
                rank=5,
                url="https://blog.naver.com/myuser/bbb",
                section="VIEW",
                blog_id="blog:myuser",
            ),
        ]
        result = diagnose(pub, snaps, top10, now=_NOW)
        d = next(d for d in result if d.reason == "cannibalization")
        # primary = rank=2 → section "인기글"
        assert d.metrics["competing_section"] == "인기글"


class TestPriority:
    def test_no_measurement_returned_alone(self) -> None:
        """결정적 진단 (no_measurement) 발견 시 단독 반환."""
        result = diagnose(_pub(), [], [], now=_NOW)
        assert len(result) == 1

    def test_multiple_situational_diagnoses_sorted_desc(self) -> None:
        # never_indexed (낮은 신뢰도) + cannibalization (0.9) → 후자가 먼저
        pub = _pub(
            url="https://m.blog.naver.com/myuser/123456789",
            published_at=_NOW - timedelta(days=4),
        )
        snaps = [_snap(None, 0), _snap(None, 1), _snap(None, 2)]
        top10 = [_top10(1, "https://blog.naver.com/myuser/999999999", "blog:myuser")]
        result = diagnose(pub, snaps, top10, now=_NOW)
        assert len(result) >= 2
        assert result[0].confidence >= result[1].confidence
