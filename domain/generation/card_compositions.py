"""브랜드 카드 시퀀스 정의.

5종 기본 카드(greeting, empathy, service, trust, cta)를
프로필 정보에 따라 시퀀스로 구성한다.
"""

from __future__ import annotations

from domain.generation.model import BRAND_CARD_TYPES
from domain.profile.model import ClientProfile

# 기본 5종 시퀀스
BRAND_CARD_SEQUENCE: list[str] = list(BRAND_CARD_TYPES)


def get_brand_sequence(profile: ClientProfile) -> list[str]:
    """프로필 기반으로 브랜드 카드 시퀀스를 반환한다."""
    seq = list(BRAND_CARD_SEQUENCE)
    if profile.is_medical():
        seq.append("disclaimer")
    return seq
