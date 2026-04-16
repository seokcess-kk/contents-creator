"""prompt_validator.py 테스트 — 안전 규칙 검증."""

from __future__ import annotations

import pytest

from domain.image_generation.prompt_validator import (
    InvalidImagePromptError,
    validate_prompt,
)


class TestNoTextRequired:
    def test_no_text_present(self) -> None:
        validate_prompt("A Korean landscape, warm tones, no text")

    def test_no_letters_present(self) -> None:
        validate_prompt("A Korean landscape, warm tones, no letters")

    def test_missing_no_text_raises(self) -> None:
        with pytest.raises(InvalidImagePromptError, match="no text"):
            validate_prompt("A Korean landscape, warm tones")


class TestKoreanRequired:
    def test_person_with_korean(self) -> None:
        validate_prompt("A Korean woman doing yoga, no text")

    def test_person_without_korean_raises(self) -> None:
        with pytest.raises(InvalidImagePromptError, match="Korean"):
            validate_prompt("A woman doing yoga, no text")

    def test_family_with_korean(self) -> None:
        validate_prompt("Korean family having dinner, no text")

    def test_portrait_without_korean_raises(self) -> None:
        with pytest.raises(InvalidImagePromptError, match="Korean"):
            validate_prompt("portrait photo of a man, no text")

    def test_no_people_no_korean_ok(self) -> None:
        """인물 키워드 없으면 Korean 불필요."""
        validate_prompt("A bowl of rice, no text")


class TestForbiddenKeywords:
    @pytest.mark.parametrize(
        "keyword",
        [
            "patient",
            "before/after",
            "before and after",
            "medical procedure",
            "surgery",
            "injection",
            "treatment scene",
            "body comparison",
            "naked",
            "nude",
            "100%",
            "guarantee",
            "comparison shot",
            "weight loss progression",
        ],
    )
    def test_forbidden_keyword_raises(self, keyword: str) -> None:
        with pytest.raises(InvalidImagePromptError, match="forbidden"):
            validate_prompt(f"A scene with {keyword}, no text")

    def test_injured_raises(self) -> None:
        with pytest.raises(InvalidImagePromptError):
            validate_prompt("injured scene in a room, no text")

    def test_safe_prompt_passes(self) -> None:
        validate_prompt(
            "Realistic lifestyle photography of traditional Korean herbal "
            "tea bowl, warm beige palette, no text"
        )


class TestCaseInsensitive:
    def test_no_text_case_insensitive(self) -> None:
        validate_prompt("A landscape, No Text, warm tones")

    def test_korean_case_insensitive(self) -> None:
        validate_prompt("A KOREAN woman doing yoga, NO TEXT")

    def test_forbidden_case_insensitive(self) -> None:
        with pytest.raises(InvalidImagePromptError):
            validate_prompt("PATIENT photo, no text")
