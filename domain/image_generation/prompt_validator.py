"""이미지 prompt 정합성 검증 — 안전망.

[8] compliance 가 1차 차단하지만, image_generation 도메인이 한 번 더 검증한다.
CLAUDE.md 의 이미지 정책 + SPEC-SEO-TEXT.md §3 [9] 규칙.
"""

from __future__ import annotations


class InvalidImagePromptError(Exception):
    """이미지 prompt 가 안전 규칙을 위반."""


# 사람 관련 키워드 — 인물 등장 시 'Korean' 동반 필수
PEOPLE_KEYWORDS: tuple[str, ...] = (
    "person",
    "people",
    "man",
    "woman",
    "face",
    "portrait",
    "family",
    "child",
)

# 의료 맥락 금지 키워드 — 인물 유무 무관 영구 금지
FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    # 환자
    "patient",
    "\ud658\uc790",  # 환자
    "injured",
    "sick person",
    # 전후 비교
    "before/after",
    "before and after",
    "comparison shot",
    "weight loss progression",
    # 시술 장면
    "medical procedure",
    "surgery",
    "injection",
    "treatment scene",
    # 신체 비교
    "body comparison",
    "naked",
    "nude",
    # 효과 보장
    "100%",
    "guarantee",
)


def validate_prompt(prompt: str) -> None:
    """prompt 정합성 검증. 위반 시 InvalidImagePromptError.

    1. 텍스트 금지 키워드 필수 포함
    2. 인물 등장 시 'Korean' 명시 필수
    3. 의료 맥락·금지 키워드 차단
    """
    p = prompt.lower()

    # 1. 텍스트 금지 키워드 필수
    if "no text" not in p and "no letters" not in p:
        raise InvalidImagePromptError("prompt must contain 'no text' or 'no letters'")

    # 2. 인물 등장 시 'Korean' 명시 필수
    if any(kw in p for kw in PEOPLE_KEYWORDS) and "korean" not in p:
        raise InvalidImagePromptError("prompt mentions people but does not specify 'Korean'")

    # 3. 의료 맥락·금지 키워드 차단
    for kw in FORBIDDEN_KEYWORDS:
        if kw.lower() in p:
            raise InvalidImagePromptError(f"prompt contains forbidden keyword '{kw}'")
