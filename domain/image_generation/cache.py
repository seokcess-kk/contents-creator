"""SHA256 해시 기반 이미지 파일 캐시.

캐시 위치: `output/_image_cache/{hash}.png` (settings.image_cache_dir).
동일 prompt 텍스트 → 동일 해시 → API 재호출 없이 재사용.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def compute_cache_key(prompt: str) -> str:
    """prompt 텍스트 → SHA256 hex digest."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def get_cached(cache_dir: Path, key: str) -> Path | None:
    """캐시 히트 시 경로 반환, 미스 시 None."""
    path = cache_dir / f"{key}.png"
    if path.exists():
        logger.debug("cache hit: %s", key[:12])
        return path
    return None


def save_to_cache(cache_dir: Path, key: str, data: bytes) -> Path:
    """이미지 바이트를 캐시에 저장하고 경로 반환."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.png"
    path.write_bytes(data)
    logger.debug("cached: %s (%d bytes)", key[:12], len(data))
    return path


def copy_from_cache(cached_path: Path, dest: Path) -> None:
    """캐시 파일을 대상 경로로 복사."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached_path, dest)
