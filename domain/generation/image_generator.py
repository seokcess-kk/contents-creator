"""AI 이미지 생성. GPT Image Generation으로 본문 삽입용 이미지를 생성한다.

한글/영문 텍스트 삽입 지시 금지.
의료 시술 전후 연출 금지.
"""

from __future__ import annotations

import logging

from domain.analysis.model import PatternCard
from domain.generation.model import GeneratedImage
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)


def generate_image_prompts(
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
    count: int = 2,
) -> list[str]:
    """본문 삽입용 AI 이미지 프롬프트를 생성한다."""
    mood = pattern_card.visual_pattern.get("mood", "professional")
    industry = profile.industry or "health"

    base_prompts = [
        (
            f"A serene and {mood} {industry} clinic interior, "
            f"soft natural lighting, clean modern design, "
            f"no text or writing visible, photorealistic"
        ),
        (
            f"Abstract {mood} wellness concept, "
            f"calming color palette, minimalist composition, "
            f"no text or letters, soft focus background"
        ),
        (
            f"Professional {industry} environment, "
            f"warm inviting atmosphere, modern equipment, "
            f"no visible text or signage, clean aesthetic"
        ),
    ]

    return base_prompts[:count]


def generate_images(
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
    count: int = 2,
) -> list[GeneratedImage]:
    """이미지를 생성하고 바이트로 반환한다.

    Args:
        keyword: 키워드
        pattern_card: 패턴 카드
        profile: 클라이언트 프로필
        count: 생성할 이미지 수

    Returns:
        GeneratedImage 리스트
    """
    from domain.common.openai_client import generate_image

    prompts = generate_image_prompts(keyword, pattern_card, profile, count)
    results: list[GeneratedImage] = []

    for i, prompt in enumerate(prompts):
        logger.info("이미지 생성 중 (%d/%d)...", i + 1, len(prompts))
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
            logger.error("이미지 생성 실패 (%d/%d): %s", i + 1, len(prompts), e)
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
