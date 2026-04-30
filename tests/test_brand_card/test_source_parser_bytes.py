"""source_parser.parse_source_bytes — bytes 입력 시 동일 결과를 내는지 검증.

presigned 다운로드 후 곧바로 파싱하는 신규 흐름에서 사용.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.brand_card.source_parser import (
    UnsupportedSourceError,
    parse_source_bytes,
    parse_source_file,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "brand_card_sources"


class TestParseSourceBytes:
    def test_txt_bytes_match_file_result(self) -> None:
        path = _FIXTURES / "sample.txt"
        from_file = parse_source_file(path)
        from_bytes = parse_source_bytes(".txt", path.read_bytes())
        assert from_bytes == from_file

    def test_html_bytes_strips_script(self) -> None:
        path = _FIXTURES / "sample.html"
        text = parse_source_bytes(".html", path.read_bytes())
        assert "alert(1)" not in text
        assert "본문 내용입니다" in text

    def test_docx_bytes_extracts_paragraphs(self) -> None:
        path = _FIXTURES / "sample.docx"
        text = parse_source_bytes(".docx", path.read_bytes())
        assert "브랜드 소개 본문" in text

    def test_empty_bytes_returns_empty_string(self) -> None:
        assert parse_source_bytes(".txt", b"") == ""

    def test_unsupported_suffix_raises(self) -> None:
        with pytest.raises(UnsupportedSourceError, match=".xyz"):
            parse_source_bytes(".xyz", b"hello")

    def test_suffix_case_insensitive(self) -> None:
        path = _FIXTURES / "sample.txt"
        text = parse_source_bytes(".TXT", path.read_bytes())
        assert "대구 다이어트 한의원" in text
