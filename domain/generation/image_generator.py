"""AI 이미지 프롬프트 생성. 인터페이스만 구현.

한글/영문 텍스트 삽입 지시 금지.
의료 시술 전후 연출 금지.
"""

from __future__ import annotations

from domain.analysis.model import PatternCard
from domain.profile.model import ClientProfile


def generate_image_prompts(
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
    count: int = 2,
) -> list[str]:
    """본문 삽입용 AI 이미지 프롬프트를 생성한다.

    Args:
        keyword: 키워드
        pattern_card: 패턴 카드
        profile: 클라이언트 프로필
        count: 생성할 프롬프트 수

    Returns:
        프롬프트 문자열 리스트
    """
    mood = pattern_card.visual_pattern.get("mood", "professional")
    industry = profile.industry or "health"

    # 기본 프롬프트 템플릿 (분위기/무드 중심, 텍스트 삽입 금지)
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
