"""outline_writer 테스트 (LLM mock)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from domain.analysis.pattern_card import PatternCard
from domain.generation.model import Outline
from domain.generation.outline_writer import generate_outline


def _make_tool_response(data: dict[str, Any]) -> SimpleNamespace:
    """tool_use 블록을 가진 mock 응답 생성."""
    block = SimpleNamespace(type="tool_use", input=data)
    usage = SimpleNamespace(input_tokens=100, output_tokens=50)
    return SimpleNamespace(content=[block], usage=usage)


_VALID_OUTLINE_DATA: dict[str, Any] = {
    "title": "다이어트 한의원 효과 정리",
    "title_pattern": "방법론형",
    "target_chars": 2800,
    "suggested_tags": ["다이어트", "한의원", "체질"],
    "image_prompts": [
        {
            "sequence": 1,
            "position": "after_intro",
            "prompt": "Korean tea scene, no text",
            "alt_text": "한국 차 풍경",
            "image_type": "photo",
            "rationale": "도입 직후",
        },
    ],
    "intro": "체중 관리에 대한 관심이 높아지면서 한의원을 찾는 분들이 늘고 있습니다. "
    "반복되는 실패 속에서 한의학적 접근이 주목받는 이유를 정리했습니다.",
    "sections": [
        {"index": 1, "role": "도입/공감", "subtitle": "(도입)", "is_intro": True},
        {
            "index": 2,
            "role": "정보제공",
            "subtitle": "주목받는 이유",
            "summary": "설명",
            "target_chars": 450,
            "dia_markers": ["list"],
        },
        {
            "index": 3,
            "role": "요약",
            "subtitle": "정리",
            "summary": "요약",
            "target_chars": 200,
        },
    ],
    "keyword_plan": {
        "main_keyword_target_count": 14,
        "subtitle_inclusion_target": 0.67,
    },
}


class TestGenerateOutline:
    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_returns_outline(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_OUTLINE_DATA)

        result = generate_outline(sample_pattern_card)

        assert isinstance(result, Outline)
        assert result.title == "다이어트 한의원 효과 정리"
        assert len(result.sections) == 3
        assert len(result.image_prompts) == 1
        assert len(result.suggested_tags) == 3

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_uses_opus_model(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_OUTLINE_DATA)

        generate_outline(sample_pattern_card)

        call_kwargs = mock_client.messages.create.call_args
        assert "opus" in call_kwargs.kwargs.get("model", "")

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_uses_tool_use(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_tool_response(_VALID_OUTLINE_DATA)

        generate_outline(sample_pattern_card)

        call_kwargs = mock_client.messages.create.call_args
        tools = call_kwargs.kwargs.get("tools", [])
        assert len(tools) == 1
        assert tools[0]["name"] == "record_outline"
        tool_choice = call_kwargs.kwargs.get("tool_choice", {})
        # outline_thinking_budget 기본값 0 → thinking 비활성 경로
        # → tool_choice=tool 로 이름 강제 (구조화 응답 보장).
        assert tool_choice.get("type") == "tool"
        assert tool_choice.get("name") == "record_outline"

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_raises_on_no_tool_use(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
    ) -> None:
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        # 텍스트 블록만 반환 (tool_use 없음)
        text_block = SimpleNamespace(type="text", text="no tool")
        mock_client.messages.create.return_value = SimpleNamespace(
            content=[text_block],
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )

        with pytest.raises(ValueError, match="tool_use"):
            generate_outline(sample_pattern_card)

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_falls_back_when_required_fields_missing(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """thinking 응답에 target_chars 등 required 필드 누락 → thinking off 폴백.

        기본값이 thinking=0 이므로 이 시나리오 재현을 위해 명시적으로 예산을 켠다.
        (실측에서 thinking 활성 시 tool_use 누락/부분 응답이 드물게 발생하는 케이스 보호)
        """
        from config.settings import settings

        monkeypatch.setattr(settings, "outline_thinking_budget", 2000)
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        # 1차 응답: target_chars 누락
        partial = {k: v for k, v in _VALID_OUTLINE_DATA.items() if k != "target_chars"}
        # 2차 응답 (폴백): 완전한 데이터
        mock_client.messages.create.side_effect = [
            _make_tool_response(partial),
            _make_tool_response(_VALID_OUTLINE_DATA),
        ]

        result = generate_outline(sample_pattern_card)

        assert isinstance(result, Outline)
        assert mock_client.messages.create.call_count == 2

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_raises_when_fallback_also_incomplete(
        self,
        mock_require: MagicMock,
        mock_anthropic: MagicMock,
        sample_pattern_card: PatternCard,
    ) -> None:
        """폴백 응답마저 필수 필드 누락 시 명시적 ValueError."""
        mock_require.return_value = "test-key"
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        partial = {k: v for k, v in _VALID_OUTLINE_DATA.items() if k != "target_chars"}
        mock_client.messages.create.return_value = _make_tool_response(partial)

        with pytest.raises(ValueError, match="target_chars"):
            generate_outline(sample_pattern_card)
