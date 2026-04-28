"""source_parser — txt/md/docx/pdf/html 4종 텍스트 추출 단위 테스트.

tests/fixtures/brand_card_sources/ 의 실측 파일 사용.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.brand_card.source_parser import (
    SourceParseError,
    UnsupportedSourceError,
    parse_source_file,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "brand_card_sources"


class TestTxtAndMd:
    def test_utf8_txt_extracted(self) -> None:
        text = parse_source_file(_FIXTURES / "sample.txt")
        assert "대구 다이어트 한의원" in text
        assert "체질 분석" in text

    def test_md_extracted_as_plain_text(self) -> None:
        """md 도 _parse_text 경로 사용 — 마크다운 마크업 그대로 보존."""
        text = parse_source_file(_FIXTURES / "sample.md")
        assert "브랜드 소개" in text
        # 마크다운 raw 그대로 (LLM 이 해석)
        assert "#" in text or "체질" in text

    def test_cp949_fallback(self) -> None:
        """utf-8 디코딩 실패 시 cp949 시도."""
        text = parse_source_file(_FIXTURES / "cp949.txt")
        assert "한약 처방" in text


class TestDocx:
    def test_paragraphs_and_tables_extracted(self) -> None:
        text = parse_source_file(_FIXTURES / "sample.docx")
        # paragraph
        assert "브랜드 소개 본문" in text
        assert "체질 진단" in text
        # 표 셀 평탄화
        assert "진료" in text
        assert "한약" in text
        assert "관리" in text
        assert "체크" in text


class TestPdf:
    def test_blank_pdf_returns_empty_or_handles_gracefully(self) -> None:
        """blank PDF — pypdf 가 빈 결과 → pdfplumber 로 fallback. 빈 결과 허용."""
        text = parse_source_file(_FIXTURES / "sample.pdf")
        # 빈 PDF 라 빈 문자열 또는 공백만 있을 수 있음 — 예외만 안 나면 OK
        assert isinstance(text, str)


class TestHtml:
    def test_script_and_style_removed(self) -> None:
        text = parse_source_file(_FIXTURES / "sample.html")
        # script/style 태그는 제거
        assert "alert(1)" not in text
        assert "color:red" not in text
        # 본문 텍스트 보존
        assert "대구 한의원" in text
        assert "본문 내용입니다" in text


class TestErrorHandling:
    def test_missing_file_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_source_file(_FIXTURES / "nonexistent.txt")

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        bad = tmp_path / "data.xyz"
        bad.write_text("x")
        with pytest.raises(UnsupportedSourceError, match=".xyz"):
            parse_source_file(bad)

    def test_unparseable_encoding_raises(self, tmp_path: Path) -> None:
        """utf-8 도 cp949 도 디코딩 안 되는 바이너리 → SourceParseError."""
        bad = tmp_path / "binary.txt"
        # cp949 와 utf-8 모두에서 invalid 인 바이트
        bad.write_bytes(b"\xff\xfe\xfd\xfc\xff\xfe\xfd")
        with pytest.raises(SourceParseError):
            parse_source_file(bad)
