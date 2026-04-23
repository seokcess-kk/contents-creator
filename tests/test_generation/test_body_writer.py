"""body_writer 테스트 (LLM mock + M2 검증).

핵심 검증:
- M2: generate_body 시그니처에 intro 원문 파라미터 없음
- M2: 프롬프트에 intro 원문 미포함
- tool_use 사용 확인
- BodyResult 파싱
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from domain.analysis.pattern_card import PatternCard
from domain.generation.body_writer import generate_body
from domain.generation.model import BodyResult, Outline


def _make_tool_response(data: dict[str, Any]) -> SimpleNamespace:
    block = SimpleNamespace(type="tool_use", input=data)
    usage = SimpleNamespace(input_tokens=100, output_tokens=50)
    return SimpleNamespace(content=[block], usage=usage)


_VALID_BODY_DATA: dict[str, Any] = {
    "body_sections": [
        {
            "index": 2,
            "subtitle": "한의원 다이어트가 주목받는 이유",
            "content_md": "한의학적 접근은 체질을 기반으로 합니다.",
        },
        {
            "index": 3,
            "subtitle": "체질별 관리 방법",
            "content_md": "체질에 따라 관리 방법이 다릅니다.",
        },
    ],
}


class TestM2Invariant:
    """M2 불변 규칙 검증."""

    def test_signature_has_no_intro_text_param(self) -> None:
        """generate_body 시그니처에 intro 원문 파라미터가 없어야 한다."""
        sig = inspect.signature(generate_body)
        forbidden = {
            "intro_text",
            "intro_md",
            "full_intro",
            "intro_content",
            "intro_body",
            "intro_raw",
        }
        params = set(sig.parameters.keys())
        overlap = params & forbidden
        assert not overlap, f"M2 위반: 금지된 파라미터 발견 {overlap}"

    def test_signature_has_intro_tone_hint(self) -> None:
        """intro_tone_hint 파라미터는 허용된다."""
        sig = inspect.signature(generate_body)
        assert "intro_tone_hint" in sig.parameters

    def test_signature_has_outline_without_intro(self) -> None:
        """outline_without_intro 파라미터가 있어야 한다."""
        sig = inspect.signature(generate_body)
        assert "outline_without_intro" in sig.parameters


class TestGenerateBody:
    @patch("domain.generation.body_writer.anthropic")
    @patch("domain.generation.body_writer.require")
    def test_returns_body_result(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_BODY_DATA)

        result = generate_body(
            outline_without_intro,
            "공감형 톤 유지",
            sample_pattern_card,
        )

        assert isinstance(result, BodyResult)
        assert len(result.body_sections) == 2
        assert result.body_sections[0].index == 2

    @patch("domain.generation.body_writer.anthropic")
    @patch("domain.generation.body_writer.require")
    def test_uses_opus_model(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_BODY_DATA)

        generate_body(outline_without_intro, "톤", sample_pattern_card)

        call_kwargs = mock_client.messages.create.call_args
        assert "opus" in call_kwargs.kwargs.get("model", "")

    @patch("domain.generation.body_writer.anthropic")
    @patch("domain.generation.body_writer.require")
    def test_uses_tool_use(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_BODY_DATA)

        generate_body(outline_without_intro, "톤", sample_pattern_card)

        call_kwargs = mock_client.messages.create.call_args
        tools = call_kwargs.kwargs.get("tools", [])
        assert len(tools) == 1
        assert tools[0]["name"] == "record_body"

    @patch("domain.generation.body_writer.anthropic")
    @patch("domain.generation.body_writer.require")
    def test_raises_on_no_tool_use(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        outline_without_intro: Outline,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        text_block = SimpleNamespace(type="text", text="no tool")
        mock_client.messages.create.return_value = SimpleNamespace(
            content=[text_block],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )

        with pytest.raises(ValueError, match="tool_use"):
            generate_body(outline_without_intro, "톤", sample_pattern_card)
