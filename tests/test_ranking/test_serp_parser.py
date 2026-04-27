"""serp_parser 회귀 테스트 — 실측 fixture 14건.

PoC 검증된 케이스를 fixture 로 정착하여 네이버 SERP DOM 변경 감지.
- 노출 9건 — 매칭된 섹션·순위가 실측과 일치
- 미노출 5건 — 어느 섹션에서도 발견되지 않음
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.ranking.serp_parser import find_section_position, parse_integrated_serp

_FIXTURE_DIR = Path("tests/fixtures/integrated_serp")


_EXPOSED_CASES = [
    # (keyword, target_url, expected_section, expected_position)
    ("수성구다이어트한의원", "https://blog.naver.com/taq87641/224248214490", "인기글", 4),
    ("동대구다이어트", "https://blog.naver.com/taq87641/224247446940", "인플루언서", 3),
    ("부평구다이어트한의원", "https://blog.naver.com/wob926883/224246841615", "인플루언서", 2),
    ("우만동다이어트", "https://blog.naver.com/wob926883/224246848338", "VIEW", 3),
    ("장항동다이어트", "https://blog.naver.com/taq87641/224246875951", "VIEW", 2),
    ("웨스턴돔다이어트한의원", "https://blog.naver.com/wob926883/224246895814", "인플루언서", 2),
    ("고양다이어트한의원", "https://blog.naver.com/taq87641/224246883027", "인플루언서", 5),
    ("진구다이어트한의원", "https://blog.naver.com/wob926883/224246902914", "인플루언서", 2),
    ("범일역다이어트", "https://blog.naver.com/taq87641/224246888807", "인플루언서", 1),
]


_HIDDEN_CASES = [
    ("압구정한의원", "https://blog.naver.com/taq87641/224246820601"),
    ("강남마운자로", "https://blog.naver.com/wob926883/224251807284"),
    ("다이어트클리닉", "https://blog.naver.com/wob926883/224251793087"),
    ("강남역다이어트", "https://blog.naver.com/taq87641/224251814129"),
    ("부평다이어트한의원", "https://blog.naver.com/taq87641/224250357980"),
]


@pytest.mark.parametrize(("keyword", "target_url", "section", "position"), _EXPOSED_CASES)
def test_exposed_cases(keyword: str, target_url: str, section: str, position: int) -> None:
    html = (_FIXTURE_DIR / f"{keyword}.html").read_text(encoding="utf-8")
    result = parse_integrated_serp(html)
    match = find_section_position(result, target_url)
    assert match is not None, f"{keyword}: target should be found"
    assert match.section == section
    assert match.position == position


@pytest.mark.parametrize(("keyword", "target_url"), _HIDDEN_CASES)
def test_hidden_cases(keyword: str, target_url: str) -> None:
    html = (_FIXTURE_DIR / f"{keyword}.html").read_text(encoding="utf-8")
    result = parse_integrated_serp(html)
    match = find_section_position(result, target_url)
    assert match is None, f"{keyword}: target should NOT be found"


def test_excludes_ad_and_place_sections() -> None:
    """광고·플레이스 섹션은 결과에 포함되지 않아야."""
    html = (_FIXTURE_DIR / "수성구다이어트한의원.html").read_text(encoding="utf-8")
    result = parse_integrated_serp(html)
    section_names = {s.name for s in result.sections}
    assert "광고" not in section_names
    assert "플레이스" not in section_names
    assert "쇼핑" not in section_names


def test_section_order_preserved() -> None:
    """섹션은 DOM 순서대로 반환되어야."""
    html = (_FIXTURE_DIR / "동대구다이어트.html").read_text(encoding="utf-8")
    result = parse_integrated_serp(html)
    names = [s.name for s in result.sections]
    # 동대구는 인플루언서 → 뉴스 → VIEW 순서로 노출
    assert names[0] == "인플루언서"
    assert "뉴스" in names
    assert "VIEW" in names
