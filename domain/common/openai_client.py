"""OpenAI API 클라이언트. 이미지 생성 전용.

gpt-image-1 모델로 본문 삽입용 이미지를 생성한다.
"""

from __future__ import annotations

import base64
import logging
import time

from domain.common.config import settings

logger = logging.getLogger(__name__)

_client = None

IMAGE_MODEL = "gpt-image-1"


def _get_client():  # type: ignore[no-untyped-def]
    """OpenAI 클라이언트를 반환한다 (캐시)."""
    global _client  # noqa: PLW0603
    if _client is None:
        from openai import OpenAI

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def generate_image(
    prompt: str,
    *,
    size: str = "1024x1024",
    max_retries: int = 2,
) -> bytes:
    """프롬프트로 이미지를 생성하고 PNG 바이트를 반환한다.

    Args:
        prompt: 이미지 생성 프롬프트
        size: 이미지 크기
        max_retries: 최대 재시도 횟수

    Returns:
        PNG 이미지 바이트
    """
    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            response = client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json",
            )
            b64_data = response.data[0].b64_json
            if not b64_data:
                raise ValueError("이미지 데이터가 비어 있습니다.")

            logger.info("이미지 생성 완료 (%s)", size)
            return base64.b64decode(b64_data)

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
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("이미지 생성 실패")
