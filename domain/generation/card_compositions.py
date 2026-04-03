"""구조 타입 → 브랜디드 카드 삽입 위치 매핑.

카드 3종(intro, transition, cta)이 SEO 텍스트 흐름 내
어느 섹션 뒤에 삽입될지 결정한다.
disclaimer는 의료 업종일 때 HTML 텍스트로 처리 (카드 아님).
"""

from __future__ import annotations

from domain.profile.model import ClientProfile

# 구조 타입별 카드 삽입 위치
# 값: "섹션 N 뒤에 삽입" (-1 = 글 끝)
CARD_POSITIONS: dict[str, dict[str, int]] = {
    "문제해결형": {"intro": 0, "transition": 3, "cta": -1},
    "스토리공감형": {"intro": 0, "transition": 2, "cta": -1},
    "QA형": {"intro": 0, "transition": 2, "cta": -1},
    "시즌연결형": {"intro": 0, "transition": 1, "cta": -1},
    "데이터기반형": {"intro": 0, "transition": 2, "cta": -1},
    "리스트형": {"intro": 0, "transition": 2, "cta": -1},
    "비포애프터형": {"intro": 0, "transition": 2, "cta": -1},
    "전문가칼럼형": {"intro": 0, "transition": 2, "cta": -1},
}

DEFAULT_POSITIONS: dict[str, int] = {"intro": 0, "transition": 2, "cta": -1}

# 생성 대상 카드 타입 (disclaimer 제외)
CARD_TYPES: list[str] = ["intro", "transition", "cta"]


def get_card_positions(
    structure_name: str,
    profile: ClientProfile,
) -> dict[str, int]:
    """구조 이름과 프로필을 기반으로 카드 삽입 위치를 반환한다.

    Returns:
        {"intro": 0, "transition": 3, "cta": -1} 형태의 딕셔너리
    """
    return CARD_POSITIONS.get(structure_name, DEFAULT_POSITIONS).copy()
