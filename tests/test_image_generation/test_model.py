"""ImagePrompt, GeneratedImage, SkippedImage, ImageGenerationResult 모델 테스트."""

from __future__ import annotations

from domain.image_generation.model import (
    GeneratedImage,
    ImageGenerationResult,
    ImagePrompt,
    SkippedImage,
)


class TestImagePrompt:
    def test_roundtrip(self) -> None:
        prompt = ImagePrompt(
            sequence=1,
            position="after_intro",
            prompt="A photo of Korean food, no text",
            alt_text="한식 사진",
            image_type="photo",
            rationale="도입 직후 분위기 사진",
        )
        data = prompt.model_dump()
        restored = ImagePrompt.model_validate(data)
        assert restored == prompt

    def test_json_roundtrip(self) -> None:
        prompt = ImagePrompt(
            sequence=2,
            position="section_3_end",
            prompt="Flat illustration, no text, no letters",
            alt_text="일러스트",
            image_type="illustration",
            rationale="본문 중간",
        )
        json_str = prompt.model_dump_json()
        restored = ImagePrompt.model_validate_json(json_str)
        assert restored.sequence == 2
        assert restored.image_type == "illustration"


class TestGeneratedImage:
    def test_fields(self) -> None:
        img = GeneratedImage(
            sequence=1,
            path="images/image_1.png",
            prompt_hash="abc123",
            alt_text="건강한 한식",
        )
        assert img.path == "images/image_1.png"
        assert img.prompt_hash == "abc123"


class TestSkippedImage:
    def test_reasons(self) -> None:
        for reason in (
            "compliance_failed",
            "api_error",
            "budget_exceeded",
            "prompt_safety_failed",
        ):
            s = SkippedImage(sequence=1, reason=reason)
            assert s.reason == reason


class TestImageGenerationResult:
    def test_empty(self) -> None:
        result = ImageGenerationResult()
        assert result.generated == []
        assert result.skipped == []

    def test_mixed(self) -> None:
        result = ImageGenerationResult(
            generated=[
                GeneratedImage(
                    sequence=1,
                    path="images/image_1.png",
                    prompt_hash="aaa",
                    alt_text="alt1",
                ),
            ],
            skipped=[
                SkippedImage(sequence=2, reason="api_error"),
            ],
        )
        assert len(result.generated) == 1
        assert len(result.skipped) == 1
        assert result.generated[0].sequence == 1
        assert result.skipped[0].reason == "api_error"
