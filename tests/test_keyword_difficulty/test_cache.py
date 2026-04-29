"""SERP 메모리 캐시 단위 테스트."""

from __future__ import annotations

import time
from unittest.mock import patch

from domain.keyword_difficulty.cache import SerpCache


class TestSerpCache:
    def test_miss_returns_none(self) -> None:
        cache = SerpCache()
        assert cache.get("test") is None

    def test_put_then_get(self) -> None:
        cache = SerpCache()
        cache.put("키워드", "<html>...</html>")
        assert cache.get("키워드") == "<html>...</html>"

    def test_normalized_key_case_insensitive(self) -> None:
        cache = SerpCache()
        cache.put("KeYwOrD", "html")
        assert cache.get("keyword") == "html"
        assert cache.get(" KEYWORD ") == "html"

    def test_ttl_expiry(self) -> None:
        cache = SerpCache(ttl_sec=60)
        cache.put("k", "html")
        # 가짜 시간 흐름 — monotonic 을 미래로
        with patch(
            "domain.keyword_difficulty.cache.time.monotonic",
            return_value=time.monotonic() + 3600,
        ):
            assert cache.get("k") is None

    def test_lru_eviction(self) -> None:
        cache = SerpCache(max_entries=3)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        cache.put("d", "4")  # a 추출
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"
        assert cache.get("d") == "4"

    def test_lru_recent_access_protected(self) -> None:
        """최근 접근한 항목은 evict 되지 않는다."""
        cache = SerpCache(max_entries=3)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        cache.get("a")  # a 를 most-recent 로 끌어올림
        cache.put("d", "4")  # b 가 추출되어야 함
        assert cache.get("a") == "1"
        assert cache.get("b") is None
        assert cache.get("c") == "3"
        assert cache.get("d") == "4"

    def test_info_tracks_hits_and_misses(self) -> None:
        cache = SerpCache()
        cache.get("missing")
        cache.put("k", "v")
        cache.get("k")
        cache.get("k")
        info = cache.info()
        assert info["hits"] == 2
        assert info["misses"] == 1
        assert info["size"] == 1

    def test_clear(self) -> None:
        cache = SerpCache()
        cache.put("a", "1")
        cache.clear()
        assert cache.get("a") is None
        assert cache.info()["size"] == 0
