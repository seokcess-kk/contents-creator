"""이미지 생성 메인 진입점.

검증된 image_prompts 를 순회하며 캐시 확인 → API 호출 → 저장.
예산 가드, 1회 재시도, 실패 시 스킵 (파이프라인 계속).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from domain.image_generation.cache import (
    compute_cache_key,
    copy_from_cache,
    get_cached,
    save_to_cache,
)
from domain.image_generation.model import (
    GeneratedImage,
    ImageGenerationResult,
    ImagePrompt,
    SkippedImage,
)
from domain.image_generation.prompt_validator import (
    InvalidImagePromptError,
    validate_prompt,
)
from domain.image_generation.provider import ImageGenerationError, ImageProvider

logger = logging.getLogger(__name__)

_RETRY_DELAY_SECONDS = 1.0


def generate_images(
    prompts: list[ImagePrompt],
    output_dir: Path,
    provider: ImageProvider | None = None,
    cache_dir: Path | None = None,
    budget: int | None = None,
    regenerate: bool = False,
) -> ImageGenerationResult:
    """검증 통과된 prompt 리스트로 이미지를 생성한다.

    Args:
        prompts: [6] outline 에서 생성, [8] compliance 통과된 prompt 리스트.
        output_dir: images/ 디렉토리 상위 (output/{slug}/{ts}/).
        provider: ImageProvider 구현체. None 이면 기본 Gemini 생성.
        cache_dir: 캐시 디렉토리. None 이면 캐시 사용 안 함.
        budget: 최대 API 호출 수. None 이면 무제한.
        regenerate: True 면 캐시 무시.

    Returns:
        ImageGenerationResult with generated/skipped lists.
    """
    if provider is None:
        provider = _create_default_provider()

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    generated: list[GeneratedImage] = []
    skipped: list[SkippedImage] = []
    api_call_count = 0

    for prompt_item in prompts:
        # 예산 가드 — 실제 API 호출 수만 카운트 (캐시 히트 제외)
        if budget is not None and api_call_count >= budget:
            logger.warning(
                "image budget exceeded (%d), skipping sequence %d",
                budget,
                prompt_item.sequence,
            )
            skipped.append(
                SkippedImage(
                    sequence=prompt_item.sequence,
                    reason="budget_exceeded",
                )
            )
            continue

        result = _process_single_prompt(
            prompt_item=prompt_item,
            images_dir=images_dir,
            provider=provider,
            cache_dir=cache_dir,
            regenerate=regenerate,
        )

        if isinstance(result, GeneratedImage):
            generated.append(result)
        elif isinstance(result, SkippedImage):
            skipped.append(result)
        else:
            # api_call_happened 플래그
            gen_img, called_api = result
            generated.append(gen_img)
            if called_api:
                api_call_count += 1

    return ImageGenerationResult(generated=generated, skipped=skipped)


def _process_single_prompt(
    prompt_item: ImagePrompt,
    images_dir: Path,
    provider: ImageProvider,
    cache_dir: Path | None,
    regenerate: bool,
) -> SkippedImage | tuple[GeneratedImage, bool]:
    """단일 prompt 처리. 성공 시 (GeneratedImage, api_called), 실패 시 SkippedImage."""
    cache_key = compute_cache_key(prompt_item.prompt)
    dest_path = images_dir / f"image_{prompt_item.sequence}.png"
    relative_path = f"images/image_{prompt_item.sequence}.png"

    # 안전망 검증
    try:
        validate_prompt(prompt_item.prompt)
    except InvalidImagePromptError as exc:
        logger.warning(
            "prompt safety failed (seq %d): %s",
            prompt_item.sequence,
            exc,
        )
        return SkippedImage(
            sequence=prompt_item.sequence,
            reason="prompt_safety_failed",
        )

    # 캐시 확인
    if not regenerate and cache_dir is not None:
        cached_path = get_cached(cache_dir, cache_key)
        if cached_path is not None:
            copy_from_cache(cached_path, dest_path)
            return (
                GeneratedImage(
                    sequence=prompt_item.sequence,
                    path=relative_path,
                    prompt_hash=cache_key,
                    alt_text=prompt_item.alt_text,
                ),
                False,
            )

    # API 호출 + 1회 재시도
    png_bytes = _call_with_retry(provider, prompt_item.prompt)
    if png_bytes is None:
        return SkippedImage(
            sequence=prompt_item.sequence,
            reason="api_error",
        )

    # 저장
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(png_bytes)

    # 캐시에도 저장
    if cache_dir is not None:
        save_to_cache(cache_dir, cache_key, png_bytes)

    return (
        GeneratedImage(
            sequence=prompt_item.sequence,
            path=relative_path,
            prompt_hash=cache_key,
            alt_text=prompt_item.alt_text,
        ),
        True,
    )


def _call_with_retry(
    provider: ImageProvider,
    prompt: str,
) -> bytes | None:
    """API 호출 + 1회 재시도. 2회 실패 시 None 반환."""
    for attempt in range(2):
        try:
            return provider.generate(prompt)
        except ImageGenerationError as exc:
            if attempt == 0:
                logger.warning(
                    "image generation failed, retrying in %.1fs: %s",
                    _RETRY_DELAY_SECONDS,
                    exc,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
            else:
                logger.error("image generation failed after 2 attempts: %s", exc)
    return None


def _create_default_provider() -> ImageProvider:
    """config/settings.py 에서 설정을 읽어 기본 GeminiImageProvider 생성."""
    from config.settings import require, settings
    from domain.image_generation.provider import GeminiImageProvider

    api_key = require("gemini_api_key")
    return GeminiImageProvider(api_key=api_key, model=settings.image_model)
