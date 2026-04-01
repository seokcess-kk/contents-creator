"""Anthropic Claude API 클라이언트 래퍼.

재시도 로직, 타임아웃, 에러 핸들링을 내장한다.
VLM 호출은 인터페이스만 정의하고 추후 연결한다.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from anthropic import Anthropic, APIError

from domain.common.config import settings

logger = logging.getLogger(__name__)

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def chat(
    prompt: str,
    *,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_retries: int = 2,
    timeout: float = 60.0,
) -> str:
    """Claude API에 텍스트 메시지를 보내고 응답을 반환한다.

    Args:
        prompt: 사용자 메시지
        system: 시스템 프롬프트
        model: 모델 ID
        max_tokens: 최대 출력 토큰
        temperature: 생성 온도
        max_retries: 최대 재시도 횟수
        timeout: 요청 타임아웃 (초)

    Returns:
        모델 응답 텍스트
    """
    client = get_client()
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else [],
                messages=messages,
                timeout=timeout,
            )
            return response.content[0].text
        except APIError as e:
            if attempt < max_retries and e.status_code in (429, 500, 502, 503):
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Claude API 에러 %s, %d초 후 재시도 (%d/%d)",
                    e.status_code,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
            else:
                raise


def chat_json(
    prompt: str,
    *,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """JSON 출력을 강제하는 chat 호출."""
    json_system = system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."
    return chat(prompt, system=json_system, model=model, max_tokens=max_tokens, temperature=0.3)


def analyze_image(
    image_path: Path,
    prompt: str,
    *,
    system: str = "",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
) -> str:
    """이미지를 VLM에 전달하여 분석한다.

    현재는 Claude의 비전 기능을 사용한다. 추후 다른 VLM으로 교체 가능.
    """
    client = get_client()

    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

    suffix = image_path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(suffix, "image/png")

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system if system else [],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        timeout=60.0,
    )
    return response.content[0].text
