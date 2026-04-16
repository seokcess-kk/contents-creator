"""cache.py 테스트 — SHA256 일관성, 히트/미스, 저장, 복사."""

from __future__ import annotations

from pathlib import Path

from domain.image_generation.cache import (
    compute_cache_key,
    copy_from_cache,
    get_cached,
    save_to_cache,
)


class TestComputeCacheKey:
    def test_deterministic(self) -> None:
        """동일 prompt 에 대해 항상 동일 해시."""
        prompt = "A beautiful Korean landscape, no text"
        key1 = compute_cache_key(prompt)
        key2 = compute_cache_key(prompt)
        assert key1 == key2

    def test_different_prompts_different_keys(self) -> None:
        key_a = compute_cache_key("prompt A, no text")
        key_b = compute_cache_key("prompt B, no text")
        assert key_a != key_b

    def test_hex_format(self) -> None:
        key = compute_cache_key("test prompt")
        assert len(key) == 64  # SHA256 hex digest
        assert all(c in "0123456789abcdef" for c in key)


class TestGetCached:
    def test_miss(self, tmp_path: Path) -> None:
        result = get_cached(tmp_path, "nonexistent_key")
        assert result is None

    def test_hit(self, tmp_path: Path) -> None:
        key = "abc123def456"
        (tmp_path / f"{key}.png").write_bytes(b"PNG_DATA")
        result = get_cached(tmp_path, key)
        assert result is not None
        assert result.name == f"{key}.png"


class TestSaveToCache:
    def test_creates_file(self, tmp_path: Path) -> None:
        key = "test_key_123"
        data = b"\x89PNG_TEST_DATA"
        path = save_to_cache(tmp_path, key, data)
        assert path.exists()
        assert path.read_bytes() == data

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "sub" / "dir"
        key = "nested_key"
        save_to_cache(nested, key, b"data")
        assert (nested / f"{key}.png").exists()


class TestCopyFromCache:
    def test_copy(self, tmp_path: Path) -> None:
        src = tmp_path / "cache" / "src.png"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"IMAGE_BYTES")

        dest = tmp_path / "output" / "images" / "image_1.png"
        copy_from_cache(src, dest)

        assert dest.exists()
        assert dest.read_bytes() == b"IMAGE_BYTES"
