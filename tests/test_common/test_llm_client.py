"""LLM 클라이언트 유틸리티 테스트."""

from __future__ import annotations

from domain.common.llm_client import _strip_json_markdown


class TestStripJsonMarkdown:
    def test_strips_json_codeblock(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _strip_json_markdown(text) == '{"key": "value"}'

    def test_strips_plain_codeblock(self) -> None:
        text = "```\n[1, 2, 3]\n```"
        assert _strip_json_markdown(text) == "[1, 2, 3]"

    def test_strips_with_extra_whitespace(self) -> None:
        text = '  ```json\n{"a": 1}\n```  '
        assert _strip_json_markdown(text) == '{"a": 1}'

    def test_passthrough_plain_json(self) -> None:
        text = '{"key": "value"}'
        assert _strip_json_markdown(text) == '{"key": "value"}'

    def test_passthrough_array(self) -> None:
        text = '[{"a": 1}]'
        assert _strip_json_markdown(text) == '[{"a": 1}]'

    def test_multiline_json(self) -> None:
        text = '```json\n{\n  "key": "value",\n  "num": 42\n}\n```'
        result = _strip_json_markdown(text)
        assert '"key": "value"' in result
        assert '"num": 42' in result
