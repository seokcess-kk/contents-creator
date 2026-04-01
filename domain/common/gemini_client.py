"""Google Gemini API 클라이언트. VLM(비전) 전용.

비주얼 분석에서만 사용한다. 텍스트 LLM은 Anthropic Claude를 계속 사용.
새 SDK: google-genai (google.generativeai는 deprecated).
"""

from __future__ import annotations

import logging
from pathlib import Path

from domain.common.config import settings

logger = logging.getLogger(__name__)

_client = None

MODEL_ID = "gemini-2.5-flash"


def _get_client():  # type: ignore[no-untyped-def]
    """Gemini 클라이언트를 반환한다 (캐시)."""
    global _client
    if _client is None:
        from google import genai

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def analyze_image(
    image_path: Path,
    prompt: str,
    *,
    max_tokens: int = 1024,
) -> str:
    """Gemini Vision으로 이미지를 분석한다.

    Args:
        image_path: 이미지 파일 경로
        prompt: 분석 프롬프트
        max_tokens: 최대 출력 토큰

    Returns:
        모델 응답 텍스트
    """
    from google.genai import types

    client = _get_client()

    image_bytes = image_path.read_bytes()
    suffix = image_path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/png")

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=prompt),
                ],
            ),
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.3,
        ),
    )

    return response.text
