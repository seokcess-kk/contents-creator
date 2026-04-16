"""generator.py 테스트 — mock provider 로 성공/실패/캐시/예산 검증."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

from domain.image_generation.cache import compute_cache_key, save_to_cache
from domain.image_generation.generator import generate_images
from domain.image_generation.model import ImagePrompt
from domain.image_generation.provider import ImageGenerationError


def _make_valid_png(width: int = 100, height: int = 100) -> bytes:
    """Pillow 로 열 수 있는 유효한 PNG 바이트 생성."""
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# 테스트 전역에서 공유하는 유효한 PNG 바이트
_VALID_PNG = _make_valid_png()


def _make_prompt(
    seq: int = 1,
    prompt: str = "A Korean landscape, warm tones, no text",
) -> ImagePrompt:
    return ImagePrompt(
        sequence=seq,
        position="after_intro",
        prompt=prompt,
        alt_text=f"alt_{seq}",
        image_type="photo",
        rationale="test",
    )


def _make_mock_provider(data: bytes | None = None) -> MagicMock:
    provider = MagicMock()
    provider.generate.return_value = data if data is not None else _VALID_PNG
    return provider


class TestGenerateImagesSuccess:
    def test_single_prompt_success(self, tmp_path: Path) -> None:
        provider = _make_mock_provider()
        prompts = [_make_prompt(1)]

        result = generate_images(
            prompts=prompts,
            output_dir=tmp_path,
            provider=provider,
            cache_dir=tmp_path / "cache",
        )

        assert len(result.generated) == 1
        assert len(result.skipped) == 0
        assert result.generated[0].sequence == 1
        assert result.generated[0].alt_text == "alt_1"
        # 파일이 실제로 존재
        assert (tmp_path / "images" / "image_1.jpg").exists()
        # 캐시에도 존재
        key = compute_cache_key(prompts[0].prompt)
        assert (tmp_path / "cache" / f"{key}.png").exists()

    def test_multiple_prompts(self, tmp_path: Path) -> None:
        provider = _make_mock_provider()
        prompts = [_make_prompt(i, f"prompt {i}, no text") for i in range(1, 4)]

        result = generate_images(
            prompts=prompts,
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.generated) == 3
        assert provider.generate.call_count == 3


class TestCacheHit:
    def test_cache_hit_skips_api(self, tmp_path: Path) -> None:
        prompt = _make_prompt(1)
        cache_dir = tmp_path / "cache"
        key = compute_cache_key(prompt.prompt)
        save_to_cache(cache_dir, key, _VALID_PNG)

        provider = _make_mock_provider()
        result = generate_images(
            prompts=[prompt],
            output_dir=tmp_path,
            provider=provider,
            cache_dir=cache_dir,
        )

        assert len(result.generated) == 1
        # API 호출 없음
        provider.generate.assert_not_called()
        # 출력 파일이 존재 (optimize 후 JPEG 이므로 바이트는 다를 수 있음)
        assert (tmp_path / "images" / "image_1.jpg").exists()

    def test_regenerate_ignores_cache(self, tmp_path: Path) -> None:
        prompt = _make_prompt(1)
        cache_dir = tmp_path / "cache"
        key = compute_cache_key(prompt.prompt)
        save_to_cache(cache_dir, key, _make_valid_png(50, 50))

        provider = _make_mock_provider(_make_valid_png(200, 200))
        result = generate_images(
            prompts=[prompt],
            output_dir=tmp_path,
            provider=provider,
            cache_dir=cache_dir,
            regenerate=True,
        )

        assert len(result.generated) == 1
        provider.generate.assert_called_once()
        assert (tmp_path / "images" / "image_1.jpg").exists()


class TestBudgetGuard:
    def test_budget_exceeded_skips_remaining(self, tmp_path: Path) -> None:
        provider = _make_mock_provider()
        prompts = [_make_prompt(i, f"prompt {i}, no text") for i in range(1, 5)]

        result = generate_images(
            prompts=prompts,
            output_dir=tmp_path,
            provider=provider,
            budget=2,
        )

        assert len(result.generated) == 2
        assert len(result.skipped) == 2
        assert all(s.reason == "budget_exceeded" for s in result.skipped)
        assert provider.generate.call_count == 2

    def test_cache_hit_does_not_count_budget(self, tmp_path: Path) -> None:
        """캐시 히트는 예산 카운트에 포함하지 않는다."""
        cache_dir = tmp_path / "cache"

        # prompt 1 을 캐시에 미리 넣기
        p1 = _make_prompt(1)
        key = compute_cache_key(p1.prompt)
        save_to_cache(cache_dir, key, _VALID_PNG)

        provider = _make_mock_provider()
        prompts = [
            p1,
            _make_prompt(2, "fresh prompt 2, no text"),
            _make_prompt(3, "fresh prompt 3, no text"),
        ]

        result = generate_images(
            prompts=prompts,
            output_dir=tmp_path,
            provider=provider,
            cache_dir=cache_dir,
            budget=2,
        )

        # 캐시 히트 1 + API 호출 2 = 3개 generated, 0 skipped
        assert len(result.generated) == 3
        assert len(result.skipped) == 0
        assert provider.generate.call_count == 2


class TestApiError:
    def test_single_failure_retries_then_skips(self, tmp_path: Path) -> None:
        provider = MagicMock()
        provider.generate.side_effect = ImageGenerationError("network error")

        result = generate_images(
            prompts=[_make_prompt(1)],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.generated) == 0
        assert len(result.skipped) == 1
        assert result.skipped[0].reason == "api_error"
        # 2회 시도 (1차 + 1회 재시도)
        assert provider.generate.call_count == 2

    def test_first_fail_second_success(self, tmp_path: Path) -> None:
        provider = MagicMock()
        provider.generate.side_effect = [
            ImageGenerationError("transient"),
            _VALID_PNG,
        ]

        result = generate_images(
            prompts=[_make_prompt(1)],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.generated) == 1
        assert len(result.skipped) == 0
        assert provider.generate.call_count == 2

    def test_pipeline_continues_after_error(self, tmp_path: Path) -> None:
        """하나 실패해도 나머지 prompt 는 처리 계속."""
        provider = MagicMock()
        provider.generate.side_effect = [
            ImageGenerationError("fail"),
            ImageGenerationError("fail"),  # seq 1 재시도도 실패
            _VALID_PNG,  # seq 2 성공
        ]

        prompts = [
            _make_prompt(1, "prompt 1, no text"),
            _make_prompt(2, "prompt 2, no text"),
        ]
        result = generate_images(
            prompts=prompts,
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.generated) == 1
        assert result.generated[0].sequence == 2
        assert len(result.skipped) == 1
        assert result.skipped[0].sequence == 1


class TestPromptSafetyValidation:
    def test_missing_no_text_skips(self, tmp_path: Path) -> None:
        """'no text' 누락 prompt 는 생성 없이 스킵."""
        bad_prompt = _make_prompt(1, "A Korean landscape, warm tones")
        provider = _make_mock_provider()

        result = generate_images(
            prompts=[bad_prompt],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.skipped) == 1
        assert result.skipped[0].reason == "prompt_safety_failed"
        provider.generate.assert_not_called()

    def test_forbidden_keyword_skips(self, tmp_path: Path) -> None:
        bad_prompt = _make_prompt(1, "patient recovery scene, no text")
        provider = _make_mock_provider()

        result = generate_images(
            prompts=[bad_prompt],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.skipped) == 1
        assert result.skipped[0].reason == "prompt_safety_failed"

    def test_people_without_korean_skips(self, tmp_path: Path) -> None:
        bad_prompt = _make_prompt(1, "A woman doing yoga, no text")
        provider = _make_mock_provider()

        result = generate_images(
            prompts=[bad_prompt],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.skipped) == 1
        assert result.skipped[0].reason == "prompt_safety_failed"

    def test_people_with_korean_passes(self, tmp_path: Path) -> None:
        good_prompt = _make_prompt(1, "A Korean woman doing yoga, no text")
        provider = _make_mock_provider()

        result = generate_images(
            prompts=[good_prompt],
            output_dir=tmp_path,
            provider=provider,
        )

        assert len(result.generated) == 1
        assert len(result.skipped) == 0


class TestNoPrompts:
    def test_empty_list(self, tmp_path: Path) -> None:
        result = generate_images(
            prompts=[],
            output_dir=tmp_path,
            provider=_make_mock_provider(),
        )
        assert result.generated == []
        assert result.skipped == []
