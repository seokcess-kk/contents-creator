"""tracker.find_position 단위 테스트 — fake fetcher/parser 주입."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from domain.ranking.model import RankingMatchError
from domain.ranking.tracker import find_position


@dataclass
class FakeSerpItem:
    """ParsedSerpItem Protocol 호환."""

    rank: int
    url: str
    title: str = ""


def _builder(keyword: str) -> str:
    return f"https://search.naver.com/?q={keyword}"


def _items_with(*urls: str) -> list[Any]:
    return [FakeSerpItem(rank=i + 1, url=u) for i, u in enumerate(urls)]


class TestFindPosition:
    def test_first_position(self) -> None:
        target = "https://blog.naver.com/myblog/123456789"
        items = _items_with(
            "https://m.blog.naver.com/myblog/123456789",
            "https://blog.naver.com/other/999999999",
        )
        snap = find_position(
            keyword="kw",
            target_url=target,
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: "<html/>",
            serp_parser=lambda _: items,
        )
        assert snap.position == 1
        assert snap.total_results == 2
        assert snap.publication_id == "pub-1"

    def test_fifth_position(self) -> None:
        target = "https://blog.naver.com/myblog/123456789"
        items = _items_with(
            *[f"https://blog.naver.com/u{i}/{100000000 + i}" for i in range(4)],
            "https://m.blog.naver.com/myblog/123456789",
        )
        snap = find_position(
            keyword="kw",
            target_url=target,
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: "<html/>",
            serp_parser=lambda _: items,
        )
        assert snap.position == 5

    def test_off_chart_returns_none(self) -> None:
        target = "https://blog.naver.com/myblog/123456789"
        items = _items_with("https://blog.naver.com/other/999999999")
        snap = find_position(
            keyword="kw",
            target_url=target,
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: "<html/>",
            serp_parser=lambda _: items,
        )
        assert snap.position is None
        assert snap.total_results == 1

    def test_fetcher_exception_wrapped(self) -> None:
        def bad_fetcher(_: str) -> str:
            raise RuntimeError("network")

        with pytest.raises(RankingMatchError, match="SERP fetch"):
            find_position(
                keyword="kw",
                target_url="https://blog.naver.com/myblog/123456789",
                publication_id="pub-1",
                serp_url_builder=_builder,
                serp_fetcher=bad_fetcher,
                serp_parser=lambda _: [],
            )

    def test_parser_exception_wrapped(self) -> None:
        def bad_parser(_: str) -> list[Any]:
            raise ValueError("malformed")

        with pytest.raises(RankingMatchError, match="SERP parse"):
            find_position(
                keyword="kw",
                target_url="https://blog.naver.com/myblog/123456789",
                publication_id="pub-1",
                serp_url_builder=_builder,
                serp_fetcher=lambda _: "<html/>",
                serp_parser=bad_parser,
            )

    def test_empty_results(self) -> None:
        snap = find_position(
            keyword="kw",
            target_url="https://blog.naver.com/myblog/123456789",
            publication_id="pub-1",
            serp_url_builder=_builder,
            serp_fetcher=lambda _: "<html/>",
            serp_parser=lambda _: [],
        )
        assert snap.position is None
        assert snap.total_results == 0
