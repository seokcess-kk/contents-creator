"""parser 단위 테스트 — 합성 HTML fixture 기반.

네이버 SERP 의 실제 구조 (`div#main_pack > div.sc_new`) 를 시뮬레이션.
"""

from __future__ import annotations

import pathlib

import pytest

from domain.keyword_difficulty.model import SerpSection
from domain.keyword_difficulty.parser import parse_serp


def _wrap(body: str) -> str:
    """`div#main_pack` 으로 감싼 SERP 본문."""
    return f'<html><body><div id="main_pack">{body}</div></body></html>'


class TestParseSerp:
    def test_no_main_pack_returns_zero(self) -> None:
        comp = parse_serp("<html><body></body></html>")
        assert comp.total_cards == 0
        assert comp.blog_slots == 0

    def test_empty_main_pack(self) -> None:
        comp = parse_serp(_wrap(""))
        assert comp.total_cards == 0

    def test_ad_section_counts_lst_items(self) -> None:
        html = _wrap(
            """
            <div class="sc_new ad_section">
              <h2>광고</h2>
              <ul class="lst_type">
                <li class="lst">광고1</li>
                <li class="lst">광고2</li>
                <li class="lst">광고3</li>
              </ul>
            </div>
            """
        )
        comp = parse_serp(html)
        assert comp.section_counts.get(SerpSection.AD, 0) == 3

    def test_blog_integrated_unique_post_urls(self) -> None:
        html = _wrap(
            """
            <div class="sc_new">
              <h2>블로그</h2>
              <a href="https://blog.naver.com/u1/123456789">b1</a>
              <a href="https://blog.naver.com/u1/123456789">중복</a>
              <a href="https://blog.naver.com/u2/987654321">b2</a>
              <a href="https://blog.naver.com/u3">작성자링크 (게시물 패턴 아님 → 무시)</a>
            </div>
            """
        )
        comp = parse_serp(html)
        # 게시물 URL 2개 (작성자 프로필 / 중복 제외)
        # 제목 "블로그" → BLOG_INTEGRATED 분류
        assert comp.section_counts.get(SerpSection.BLOG_INTEGRATED, 0) == 2

    def test_view_section_blog_dominant(self) -> None:
        html = _wrap(
            """
            <div class="sc_new">
              <h2>VIEW</h2>
              <a href="https://blog.naver.com/u1/123456789">v1</a>
              <a href="https://blog.naver.com/u2/987654321">v2</a>
              <a href="https://cafe.naver.com/c1/100">c1</a>
            </div>
            """
        )
        comp = parse_serp(html)
        # 제목 'VIEW' → OTHER (제목 분류 우선) — 도메인 비중 분류는 발동 안 됨
        # OTHER 슬롯 가중치 1
        assert comp.section_counts.get(SerpSection.OTHER, 0) == 1

    def test_blog_slots_aggregate_view_and_blog_integrated(self) -> None:
        html = _wrap(
            """
            <div class="sc_new">
              <a href="https://blog.naver.com/a/111111111">v1</a>
              <a href="https://blog.naver.com/b/222222222">v2</a>
              <a href="https://blog.naver.com/c/333333333">v3</a>
            </div>
            <div class="sc_new">
              <h2>블로그</h2>
              <a href="https://blog.naver.com/x/444444444">i1</a>
              <a href="https://blog.naver.com/y/555555555">i2</a>
            </div>
            """
        )
        comp = parse_serp(html)
        # 첫 섹션은 도메인 비중으로 VIEW_BLOG → 게시물 URL 3개
        # 두 번째는 제목으로 BLOG_INTEGRATED → URL 2개
        assert comp.section_counts.get(SerpSection.VIEW_BLOG, 0) == 3
        assert comp.section_counts.get(SerpSection.BLOG_INTEGRATED, 0) == 2
        assert comp.blog_slots == 5

    def test_shopping_section_uses_slot_weight(self) -> None:
        html = _wrap(
            '<div class="sc_new"><h2>쇼핑</h2><a href="https://shopping.naver.com/x">s</a></div>'
        )
        comp = parse_serp(html)
        # 쇼핑 섹션은 _SLOT_WEIGHT (3) 적용
        assert comp.section_counts.get(SerpSection.SHOPPING, 0) == 3

    def test_widget_section_via_title(self) -> None:
        html = _wrap('<div class="sc_new"><h2>지식백과</h2></div>')
        comp = parse_serp(html)
        assert comp.section_counts.get(SerpSection.WIDGET, 0) == 3

    def test_kin_section_unique_urls(self) -> None:
        html = _wrap(
            """
            <div class="sc_new">
              <h2>지식iN</h2>
              <a href="https://kin.naver.com/qna/detail/111">q1</a>
              <a href="https://kin.naver.com/qna/detail/222">q2</a>
              <a href="https://kin.naver.com/qna/detail/111">중복</a>
            </div>
            """
        )
        comp = parse_serp(html)
        assert comp.section_counts.get(SerpSection.KNOWLEDGE_IN, 0) == 2

    def test_smartblock_h2_subtopic_counted(self) -> None:
        """명시적 sub-topic 헤더 (h2) 가 있는 섹션 → 스마트블록."""
        html = _wrap(
            '<div class="sc_new"><h2>강남역 다이어트 맛집</h2></div>'
            '<div class="sc_new"><h2>강남역 다이어트약</h2></div>'
            "<div class=\"sc_new\"><h2>'강남역다이어트' 관련 브랜드 콘텐츠</h2></div>"
        )
        comp = parse_serp(html)
        assert comp.smartblock.present is True
        assert comp.smartblock.count == 3

    def test_smartblock_excludes_ads_and_widgets(self) -> None:
        """광고/플레이스/가격비교/스토어/지식백과/뉴스 등 위젯 헤더는 제외."""
        html = _wrap(
            '<div class="sc_new ad_section"><h2>관련 광고</h2></div>'
            '<div class="sc_new"><h2>플레이스</h2></div>'
            '<div class="sc_new"><h2>네이버 가격비교</h2></div>'
            '<div class="sc_new"><h2>네이버플러스 스토어</h2></div>'
            '<div class="sc_new"><h2>지식백과</h2></div>'
            '<div class="sc_new"><h2>뉴스</h2></div>'
        )
        comp = parse_serp(html)
        assert comp.smartblock.present is False
        assert comp.smartblock.count == 0

    def test_smartblock_excludes_influencer_and_popular(self) -> None:
        """사용자 운영 정의 — 인플루언서·인기글 헤더는 명시적으로 제외."""
        html = _wrap(
            '<div class="sc_new"><h2>인플루언서</h2></div>'
            "<div class=\"sc_new\"><h2>'강남역다이어트' 인기글</h2></div>"
            '<div class="sc_new"><h2>건강·의학 인기글</h2></div>'
        )
        comp = parse_serp(html)
        assert comp.smartblock.present is False
        assert comp.smartblock.count == 0

    def test_smartblock_skips_sections_without_h2(self) -> None:
        """h2/h3 가 없는 sc_new (단순 카드 컨테이너) 는 스마트블록 X."""
        html = _wrap(
            '<div class="sc_new" data-meta-area="rrB_bdR">'
            '<a href="https://blog.naver.com/x/111111111">card1</a>'
            "</div>"
            '<div class="sc_new" data-meta-area="rrB_bdR">'
            '<a href="https://blog.naver.com/y/222222222">card2</a>'
            "</div>"
        )
        comp = parse_serp(html)
        assert comp.smartblock.present is False
        assert comp.smartblock.count == 0

    def test_smartblock_mixed_real_world_subset(self) -> None:
        """실측 강남역다이어트 SERP 의 h2 6종 — 광고/플레이스/인기글 제외하면 3개."""
        html = _wrap(
            '<div class="sc_new ad_section"><h2>강남역다이어트관련 광고</h2></div>'
            '<div class="sc_new"><h2>플레이스</h2></div>'
            '<div class="sc_new"><h2>강남역 다이어트 맛집</h2></div>'
            "<div class=\"sc_new\"><h2>'강남역다이어트' 인기글</h2></div>"
            '<div class="sc_new"><h2>강남역 다이어트약</h2></div>'
            "<div class=\"sc_new\"><h2>'강남역다이어트' 관련 브랜드 콘텐츠</h2></div>"
        )
        comp = parse_serp(html)
        assert comp.smartblock.count == 3

    def test_total_aggregates_across_sections(self) -> None:
        html = _wrap(
            """
            <div class="sc_new ad_section">
              <ul class="lst_type"><li class="lst">a1</li><li class="lst">a2</li></ul>
            </div>
            <div class="sc_new">
              <h2>블로그</h2>
              <a href="https://blog.naver.com/x/111111111">b</a>
            </div>
            <div class="sc_new"><h2>쇼핑</h2></div>
            """
        )
        comp = parse_serp(html)
        # ad=2 + blog_integrated=1 + shopping=3 = 6
        assert comp.total_cards == 6


_FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "integrated_serp"


@pytest.mark.skipif(
    not _FIXTURE_DIR.exists() or not any(_FIXTURE_DIR.glob("*.html")),
    reason="integrated_serp fixtures 미설치",
)
class TestSmartblockRegressionLiveFixtures:
    """실측 네이버 통합검색 HTML fixture 기반 스마트블록 감지 regression.

    2026-05-12 v2 운영 정의: 명시적 sub-topic 헤더(h2/h3), 인플루언서·인기글
    제외. 89개 의료 키워드 fixture 중 8개에서 1+개 감지 (강남역다이어트=3 최대).
    이 영역은 키워드별 변동성이 큰 영역이므로 회귀 임계값은 보수적으로 둠.
    """

    def test_at_least_some_fixtures_have_smartblock(self) -> None:
        files = sorted(_FIXTURE_DIR.glob("*.html"))
        assert len(files) >= 20, "fixture 갯수 부족 (최소 20개)"
        hit = 0
        for f in files:
            comp = parse_serp(f.read_text(encoding="utf-8", errors="ignore"))
            if comp.smartblock.present:
                hit += 1
        # 새 정의 (h2 sub-topic) 는 sparse. 3개 미만이면 셀렉터 회귀 의심.
        assert hit >= 3, f"스마트블록 감지 키워드 {hit}개 — 셀렉터 회귀 의심"

    def test_known_keyword_gangnam_dieat_has_three(self) -> None:
        """강남역다이어트 — 사용자 검증 ground truth. 3개 sub-topic 헤더 유지."""
        p = _FIXTURE_DIR / "강남역다이어트.html"
        if not p.exists():
            pytest.skip("강남역다이어트.html fixture 없음")
        comp = parse_serp(p.read_text(encoding="utf-8", errors="ignore"))
        assert comp.smartblock.count == 3

    def test_present_count_consistency(self) -> None:
        """present 와 count 는 정합 — present=True 면 count>=1, present=False 면 count==0."""
        files = sorted(_FIXTURE_DIR.glob("*.html"))
        for f in files:
            comp = parse_serp(f.read_text(encoding="utf-8", errors="ignore"))
            sb = comp.smartblock
            if sb.present:
                assert sb.count >= 1, f"{f.name}: present True but count {sb.count}"
            else:
                assert sb.count == 0, f"{f.name}: present False but count {sb.count}"
