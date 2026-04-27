"""tracker.find_position 단위 테스트.

새 구조: parse_integrated_serp 가 HTML 을 직접 받아 섹션을 추출하므로,
테스트도 fetcher 가 반환하는 HTML 문자열로 동작을 검증한다.
서브 fixture HTML 은 tests/fixtures/integrated_serp/*.html 사용.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.ranking.model import RankingMatchError
from domain.ranking.tracker import find_position

_FIXTURE_DIR = Path("tests/fixtures/integrated_serp")


def _builder(keyword: str) -> str:
    return f"https://search.naver.com/search.naver?where=nexearch&query={keyword}"


class TestFindPosition:
    def test_matched_in_section(self) -> None:
        """수성구 fixture: target 이 인기글 섹션 4위에 매칭되어야."""
        html = (_FIXTURE_DIR / "수성구다이어트한의원.html").read_text(encoding="utf-8")
        snap = find_position(
            keyword="수성구다이어트한의원",
            target_url="https://blog.naver.com/taq87641/224248214490",
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: html,
        )
        assert snap.section == "인기글"
        assert snap.position == 4
        assert snap.publication_id == "pub-1"
        assert snap.total_results is not None and snap.total_results > 0

    def test_not_exposed_returns_none(self) -> None:
        """압구정한의원 fixture: target URL 이 HTML 에 없어 미노출."""
        html = (_FIXTURE_DIR / "압구정한의원.html").read_text(encoding="utf-8")
        snap = find_position(
            keyword="압구정한의원",
            target_url="https://blog.naver.com/taq87641/224246820601",
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: html,
        )
        assert snap.section is None
        assert snap.position is None

    def test_fetcher_exception_wrapped(self) -> None:
        def bad_fetcher(_: str) -> str:
            raise RuntimeError("network down")

        with pytest.raises(RankingMatchError, match="SERP fetch"):
            find_position(
                keyword="kw",
                target_url="https://blog.naver.com/u/123456789",
                publication_id="pub-1",
                serp_url_builder=_builder,
                serp_fetcher=bad_fetcher,
            )

    def test_parser_exception_wrapped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def bad_parser(_: str) -> object:
            raise ValueError("malformed")

        monkeypatch.setattr("domain.ranking.tracker.parse_integrated_serp", bad_parser)
        with pytest.raises(RankingMatchError, match="SERP parse"):
            find_position(
                keyword="kw",
                target_url="https://blog.naver.com/u/123456789",
                publication_id="pub-1",
                serp_url_builder=_builder,
                serp_fetcher=lambda _: "<html/>",
            )
