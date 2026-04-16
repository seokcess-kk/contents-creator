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

    # "no patient", "no medical procedure" 같은 부정 지시를 제거하여 오탐 방지
    cleaned = _strip_negations(p)

    # 1. 텍스트 금지 키워드 필수
    if "no text" not in p and "no letters" not in p:
        raise InvalidImagePromptError("prompt must contain 'no text' or 'no letters'")

    # 2. 인물 등장 시 'Korean' 명시 필수 (부정 제거 후 검사)
    if any(kw in cleaned for kw in PEOPLE_KEYWORDS) and "korean" not in p:
        raise InvalidImagePromptError("prompt mentions people but does not specify 'Korean'")

    # 3. 의료 맥락·금지 키워드 차단 (부정 제거 후 검사)
    for kw in FORBIDDEN_KEYWORDS:
        if kw.lower() in cleaned:
            raise InvalidImagePromptError(f"prompt contains forbidden keyword '{kw}'")


def _strip_negations(text: str) -> str:
    """'no X', 'without X' 패턴을 제거해 부정 표현 오탐을 방지한다."""
    import re

    # "no patient", "no medical procedure" 등 제거
    cleaned = re.sub(r"\bno\s+\w[\w\s/]*(?=,|\.|$|\b(?:no|and)\b)", "", text)
    return re.sub(r"\bwithout\s+\w[\w\s/]*(?=,|\.|$|\b(?:no|and)\b)", "", cleaned)
