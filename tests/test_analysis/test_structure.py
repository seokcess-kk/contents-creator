"""L1 구조 분석 테스트."""

from __future__ import annotations

from domain.analysis.structure_analyzer import aggregate_l1, analyze_structure

SAMPLE_HTML = """\
<html><body>
<div class="se-main-container">
  <p>도입부 첫 문단입니다. 오늘은 피부 관리에 대해 알아보겠습니다.</p>
  <h3>피부 관리의 중요성</h3>
  <p>피부는 우리 몸의 가장 큰 기관입니다.</p>
  <p>꾸준한 관리가 필요합니다.</p>
  <img src="image1.jpg" alt="피부 관리">
  <h3>추천 관리 방법</h3>
  <p>보습이 가장 중요합니다.</p>
  <p>자외선 차단제를 꼭 바르세요.</p>
  <img src="image2.jpg" alt="자외선 차단">
  <hr>
  <p>상담 예약은 전화로 문의해 주세요.</p>
  <blockquote>건강한 피부를 위한 첫걸음</blockquote>
</div>
</body></html>
"""


class TestAnalyzeStructure:
    def test_counts_chars(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert result.total_chars > 0

    def test_counts_paragraphs(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert result.total_paragraphs > 0

    def test_extracts_subtitles(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert result.subtitle_count == 2
        assert "피부 관리의 중요성" in result.subtitles

    def test_extracts_images(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert result.image_count == 2

    def test_extracts_cta(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert len(result.cta_texts) > 0
        assert any("전화" in t or "상담" in t or "예약" in t for t in result.cta_texts)

    def test_counts_naver_elements(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert result.naver_elements["divider"] >= 1
        assert result.naver_elements["blockquote"] >= 1

    def test_section_ratio_format(self) -> None:
        result = analyze_structure(SAMPLE_HTML)
        assert "도입" in result.section_ratio
        assert "본론" in result.section_ratio
        assert "결론" in result.section_ratio


class TestAggregateL1:
    def test_aggregate_multiple(self) -> None:
        s1 = analyze_structure(SAMPLE_HTML)
        s2 = analyze_structure(SAMPLE_HTML)
        l1 = aggregate_l1([s1, s2])

        assert l1.post_count == 2
        assert l1.avg_char_count > 0
        assert l1.avg_subtitle_count > 0

    def test_aggregate_empty(self) -> None:
        l1 = aggregate_l1([])
        assert l1.post_count == 0
