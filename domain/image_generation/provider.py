"""이미지 생성 프로바이더 — Protocol + Gemini 구현.

ImageProvider Protocol 로 테스트 시 mock 주입 가능.
GeminiImageProvider 는 Google Gen AI SDK 를 사용한다.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """이미지 생성 API 호출 실패."""


class ImageProvider(Protocol):
    """이미지 생성 프로바이더 인터페이스."""

    def generate(self, prompt: str, aspect_ratio: str = "1:1") -> bytes:
        """prompt → PNG 바이트. 실패 시 ImageGenerationError."""
        ...


class GeminiImageProvider:
    """Google Gen AI SDK 기반 Gemini 이미지 생성."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, aspect_ratio: str = "1:1") -> bytes:
        """prompt → PNG 바이트. 실패 시 ImageGenerationError."""
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                ),
            )
        except Exception as exc:
            raise ImageGenerationError(f"Gemini API 호출 실패: {exc}") from exc

        return self._extract_image_bytes(response)

    def _extract_image_bytes(self, response: object) -> bytes:
        """응답에서 이미지 바이트를 추출한다."""
        try:
            candidates = response.candidates  # type: ignore[attr-defined]
            if not candidates:
                raise ImageGenerationError("응답에 candidates 없음")

            parts = candidates[0].content.parts
            for part in parts:
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    data: bytes = part.inline_data.data
                    return data

        except ImageGenerationError:
            raise
        except Exception as exc:
            raise ImageGenerationError(f"응답 파싱 실패: {exc}") from exc

        raise ImageGenerationError("응답에 이미지 데이터 없음")
