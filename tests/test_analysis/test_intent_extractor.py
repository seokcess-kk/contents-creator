"""intent_extractor 단위 테스트 (LLM mock).

P1 (2026-05-12) — Haiku 4.5 기반 사용자 의도 추출.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from pydantic import HttpUrl

from domain.analysis.intent_extractor import extract_intents
from domain.crawler.model import BlogPage

_NOW = datetime.now().astimezone()


def _make_tool_response(data: dict[str, Any]) -> SimpleNamespace:
    block = SimpleNamespace(type="tool_use", input=data)
    usage = SimpleNamespace(input_tokens=100, output_tokens=50)
    return SimpleNamespace(content=[block], usage=usage)


def _page(html: str = "<html><body>본문 텍스트</body></html>") -> BlogPage:
    return BlogPage(
        idx=0,
        rank=1,
        url=HttpUrl("https://blog.naver.com/test/100000001"),
        mobile_url=HttpUrl("https://m.blog.naver.com/test/100000001"),
        html=html,
        fetched_at=_NOW,
    )


class TestExtractIntents:
    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_returns_intent_list(self, mock_require: MagicMock, mock_anthropic: MagicMock) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.return_value = _make_tool_response(
            {
                "intents": [
                    "비용은 얼마인가요?",
                    "보철물 종류 차이",
                    "회복 기간은 얼마나 걸리나요?",
                ]
            }
        )
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "강남 임플란트")
        assert result == [
            "비용은 얼마인가요?",
            "보철물 종류 차이",
            "회복 기간은 얼마나 걸리나요?",
        ]

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_strips_whitespace_and_dedupes_capped(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.return_value = _make_tool_response(
            {
                "intents": [
                    "  비용 ",
                    "보철물 종류",
                    "회복 기간",
                    "보장 기간",
                    "추가 시술",
                    "사후 관리",
                    "병원 위치",  # 6번째 — 5개로 자름
                ]
            }
        )
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "임플란트")
        assert len(result) == 5
        assert result[0] == "비용"  # 공백 strip

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_empty_string_filtered(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.return_value = _make_tool_response(
            {"intents": ["", "   ", "유효한 의도"]}
        )
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "키워드")
        assert result == ["유효한 의도"]

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_too_long_intent_filtered(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        long_intent = "x" * 100  # _MAX_INTENT_CHARS=60 초과
        client.messages.create.return_value = _make_tool_response(
            {"intents": [long_intent, "정상 의도"]}
        )
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "키워드")
        assert result == ["정상 의도"]

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_non_string_items_filtered(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.return_value = _make_tool_response(
            {"intents": [123, None, "정상 의도", {"x": "y"}]}
        )
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "키워드")
        assert result == ["정상 의도"]

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_no_tool_use_block_returns_empty(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_require.return_value = "fake-key"
        client = MagicMock()
        # text 블록만 (tool_use 누락)
        text_block = SimpleNamespace(type="text", text="설명만")
        usage = SimpleNamespace(input_tokens=10, output_tokens=10)
        client.messages.create.return_value = SimpleNamespace(content=[text_block], usage=usage)
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "키워드")
        assert result == []

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_api_failure_returns_empty(
        self, mock_require: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        """API 호출 실패 시 빈 리스트 (graceful, raise 금지)."""
        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        mock_anthropic.Anthropic.return_value = client

        result = extract_intents(_page(), "키워드")
        assert result == []

    @patch("domain.common.anthropic_client.anthropic")
    @patch("domain.common.anthropic_client.require")
    def test_uses_haiku_model(self, mock_require: MagicMock, mock_anthropic: MagicMock) -> None:
        """Haiku 4.5 모델 호출 확인 — 비용 결정 회귀 방지."""
        from config.settings import settings

        mock_require.return_value = "fake-key"
        client = MagicMock()
        client.messages.create.return_value = _make_tool_response({"intents": ["a", "b"]})
        mock_anthropic.Anthropic.return_value = client

        extract_intents(_page(), "키워드")

        call_kwargs = client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == settings.model_haiku
        assert "haiku" in settings.model_haiku.lower()
