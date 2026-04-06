"""Google Gemini API 클라이언트. VLM(비전) + 이미지 생성.

비주얼 분석 + 카드 HTML 디자인 + 이미지 생성에 사용한다.
텍스트 LLM은 Anthropic Claude를 계속 사용.
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


def chat(
    prompt: str,
    *,
    system: str = "",
    max_tokens: int = 8192,
    temperature: float = 0.7,
    max_retries: int = 2,
) -> str:
    """Gemini에 텍스트 메시지를 보내고 응답을 반환한다.

    Args:
        prompt: 사용자 메시지
        system: 시스템 프롬프트
        max_tokens: 최대 출력 토큰
        temperature: 생성 온도
        max_retries: 최대 재시도 횟수

    Returns:
        모델 응답 텍스트
    """
    import time

    from google.genai import types

    client = _get_client()

    contents = []
    if system:
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[System]\n{system}")],
            ),
        )
        contents.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="understood.")],
            ),
        )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            return response.text
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Gemini API 에러, %d초 후 재시도 (%d/%d): %s",
                    wait,
                    attempt + 1,
                    max_retries,
                    e,
                )
                time.sleep(wait)
            else:
                raise


IMAGE_MODEL_ID = "gemini-2.5-flash-image"


def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "3:4",
    max_retries: int = 2,
) -> bytes:
    """Gemini로 이미지를 생성하고 PNG 바이트를 반환한다.

    Args:
        prompt: 이미지 생성 프롬프트
        aspect_ratio: 종횡비 (1:1, 3:4, 16:9 등)
        max_retries: 최대 재시도 횟수

    Returns:
        PNG 이미지 바이트
    """
    import time as _time

    from google.genai import types

    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                ),
            )

            # 응답에서 이미지 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    logger.info("이미지 생성 완료 (Gemini, %s)", aspect_ratio)
                    return part.inline_data.data

            raise ValueError("응답에 이미지 데이터가 없습니다.")

        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "이미지 생성 실패, %d초 후 재시도 (%d/%d): %s",
                    wait,
                    attempt + 1,
                    max_retries,
                    e,
                )
                _time.sleep(wait)
            else:
                raise
    raise RuntimeError("이미지 생성 실패")
