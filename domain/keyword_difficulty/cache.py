"""SERP HTML 메모리 캐시.

같은 키워드를 짧은 시간 내 재분석할 때 Bright Data 호출을 우회한다.
Render 단일 인스턴스 전제 — 다중 인스턴스 운영 시 Supabase Storage 또는 Redis
로 마이그레이션 필요.

캐시 hit 시 record_usage 호출하지 않는다 (실제 외부 호출이 없으므로).

TTL/max_entries 는 settings 에서 동적 로딩 — 운영 중 env 로 보정 가능.
2026-05-04: 30 → 60 분으로 상향 (Phase F 후속). SERP 변동 빈도 대비 안전.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import NamedTuple

from config.settings import settings

logger = logging.getLogger(__name__)

# 폴백 default — settings 로딩 실패 시.
DEFAULT_TTL_SEC = 60 * 60  # 60분 (2026-05-04 상향)
DEFAULT_MAX_ENTRIES = 256  # LRU 보호


class _Entry(NamedTuple):
    html: str
    fetched_at: float


class SerpCache:
    """스레드 안전 LRU + TTL 캐시. 키 = 정규화된 키워드."""

    def __init__(
        self,
        ttl_sec: int = DEFAULT_TTL_SEC,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._ttl = ttl_sec
        self._max = max_entries
        self._lock = threading.Lock()
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, keyword: str) -> str | None:
        """캐시 hit 시 HTML 반환, miss 또는 만료 시 None."""
        key = self._key(keyword)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                self._log_periodic("miss", keyword)
                return None
            if time.monotonic() - entry.fetched_at > self._ttl:
                # 만료
                self._store.pop(key, None)
                self._misses += 1
                self._log_periodic("expired", keyword)
                return None
            # LRU 업데이트
            self._store.move_to_end(key)
            self._hits += 1
            self._log_periodic("hit", keyword)
            return entry.html

    def _log_periodic(self, event: str, keyword: str) -> None:
        """매 50회 이벤트마다 누적 통계 1줄 — 매 hit 마다 찍는 노이즈 회피."""
        total = self._hits + self._misses
        if total % 50 == 0:
            hit_ratio = self._hits / total if total else 0.0
            logger.info(
                "serp_cache.stats hits=%d misses=%d hit_ratio=%.1f%% size=%d ttl_sec=%d "
                "last_event=%s last_keyword=%s",
                self._hits,
                self._misses,
                hit_ratio * 100,
                len(self._store),
                self._ttl,
                event,
                keyword,
            )

    def put(self, keyword: str, html: str) -> None:
        key = self._key(keyword)
        with self._lock:
            self._store[key] = _Entry(html=html, fetched_at=time.monotonic())
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                # 가장 오래된 항목 제거
                self._store.popitem(last=False)

    def info(self) -> dict[str, int]:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "ttl_sec": self._ttl,
                "max_entries": self._max,
            }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @staticmethod
    def _key(keyword: str) -> str:
        return keyword.strip().lower()


# 모듈 레벨 싱글턴 — orchestrator 가 직접 사용.
# settings 에서 TTL/max_entries 읽어 운영 중 env 로 조정 가능.
_cache = SerpCache(
    ttl_sec=settings.keyword_difficulty_cache_ttl_seconds,
    max_entries=settings.keyword_difficulty_cache_max_entries,
)


def get_cached(keyword: str) -> str | None:
    return _cache.get(keyword)


def put_cached(keyword: str, html: str) -> None:
    _cache.put(keyword, html)


def cache_info() -> dict[str, int]:
    return _cache.info()


def clear_cache() -> None:
    _cache.clear()
