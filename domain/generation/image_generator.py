"""AI 이미지 생성. SEO 텍스트의 [이미지: 설명]을 기반으로 동적 프롬프트를 구성한다.

한글/영문 텍스트 삽입 지시 금지.
의료 시술 전후 연출 금지.
"""

from __future__ import annotations

import logging
import re

from domain.analysis.model import PatternCard
from domain.generation.model import GeneratedImage
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)


def extract_image_descriptions(seo_text: str) -> list[str]:
    """SEO 텍스트에서 [이미지: 설명] 마커의 설명을 순서대로 추출한다."""
    return re.findall(r"\[이미지:\s*(.+?)\]", seo_text)


def build_prompt(
    description: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> str:
    """이미지 설명 + 컨텍스트로 생성 프롬프트를 구성한다."""
    mood = pattern_card.visual_pattern.get("mood", "professional")
    industry = profile.industry or "health"
    sub = profile.sub_category or ""

    return (
        f"High-quality photorealistic image for a Korean {industry} "
        f"{sub} blog post. "
        f"Scene: {description}. "
        f"Mood: {mood}, clean and modern. "
        f"Style: editorial photography, soft natural lighting, "
        f"shallow depth of field. "
        f"IMPORTANT: No text, no letters, no writing, no watermarks "
        f"visible in the image."
    )


def generate_images(
    seo_text: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> list[GeneratedImage]:
    """SEO 텍스트의 이미지 마커를 기반으로 이미지를 생성한다.

    [이미지: 설명]에서 설명을 추출하여 동적 프롬프트를 구성하고,
    Gemini Image API로 이미지를 생성한다.

    Args:
        seo_text: SEO 블로그 원고 (마크다운)
        pattern_card: 패턴 카드 (mood, industry 컨텍스트)
        profile: 클라이언트 프로필

    Returns:
        GeneratedImage 리스트 (마커 순서대로)
    """
    from domain.common.gemini_client import generate_image

    descriptions = extract_image_descriptions(seo_text)
    if not descriptions:
        logger.info("이미지 마커 없음, 생성 건너뜀")
        return []

    results: list[GeneratedImage] = []

    for i, desc in enumerate(descriptions):
        prompt = build_prompt(desc, pattern_card, profile)
        logger.info("이미지 생성 중 (%d/%d): %s", i + 1, len(descriptions), desc[:40])

        try:
            image_bytes = generate_image(prompt)
            results.append(
                GeneratedImage(
                    prompt=prompt,
                    image_bytes=image_bytes,
                    success=True,
                ),
            )
        except Exception as e:
            logger.error("이미지 생성 실패 (%d/%d): %s", i + 1, len(descriptions), e)
            results.append(
                GeneratedImage(
                    prompt=prompt,
                    success=False,
                    error=str(e),
                ),
            )

    logger.info(
        "이미지 생성 완료: %d/%d 성공",
        sum(1 for r in results if r.success),
        len(results),
    )
    return results
