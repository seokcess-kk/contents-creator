"""Physical extractor regression tests — real Naver HTML fixtures.

These tests protect against regressions in the physical extractor's
ability to parse actual Naver Smart Editor HTML correctly.

If a test fails after a code change, it means the change broke
a previously working analysis capability. Fix the code, don't
relax the assertions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import HttpUrl

from domain.analysis.physical_extractor import extract_physical
from domain.crawler.model import BlogPage

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "naver_html"
GOLDEN_PATH = FIXTURES_DIR / "golden_values.json"


def _load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _make_page(html: str, idx: int = 0) -> BlogPage:
    return BlogPage(
        idx=idx,
        rank=idx + 1,
        url=HttpUrl("https://m.blog.naver.com/test/123456789"),
        mobile_url=HttpUrl("https://m.blog.naver.com/test/123456789"),
        html=html,
        source="integrated",
        fetched_at=datetime.now(UTC),
    )


@pytest.fixture(params=_load_golden(), ids=lambda g: g["filename"])
def golden_case(request: pytest.FixtureRequest) -> dict:
    """Parametrized fixture yielding one golden-value dict per sample."""
    return request.param


class TestPhysicalExtractorRegression:
    """Real HTML fixture regression tests."""

    def test_keyword_detected(self, golden_case: dict) -> None:
        """Keywords must be found (space-insensitive matching works)."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        assert result.keyword_analysis.total_count >= golden_case["keyword_total_count_min"], (
            f"Keyword count {result.keyword_analysis.total_count} "
            f"< {golden_case['keyword_total_count_min']}"
        )

    def test_keyword_density_nonzero(self, golden_case: dict) -> None:
        """Keyword density must be above minimum threshold."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        assert result.keyword_analysis.density >= golden_case["keyword_density_min"], (
            f"Density {result.keyword_analysis.density} < {golden_case['keyword_density_min']}"
        )

    def test_total_chars_in_range(self, golden_case: dict) -> None:
        """Total chars should stay within expected range."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        low = golden_case["total_chars_min"]
        high = golden_case["total_chars_max"]
        assert low <= result.total_chars <= high, (
            f"Total chars {result.total_chars} outside [{low}, {high}]"
        )

    def test_paragraph_count_reasonable(self, golden_case: dict) -> None:
        """Paragraph count must not regress to se-text component counting."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        assert result.total_paragraphs >= golden_case["total_paragraphs_min"], (
            f"Paragraphs {result.total_paragraphs} "
            f"< {golden_case['total_paragraphs_min']} (possible se-text regression)"
        )

    def test_paragraph_avg_not_bloated(self, golden_case: dict) -> None:
        """Average paragraph chars must not regress to giant se-text blocks."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        assert (
            result.paragraph_stats.avg_paragraph_chars <= golden_case["paragraph_avg_chars_max"]
        ), (
            f"Avg paragraph {result.paragraph_stats.avg_paragraph_chars} "
            f"> {golden_case['paragraph_avg_chars_max']} (possible se-text regression)"
        )

    def test_image_count_stable(self, golden_case: dict) -> None:
        """Image detection should be stable."""
        html = (FIXTURES_DIR / golden_case["filename"]).read_text(encoding="utf-8")
        result = extract_physical(_make_page(html), golden_case["keyword"])
        actual = len([e for e in result.element_sequence if e.type == "image"])
        assert actual == golden_case["image_count"], (
            f"Image count {actual} != expected {golden_case['image_count']}"
        )
